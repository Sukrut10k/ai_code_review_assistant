function login(user, pass) {
    if (user == "admin" && pass == "1234") {  // hardcoded credentials
        console.log("Login successful");
    }
}

function add(a, b) {
    return a + b;   // JS type coercion risk
}

console.log(add("5", 10));  //outputs 510

document.getElementById("app").innerHTML = userInput;  //XSS vulnerability
