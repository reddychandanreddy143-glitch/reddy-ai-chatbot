document.addEventListener("DOMContentLoaded", () => {
    const chatForm = document.getElementById("chat-form");
    const userInput = document.getElementById("user-input");
    const messagesContainer = document.getElementById("messages-container");
    const chatViewport = document.getElementById("chat-viewport");
    const geminiLoading = document.getElementById("gemini-loading");
    const heroWelcome = document.getElementById("hero-welcome");
    const promptCards = document.querySelectorAll(".prompt-card");
    const newChatBtn = document.getElementById("new-chat-btn");

    // Auth Elements
    const authModal = document.getElementById("auth-modal");
    const openAuthBtn = document.getElementById("open-auth-btn");
    const authClose = document.getElementById("auth-close");
    const tabLogin = document.getElementById("tab-login");
    const tabSignup = document.getElementById("tab-signup");
    const formLogin = document.getElementById("form-login");
    const formSignup = document.getElementById("form-signup");
    const logoutBtn = document.getElementById("logout-btn");
    const loginError = document.getElementById("login-error");
    const signupError = document.getElementById("signup-error");

    if (typeof marked !== "undefined") {
        marked.setOptions({
            breaks: true,
            highlight: function(code, lang) {
                if (lang && hljs.getLanguage(lang)) {
                    return hljs.highlight(code, { language: lang }).value;
                }
                return hljs.highlightAuto(code).value;
            }
        });
    }

    function createNewSessionId() {
        return "sess_" + Date.now() + "_" + Math.random().toString(36).substring(2, 8);
    }

    // Active session ID exists strictly in the browser tab's memory for context retention
    let activeSessionId = createNewSessionId();

    // Reset current search session
    if (newChatBtn) {
        newChatBtn.addEventListener("click", () => {
            activeSessionId = createNewSessionId();
            messagesContainer.innerHTML = "";
            if (heroWelcome) {
                heroWelcome.style.display = "flex";
                messagesContainer.appendChild(heroWelcome);
            }
            userInput.value = "";
            userInput.style.height = "auto";
            userInput.focus();
        });
    }

    // Auth Event Handlers
    if (openAuthBtn) openAuthBtn.addEventListener("click", () => authModal.style.display = "flex");
    if (authClose) authClose.addEventListener("click", () => authModal.style.display = "none");

    if (tabLogin && tabSignup) {
        tabLogin.addEventListener("click", () => {
            tabLogin.classList.add("active");
            tabSignup.classList.remove("active");
            formLogin.style.display = "flex";
            formSignup.style.display = "none";
        });

        tabSignup.addEventListener("click", () => {
            tabSignup.classList.add("active");
            tabLogin.classList.remove("active");
            formSignup.style.display = "flex";
            formLogin.style.display = "none";
        });
    }

    if (formLogin) {
        formLogin.addEventListener("submit", async (e) => {
            e.preventDefault();
            loginError.textContent = "";
            const identifier = document.getElementById("login-identifier").value.trim();
            const password = document.getElementById("login-password").value;

            try {
                const res = await fetch("/api/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ identifier, password })
                });
                const data = await res.json();
                if (data.status === "success") {
                    window.location.reload();
                } else {
                    loginError.textContent = data.message || "Invalid credentials.";
                }
            } catch {
                loginError.textContent = "Unable to connect to login service.";
            }
        });
    }

    if (formSignup) {
        formSignup.addEventListener("submit", async (e) => {
            e.preventDefault();
            signupError.textContent = "";
            const username = document.getElementById("signup-username").value.trim();
            const email = document.getElementById("signup-email").value.trim();
            const password = document.getElementById("signup-password").value;

            try {
                const res = await fetch("/api/register", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username, email, password })
                });
                const data = await res.json();
                if (data.status === "success") {
                    tabLogin.click();
                    loginError.style.color = "#34a853";
                    loginError.textContent = "Account created! Please log in.";
                } else {
                    signupError.textContent = data.message || "Signup failed.";
                }
            } catch {
                signupError.textContent = "Error connecting to server.";
            }
        });
    }

    if (logoutBtn) {
        logoutBtn.addEventListener("click", async () => {
            await fetch("/api/logout", { method: "POST" });
            window.location.reload();
        });
    }

    // Auto-expanding input textarea
    userInput.addEventListener("input", function() {
        this.style.height = "auto";
        this.style.height = (this.scrollHeight) + "px";
        if (this.value === "") this.style.height = "auto";
    });

    userInput.addEventListener("keydown", function(e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event("submit"));
        }
    });

    promptCards.forEach(card => {
        card.addEventListener("click", () => {
            userInput.value = card.getAttribute("data-prompt");
            chatForm.dispatchEvent(new Event("submit"));
        });
    });

    function appendMessageRow(sender, rawText) {
        if (heroWelcome && heroWelcome.parentNode === messagesContainer) {
            heroWelcome.style.display = "none";
        }

        const rowDiv = document.createElement("div");
        rowDiv.classList.add("message-row", `${sender}-row`);

        if (sender === "bot") {
            const avatar = document.createElement("div");
            avatar.classList.add("avatar", "bot-avatar");
            avatar.innerHTML = "✦";
            rowDiv.appendChild(avatar);

            const bubble = document.createElement("div");
            bubble.classList.add("message-bubble", "bot-bubble");
            
            if (typeof marked !== "undefined") {
                bubble.innerHTML = marked.parse(rawText);
                bubble.querySelectorAll('pre code').forEach((el) => {
                    hljs.highlightElement(el);
                });
            } else {
                bubble.textContent = rawText;
            }
            rowDiv.appendChild(bubble);
        } else {
            const bubble = document.createElement("div");
            bubble.classList.add("message-bubble", "user-bubble");
            bubble.textContent = rawText;
            rowDiv.appendChild(bubble);

            const avatar = document.createElement("div");
            avatar.classList.add("avatar", "user-avatar");
            avatar.innerHTML = "U";
            rowDiv.appendChild(avatar);
        }

        messagesContainer.appendChild(rowDiv);
        chatViewport.scrollTop = chatViewport.scrollHeight;
    }

    async function handleChatSubmit(e) {
        e.preventDefault();
        const message = userInput.value.trim();
        if (!message) return;

        appendMessageRow("user", message);
        userInput.value = "";
        userInput.style.height = "auto";
        userInput.focus();

        geminiLoading.style.display = "flex";
        chatViewport.scrollTop = chatViewport.scrollHeight;

        try {
            const response = await fetch("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    message: message, 
                    session_id: activeSessionId
                })
            });

            const data = await response.json();
            geminiLoading.style.display = "none";

            if (data.status === "success" || data.status === "warning") {
                appendMessageRow("bot", data.response);
            } else {
                appendMessageRow("bot", "An unexpected error occurred. Please try again.");
            }
        } catch {
            geminiLoading.style.display = "none";
            appendMessageRow("bot", "⚠️ Unable to connect to Reddy AI server.");
        }
    }

    chatForm.addEventListener("submit", handleChatSubmit);
});