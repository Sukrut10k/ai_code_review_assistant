import io
from collections import defaultdict

import requests
import streamlit as st
from fpdf import FPDF


BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="AI Code Review Assistant",
    layout="wide",
)
# Helper: Language Detection

EXTENSION_LANG_MAP = {
    "py": "Python",
    "js": "JavaScript",
    "java": "Java",
    "cpp": "C++",
    "c": "C",
    "go": "Go",
    "php": "PHP",
    "sql": "SQL",
    "html": "HTML",
    "css": "CSS",
    "sh": "Bash",
    "txt": "Plain text / Other",
}


def detect_language_from_filename(filename: str) -> str:
    if "." not in filename:
        return "Unknown"
    ext = filename.rsplit(".", 1)[-1].lower()
    return EXTENSION_LANG_MAP.get(ext, f"Unknown ({ext})")

# Helper: Group issues by severity

SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]


def group_issues_by_severity(issues):
    grouped = defaultdict(list)
    for issue in issues:
        sev = (issue.get("severity") or "").lower()
        if sev not in SEVERITY_ORDER:
            sev = "info"
        grouped[sev].append(issue)
    return grouped


def render_issue(issue):
    """
    Render a single issue block with severity styling.
    """
    severity = (issue.get("severity") or "").lower()
    category = issue.get("category", "unknown")
    message = issue.get("message", "")
    suggestion = issue.get("suggestion", "")
    file = issue.get("file", "unknown")
    line_start = issue.get("line_start", 0)
    line_end = issue.get("line_end", 0)
    code_patch = issue.get("code_patch") or ""

    header = f"[{severity.upper()}] [{category}] {message}"
    location = f"File: {file}, Lines: {line_start}-{line_end}"

    if severity in ("critical", "high"):
        show = st.error
    elif severity == "medium":
        show = st.warning
    else:
        show = st.info

    # Colored headline
    show(f"**{header}**\n\n*{location}*")

    # Extra details below
    if suggestion:
        st.markdown("**Suggestion:**")
        st.write(suggestion)
    if code_patch.strip():
        st.markdown("**Auto-fix suggestion (patch):**")
        st.code(code_patch, language="python")


# Helper: Build PDF report

def build_pdf_report(review, filenames_str: str, languages_str: str) -> bytes:
    """
    Unicode-safe PDF generation using a TrueType font.
    """
    import io
    from fpdf import FPDF
    import os

    font_path = os.path.join("frontend", "fonts", "DejaVuSans.ttf")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()

    # Register Unicode font
    pdf.add_font("DejaVu", "", font_path)
    pdf.set_font("DejaVu", size=12)

    def write_line(text: str = "", ln: bool = True):
        safe_text = str(text)
        pdf.multi_cell(0, 8, safe_text)
        if ln:
            pdf.ln(2)

    review_id = review.get("id", "?")
    summary = review.get("summary", "")
    details = review.get("details", "")
    issues = review.get("issues", [])
    quality_score = review.get("quality_score", 0)

    # Title
    pdf.set_font("DejaVu", size=14)
    write_line(f"Code Review Report #{review_id}")
    pdf.set_font("DejaVu", size=11)
    write_line(f"Files: {filenames_str}")
    write_line(f"Detected languages: {languages_str}")
    write_line(f"Quality Score: {quality_score}/10")
    write_line()

    # Summary
    pdf.set_font("DejaVu", size=12)
    write_line("Summary:")
    pdf.set_font("DejaVu", size=11)
    write_line(summary)
    write_line()

    # Details
    pdf.set_font("DejaVu", size=12)
    write_line("Detailed Review:")
    pdf.set_font("DejaVu", size=11)
    write_line(details)
    write_line()

    # Issues
    if issues:
        pdf.set_font("DejaVu", size=12)
        write_line("Issues:")
        pdf.set_font("DejaVu", size=11)
        for issue in issues:
            severity = (issue.get("severity") or "").upper()
            category = issue.get("category", "")
            message = issue.get("message", "")
            file = issue.get("file", "unknown")
            line_start = issue.get("line_start", 0)
            line_end = issue.get("line_end", 0)
            suggestion = issue.get("suggestion", "")
            code_patch = issue.get("code_patch") or ""

            write_line(f"[{severity}] [{category}] {message}")
            write_line(f"  File: {file}, Lines: {line_start}-{line_end}")
            if suggestion:
                write_line(f"  Suggestion: {suggestion}")
            if code_patch.strip():
                write_line("  Code patch:")
                write_line(code_patch)
            write_line()

    #export
    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer.read()


# SIDEBAR - NAVIGATION

st.sidebar.title("AI Code Review Assistant")

page = st.sidebar.radio(
    "Navigation",
    ["Upload Code", "Review History"]
)


# PAGE 1: UPLOAD + REVIEW

