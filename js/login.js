const loginForm = document.getElementById("loginForm");
const passwordInput = document.getElementById("password");
const passwordToggle = document.getElementById("passwordToggle");
const loginMessage = document.getElementById("loginMessage");

passwordToggle.addEventListener("click", function () {
    if (passwordInput.type === "password") {
        passwordInput.type = "text";
        passwordToggle.textContent = "Hide";
    } else {
        passwordInput.type = "password";
        passwordToggle.textContent = "Show";
    }
});

loginForm.addEventListener("submit", function (event) {
    event.preventDefault();

    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;

    if (username === "admin" && password === "1234") {

        loginMessage.style.color = "#07868a";
        loginMessage.textContent = "Login successful. Opening dashboard...";

        sessionStorage.setItem("gloveLoggedIn", "true");

        setTimeout(function () {
            window.location.href = "dashboard.html";
        }, 700);

    } else {

        loginMessage.style.color = "#d64b4b";
        loginMessage.textContent = "Invalid username or password.";
    }
});