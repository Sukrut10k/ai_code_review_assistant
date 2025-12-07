import os
import json
import re
from typing import Dict, List, Any

import requests
from dotenv import load_dotenv


# Load environment variables from .env
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "llama-3.1-8b-instant")

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"


class LLMConfigError(Exception):
    """Raised when LLM configuration is missing or invalid."""
    pass


def calculate_code_metrics(files: Dict[str, str]) -> Dict[str, Any]:
    """Calculate code complexity metrics."""
    metrics = {}
    for filename, content in files.items():
        lines = content.strip().split('\n')
        total_lines = len(lines)
        code_lines = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
        comment_lines = len([l for l in lines if l.strip().startswith('#')])
        
        # Simple complexity estimation
        complexity_keywords = ['if', 'for', 'while', 'elif', 'else', 'try', 'except', 'def', 'class']
        complexity_score = sum(content.lower().count(kw) for kw in complexity_keywords)
        
        metrics[filename] = {
            'total_lines': total_lines,
            'code_lines': code_lines,
            'comment_lines': comment_lines,
            'complexity_score': complexity_score,
            'comment_ratio': round((comment_lines / total_lines * 100) if total_lines > 0 else 0, 2)
        }
    return metrics


def scan_security_issues(files: Dict[str, str]) -> List[Dict[str, Any]]:
    """Basic security pattern detection."""
    security_issues = []
    
    patterns = {
        'sql_injection': [r'execute\s*\(\s*["\'].*%s', r'cursor\.execute.*\+'],
        'hardcoded_secrets': [r'password\s*=\s*["\'][^"\']+["\']', r'api_key\s*=\s*["\'][^"\']+["\']'],
        'unsafe_eval': [r'\beval\(', r'\bexec\('],
        'command_injection': [r'os\.system\(', r'subprocess\.call\(.*shell=True'],
    }
    
    for filename, content in files.items():
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            for vuln_type, regexes in patterns.items():
                for regex in regexes:
                    if re.search(regex, line, re.IGNORECASE):
                        security_issues.append({
                            'file': filename,
                            'line': line_num,
                            'type': vuln_type.replace('_', ' ').title(),
                            'code': line.strip()
                        })
    
    return security_issues


def _build_prompt_from_files(files: Dict[str, str]) -> str:
    """
    Build a single prompt string from multiple files.

    Truncates very long files to avoid hitting token limits.
    """
    parts: list[str] = []

    for filename, content in files.items():
        max_chars = 8000  # safety limit
        if len(content) > max_chars:
            content = content[:max_chars] + "\n\n[...TRUNCATED...]"

        parts.append(f"--- BEGIN FILE: {filename} ---\n{content}\n--- END FILE ---\n")

    return "\n".join(parts)


def _fallback_parse(text: str) -> Dict[str, Any]:
    """
    Fallback if JSON parsing fails: treat text as a big details block
    and generate a simple summary.
    """
    lines = text.strip().splitlines()
    summary = "\n".join(lines[:5])
    details = text.strip()
    return {
        "summary": summary,
        "details": details,
        "issues": [],
        "quality_score": 5.0,
        "strengths": [],
        "metrics": {},
        "raw_response": text,
    }


def review_code_with_llm(files: Dict[str, str]) -> Dict[str, Any]:
    """
    Call the Groq LLM to review the given code files with enhanced analysis.
    """
    if not GROQ_API_KEY:
        raise LLMConfigError("GROQ_API_KEY is not set in environment (.env).")

    # Calculate metrics FIRST
    metrics = calculate_code_metrics(files)
    
    # Security scan
    security_issues = scan_security_issues(files)
    
    prompt_code = _build_prompt_from_files(files)
    
    # Enhanced system message with metrics
    metrics_summary = "\n".join([
        f"File: {fname} - Lines: {m['code_lines']}, Complexity: {m['complexity_score']}, Comments: {m['comment_ratio']}%"
        for fname, m in metrics.items()
    ])
    
    security_summary = ""
    if security_issues:
        security_summary = "SECURITY ALERTS FOUND:\n" + "\n".join([
            f"⚠️ {issue['type']} in {issue['file']}:{issue['line']}"
            for issue in security_issues[:5]
        ]) + "\n\n"

    system_message = (
        "You are a senior software engineer performing a code review.\n"
        f"{security_summary}"
        f"CODE METRICS:\n{metrics_summary}\n\n"
        "You must return ONLY a single valid JSON object, no markdown, no backticks.\n"
        "Focus on:\n"
        "- Code complexity and maintainability\n"
        "- Readability and clarity\n"
        "- Security vulnerabilities (SQL injection, XSS, authentication)\n"
        "- Performance bottlenecks and optimization opportunities\n"
        "- Testing gaps and edge cases\n"
        "- Best practices and design patterns\n"
        "- Documentation quality\n\n"
        "The JSON object MUST have this shape:\n"
        "{\n"
        "  \"summary\": \"short high-level summary with overall quality rating (1-10)\",\n"
        "  \"details\": \"full detailed review in plain text\",\n"
        "  \"quality_score\": 7.5,\n"
        "  \"strengths\": [\"list of good practices found\"],\n"
        "  \"issues\": [\n"
        "    {\n"
        "      \"id\": \"unique-issue-id\",\n"
        "      \"file\": \"filename\",\n"
        "      \"line_start\": 0,\n"
        "      \"line_end\": 0,\n"
        "      \"severity\": \"critical | high | medium | low | info\",\n"
        "      \"category\": \"bug | security | performance | readability | style | test | other\",\n"
        "      \"message\": \"one-sentence description\",\n"
        "      \"suggestion\": \"how to fix it\",\n"
        "      \"code_patch\": \"optional code snippet\"\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "If there are no issues, return an empty list for \"issues\"."
    )

    user_message = (
        "Review the following code files and provide a professional code review.\n\n"
        f"{prompt_code}"
    )

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.2,
    }

    response = requests.post(
        GROQ_CHAT_COMPLETIONS_URL,
        headers=headers,
        json=payload,
        timeout=90,
    )

    response.raise_for_status()
    data = response.json()

    content = data["choices"][0]["message"]["content"]

    # Try to parse JSON
    try:
        parsed = json.loads(content)
        return {
            "summary": parsed.get("summary", ""),
            "details": parsed.get("details", ""),
            "quality_score": parsed.get("quality_score", 5.0),
            "strengths": parsed.get("strengths", []),
            "issues": parsed.get("issues", []),
            "metrics": metrics,
            "raw_response": content,
        }
    except Exception:
        # Fallback if the model didn't obey strict JSON
        fallback = _fallback_parse(content)
        fallback["metrics"] = metrics
        return fallback