if page == "Upload Code":
    st.title("AI-Powered Code Review")
    st.write("Upload your source code files and get an instant AI review with severity-tagged issues.")

    uploaded_files = st.file_uploader(
        label="Upload one or more code files",
        type=["py", "js", "java", "cpp", "c", "go", "php", "sql", "html", "css", "sh", "txt"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        st.subheader("Detected languages")
        for f in uploaded_files:
            lang = detect_language_from_filename(f.name)
            st.write(f"• `{f.name}` → {lang}")

    if st.button("Analyze Code"):
        if not uploaded_files:
            st.warning("Please upload at least one file.")
        else:
            with st.spinner("Analyzing with AI..."):
                try:
                    files = [
                        ("files", (file.name, file.getvalue(), file.type or "text/plain"))
                        for file in uploaded_files
                    ]

                    response = requests.post(
                        f"{BACKEND_URL}/api/review",
                        files=files,
                        timeout=180,
                    )

                    if response.status_code != 200:
                        st.error(f"Backend error: {response.text}")
                    else:
                        data = response.json()

                        st.success("Review completed and saved to database!")

                        filenames_str = ", ".join([f.name for f in uploaded_files])
                        languages_str = ", ".join(
                            {detect_language_from_filename(f.name) for f in uploaded_files}
                        )

                        #Code Quality Dashboard
                        st.subheader("Code Quality Dashboard")
                        
                        quality_score = data.get("quality_score", 5.0)
                        metrics = data.get("metrics", {})
                        strengths = data.get("strengths", [])
                        issues = data.get("issues") or []
                        
                        valid_issues = [
                            i for i in issues
                            if isinstance(i, dict)
                            and i.get("severity")
                            and i.get("message")
                        ]
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Quality Score", f"{quality_score}/10", 
                                     delta="Good" if quality_score >= 7 else "Needs Work")
                        
                        with col2:
                            total_issues = len(valid_issues)
                            critical_issues = len([i for i in valid_issues if i.get('severity') == 'critical'])
                            st.metric("Total Issues", total_issues, 
                                     delta=f"{critical_issues} Critical", delta_color="inverse")
                        
                        with col3:
                            if metrics:
                                total_lines = sum(m.get('code_lines', 0) for m in metrics.values())
                                st.metric("Lines of Code", total_lines)
                        
                        # Code Metrics Table
                        if metrics:
                            st.markdown("**File Metrics**")
                            for fname, m in metrics.items():
                                with st.expander(f"{fname}"):
                                    st.write(f"- Total Lines: {m['total_lines']}")
                                    st.write(f"- Code Lines: {m['code_lines']}")
                                    st.write(f"- Comments: {m['comment_ratio']}%")
                                    st.write(f"- Complexity Score: {m['complexity_score']}")
                        
                        # Strengths section
                        if strengths:
                            st.markdown("**Code Strengths**")
                            for strength in strengths:
                                st.success(strength)

                        st.subheader("Summary")
                        st.write(data.get("summary", ""))

                        st.subheader("Detailed Review")
                        st.write(data.get("details", ""))

                        # Issues (filtered & grouped)
                        if valid_issues:
                            st.subheader("Issues by severity")
                            grouped = group_issues_by_severity(valid_issues)
                            for sev in SEVERITY_ORDER:
                                if sev in grouped and grouped[sev]:
                                    st.markdown(f"### {sev.upper()}")
                                    for issue in grouped[sev]:
                                        render_issue(issue)
                        else:
                            st.success("No significant issues detected in this code.")

                        # PDF export
                        pdf_bytes = build_pdf_report(
                            {**data, "issues": valid_issues},
                            filenames_str,
                            languages_str,
                        )
                        st.subheader("Export")
                        st.download_button(
                            label="Download PDF report",
                            data=pdf_bytes,
                            file_name=f"code_review_{data.get('id', 'report')}.pdf",
                            mime="application/pdf",
                        )

                        st.subheader("Review ID (Saved in DB)")
                        st.code(data.get("id"))

                except Exception as e:
                    st.error(f"Unexpected error: {e}")


# PAGE 2: REVIEW HISTORY

elif page == "Review History":
    st.title("Review History")
    st.write("Browse all previously saved review reports.")

    try:
        limit = st.slider("Number of recent reviews", 1, 20, 10)

        response = requests.get(
            f"{BACKEND_URL}/api/reports",
            params={"limit": limit},
            timeout=60,
        )

        if response.status_code != 200:
            st.error(f"Backend error: {response.text}")
        else:
            reports = response.json()

            if not reports:
                st.info("No reviews found yet.")
            else:
                selected_report_id = st.selectbox(
                    "Select a review to view details",
                    options=[r["id"] for r in reports],
                    format_func=lambda x: f"Review ID {x}",
                )

                selected = next(
                    (r for r in reports if r["id"] == selected_report_id),
                    None,
                )

                if selected:
                    st.subheader("Selected Review Summary")
                    st.write(f"**Files:** {selected['filenames']}")
                    st.write(f"**Created At:** {selected['created_at']}")
                    st.write(selected["summary"])

                # Fetch full detail
                detail_response = requests.get(
                    f"{BACKEND_URL}/api/reports/{selected_report_id}",
                    timeout=60,
                )

                if detail_response.status_code == 200:
                    detail = detail_response.json()

                    st.subheader("Full Detailed Review")
                    st.write(detail.get("details", ""))

                    issues = detail.get("issues") or []
                    valid_issues = [
                        i for i in issues
                        if isinstance(i, dict)
                        and i.get("severity")
                        and i.get("message")
                    ]

                    if valid_issues:
                        st.subheader("🚦 Issues by severity")
                        grouped = group_issues_by_severity(valid_issues)
                        for sev in SEVERITY_ORDER:
                            if sev in grouped and grouped[sev]:
                                st.markdown(f"### {sev.upper()}") 
                                for issue in grouped[sev]:
                                    render_issue(issue)
                    else:
                        st.success("No significant issues recorded for this review.")

                    # PDF export from history view
                    filenames_str = selected["filenames"]
                    languages_str = "Various"
                    pdf_bytes = build_pdf_report(
                        {**detail, "issues": valid_issues},
                        filenames_str,
                        languages_str,
                    )
                    st.subheader("Export")
                    st.download_button(
                        label="Download PDF report",
                        data=pdf_bytes,
                        file_name=f"code_review_{detail.get('id', 'report')}.pdf",
                        mime="application/pdf",
                    )

                else:
                    st.error("Failed to load detailed report.")

    except Exception as e:
        st.error(f"Unexpected error: {e}")