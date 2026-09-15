console.log("PayFlow Authentication Loaded");

// Password
const password = document.getElementById("password");
const togglePassword = document.getElementById("togglePassword");

togglePassword.addEventListener("click", function () {

    if (password.type === "password") {

        password.type = "text";
        togglePassword.textContent = "🙈";

    } else {

        password.type = "password";
        togglePassword.textContent = "👁";

    }

});

// Confirm Password
const confirmPassword = document.getElementById("confirmPassword");
const toggleConfirmPassword = document.getElementById("toggleConfirmPassword");

toggleConfirmPassword.addEventListener("click", function () {

    if (confirmPassword.type === "password") {

        confirmPassword.type = "text";
        toggleConfirmPassword.textContent = "🙈";

    } else {

        confirmPassword.type = "password";
        toggleConfirmPassword.textContent = "👁";

    }

});
// -------------------------------
// Password Strength Checker
// -------------------------------

const strengthFill = document.getElementById("strengthFill");
const strengthText = document.getElementById("strengthText");

password.addEventListener("input", function () {

    const value = password.value;

    let strength = 0;

    if (value.length >= 8)
        strength++;

    if (/[A-Z]/.test(value))
        strength++;

    if (/[a-z]/.test(value))
        strength++;

    if (/[0-9]/.test(value))
        strength++;

    if (/[^A-Za-z0-9]/.test(value))
        strength++;

    switch (strength) {

        case 0:
        case 1:

            strengthFill.style.width = "20%";
            strengthFill.style.background = "#ef4444";
            strengthText.textContent = "Weak";
            strengthText.style.color = "#ef4444";
            break;

        case 2:
        case 3:

            strengthFill.style.width = "50%";
            strengthFill.style.background = "#f59e0b";
            strengthText.textContent = "Medium";
            strengthText.style.color = "#f59e0b";
            break;

        case 4:

            strengthFill.style.width = "75%";
            strengthFill.style.background = "#3b82f6";
            strengthText.textContent = "Good";
            strengthText.style.color = "#3b82f6";
            break;

        case 5:

            strengthFill.style.width = "100%";
            strengthFill.style.background = "#22c55e";
            strengthText.textContent = "Strong";
            strengthText.style.color = "#22c55e";
            break;

    }

});
// ------------------------------------
// Password Validation
// ------------------------------------

const passwordError = document.getElementById("passwordError");
const confirmMessage = document.getElementById("confirmMessage");

const email = document.getElementById("email");
const phone = document.getElementById("phone");
const fullname = document.getElementById("fullname");

function hasSequentialCharacters(text){

    const lower = text.toLowerCase();

    const sequences = [
        "abcdefghijklmnopqrstuvwxyz",
        "0123456789",
        "9876543210",
        "zyxwvutsrqponmlkjihgfedcba"
    ];

    for(const seq of sequences){

        for(let i=0;i<=seq.length-4;i++){

            if(lower.includes(seq.substring(i,i+4))){

                return true;

            }

        }

    }

    return false;

}

password.addEventListener("input", function(){

    passwordError.textContent = "";

    const value = password.value;

    if(value.includes(" ")){

        passwordError.textContent = "❌ Password cannot contain spaces.";
        return;

    }

    if(value.length < 8 || value.length > 10){

        passwordError.textContent = "❌ Password must be 8–10 characters.";
        return;

    }

    if(value.toLowerCase() === "password"){

        passwordError.textContent = "❌ 'password' cannot be used.";
        return;

    }

    if(value === email.value ||
       value === phone.value ||
       value === fullname.value){

        passwordError.textContent =
        "❌ Password cannot be the same as your personal information.";
        return;

    }

    if(hasSequentialCharacters(value)){

        passwordError.textContent =
        "❌ Sequential passwords are not allowed.";
        return;

    }

});
confirmPassword.addEventListener("input", function(){

    if(confirmPassword.value === ""){

        confirmMessage.textContent = "";
        return;

    }

    if(password.value === confirmPassword.value){

        confirmMessage.textContent = "✅ Passwords match";
        confirmMessage.style.color = "green";

    }
    else{

        confirmMessage.textContent = "❌ Passwords do not match";
        confirmMessage.style.color = "red";

    }

});
// ------------------------------------
// Email Validation
// ------------------------------------

const emailMessage = document.getElementById("emailMessage");

email.addEventListener("input", function () {

    // Convert to lowercase automatically
    email.value = email.value.toLowerCase();

    // Remove spaces
    email.value = email.value.replace(/\s/g, "");

    const emailPattern =
        /^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$/;

    if(email.value === ""){

        emailMessage.textContent = "";
        return;

    }

    if(emailPattern.test(email.value)){

        emailMessage.textContent = "✅ Valid email";
        emailMessage.style.color = "green";

    }
    else{

        emailMessage.textContent = "❌ Invalid email address";
        emailMessage.style.color = "red";

    }

});

// ------------------------------------
// Phone Number Validation
// ------------------------------------

const phoneMessage = document.getElementById("phoneMessage");

phone.addEventListener("input", function () {

    // Remove everything except digits
    phone.value = phone.value.replace(/\D/g, "");

    if (phone.value.length === 0) {

        phoneMessage.textContent = "";
        return;

    }

    if (phone.value.length < 10) {

        phoneMessage.textContent =
            "❌ Phone number must contain 10 digits.";
        phoneMessage.style.color = "red";
        return;

    }

    const firstDigit = phone.value.charAt(0);

    if (["6", "7", "8", "9"].includes(firstDigit)) {

        phoneMessage.textContent =
            "✅ Valid Indian mobile number.";
        phoneMessage.style.color = "green";

    } else {

        phoneMessage.textContent =
            "❌ Indian mobile numbers must start with 6, 7, 8 or 9.";
        phoneMessage.style.color = "red";

    }

});
// ------------------------------------
// Complete Registration Validation
// ------------------------------------

const registerForm = document.getElementById("registerForm");
const terms = document.getElementById("terms");
const formMessage = document.getElementById("formMessage");

registerForm.addEventListener("submit", function (event) {

    formMessage.textContent = "";
    formMessage.style.color = "red";

    // Full Name
    if (fullname.value.trim() === "") {

        event.preventDefault();

        formMessage.textContent =
        "❌ Please enter your full name.";

        fullname.focus();
        return;

    }

    // Email
    if (emailMessage.textContent !== "✅ Valid email") {

        event.preventDefault();

        formMessage.textContent =
        "❌ Please enter a valid email.";

        email.focus();
        return;

    }

    // Phone
    if (phoneMessage.textContent !==
        "✅ Valid Indian mobile number.") {

        event.preventDefault();

        formMessage.textContent =
        "❌ Please enter a valid mobile number.";

        phone.focus();
        return;

    }

    // Password
    if (passwordError.textContent !== "") {

        event.preventDefault();

        formMessage.textContent =
        passwordError.textContent;

        password.focus();
        return;

    }

    // Confirm Password
    if (confirmMessage.textContent !==
        "✅ Passwords match") {

        event.preventDefault();

        formMessage.textContent =
        "❌ Passwords do not match.";

        confirmPassword.focus();
        return;

    }

    // Terms
    if (!terms.checked) {

        event.preventDefault();

        formMessage.textContent =
        "❌ Please accept the Terms & Conditions.";

        return;

    }

    // Everything is valid
    formMessage.style.color = "green";
    formMessage.textContent =
    "✅ Validation Successful. Registering...";

    // Do NOT call event.preventDefault() here.
    // The browser will now submit the form to Flask.

});
// ---------------------
// Login Password Toggle
// ---------------------

const loginPassword = document.getElementById("loginPassword");
const toggleLoginPassword = document.getElementById("toggleLoginPassword");

if (loginPassword && toggleLoginPassword) {

    toggleLoginPassword.addEventListener("click", function () {

        if (loginPassword.type === "password") {

            loginPassword.type = "text";
            toggleLoginPassword.textContent = "🙈";

        } else {

            loginPassword.type = "password";
            toggleLoginPassword.textContent = "👁";

        }

    });

}