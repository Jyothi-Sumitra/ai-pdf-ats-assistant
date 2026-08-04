const pdfUpload = document.getElementById("pdf-upload");
const fileInfo = document.getElementById("file-info");
const statusText = document.getElementById("status");

const questionInput = document.getElementById("question-input");
const sendButton = document.getElementById("send-button");

const bottomQuestionInput = document.getElementById("bottom-question-input");
const bottomSendButton = document.getElementById("bottom-send-button");

const chatMessages = document.getElementById("chat-messages");

const quickActions = document.querySelectorAll(".quick-action");
const suggestionCards = document.querySelectorAll(".suggestion-card");

const newChatButton = document.querySelector(".new-chat-button");

let documentReady = false;


/* ---------------- PDF UPLOAD ---------------- */

pdfUpload.addEventListener("change", async () => {

    const file = pdfUpload.files[0];

    if (!file) return;

    fileInfo.textContent = `📄 ${file.name}`;
    statusText.textContent = "Processing...";

    setInputsEnabled(false);

    const formData = new FormData();
    formData.append("file", file);

    try {

        const response = await fetch("/upload", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error("Upload failed");
        }

        documentReady = true;

        statusText.textContent = "● Document ready";
        fileInfo.textContent = `📄 ${data.filename}`;

        setInputsEnabled(true);

        questionInput.placeholder =
            "Ask anything about your document...";

        bottomQuestionInput.placeholder =
            "Ask anything about your document...";

        questionInput.focus();

    } catch (error) {

        documentReady = false;

        statusText.textContent = "Upload failed";

        fileInfo.textContent =
            "❌ Something went wrong while processing the PDF.";

        setInputsEnabled(false);

        console.error(error);
    }
});


/* ---------------- SEND QUESTION ---------------- */

async function sendQuestion(question = null) {

    if (!documentReady) return;

    const activeQuestion =
        question ||
        bottomQuestionInput.value.trim() ||
        questionInput.value.trim();

    if (!activeQuestion) return;

    removeWelcomeMessage();

    questionInput.value = "";
    bottomQuestionInput.value = "";

    addMessage(
        "You",
        activeQuestion,
        "user-message"
    );

    setInputsEnabled(false);

    const loadingMessage = addMessage(
        "Assistant",
        "Thinking...",
        "assistant-message"
    );

    try {

        const response = await fetch("/chat", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                question: activeQuestion
            })
        });

        const data = await response.json();

        loadingMessage
            .querySelector(".message-content")
            .textContent =
                data.answer ||
                data.error ||
                "Something went wrong.";

    } catch (error) {

        loadingMessage
            .querySelector(".message-content")
            .textContent =
                "Sorry, something went wrong while generating the answer.";

        console.error(error);

    } finally {

        setInputsEnabled(true);

        bottomQuestionInput.focus();

        scrollToBottom();
    }
}


/* ---------------- DISPLAY MESSAGES ---------------- */

function addMessage(label, content, className) {

    const message = document.createElement("div");

    message.className = `message ${className}`;

    const messageLabel =
        document.createElement("div");

    messageLabel.className = "message-label";
    messageLabel.textContent = label;

    const messageContent =
        document.createElement("div");

    messageContent.className = "message-content";
    messageContent.textContent = content;

    message.appendChild(messageLabel);
    message.appendChild(messageContent);

    chatMessages.appendChild(message);

    scrollToBottom();

    return message;
}


/* ---------------- INPUT STATE ---------------- */

function setInputsEnabled(enabled) {

    questionInput.disabled = !enabled;
    sendButton.disabled = !enabled;

    bottomQuestionInput.disabled = !enabled;
    bottomSendButton.disabled = !enabled;
}


/* ---------------- HELPERS ---------------- */

function removeWelcomeMessage() {

    const welcome =
        document.querySelector(".welcome-message");

    if (welcome) {
        welcome.remove();
    }
}


function scrollToBottom() {

    chatMessages.scrollTop =
        chatMessages.scrollHeight;
}


/* ---------------- MAIN COMPOSER ---------------- */

sendButton.addEventListener("click", () => {

    const question =
        questionInput.value.trim();

    sendQuestion(question);
});


questionInput.addEventListener(
    "keydown",
    (event) => {

        if (
            event.key === "Enter" &&
            !event.shiftKey
        ) {

            event.preventDefault();

            const question =
                questionInput.value.trim();

            sendQuestion(question);
        }
    }
);


/* ---------------- BOTTOM COMPOSER ---------------- */

bottomSendButton.addEventListener(
    "click",
    () => {

        const question =
            bottomQuestionInput.value.trim();

        sendQuestion(question);
    }
);


bottomQuestionInput.addEventListener(
    "keydown",
    (event) => {

        if (
            event.key === "Enter" &&
            !event.shiftKey
        ) {

            event.preventDefault();

            const question =
                bottomQuestionInput.value.trim();

            sendQuestion(question);
        }
    }
);


/* ---------------- QUICK ACTIONS ---------------- */

quickActions.forEach((button) => {

    button.addEventListener("click", () => {

        if (!documentReady) return;

        const question =
            button.dataset.question;

        sendQuestion(question);
    });
});


/* ---------------- SUGGESTION CARDS ---------------- */

suggestionCards.forEach((card) => {

    card.addEventListener("click", () => {

        if (!documentReady) return;

        const question =
            card.dataset.question;

        sendQuestion(question);
    });
});

/* ---------------- NEW CHAT ---------------- */

newChatButton.addEventListener("click", async () => {

    try {

        await fetch("/new-chat", {
            method: "POST"
        });

        chatMessages.innerHTML = `
            <div class="welcome-message">

                <div class="hero-orb">
                    <div class="orb-core">✦</div>
                </div>

                <h1>Start a new conversation</h1>

                <p class="welcome-subtitle">
                    Your document is still loaded.
                    Ask a new question whenever you're ready.
                </p>

            </div>
        `;

        questionInput.value = "";
        bottomQuestionInput.value = "";

        if (documentReady) {
            bottomQuestionInput.focus();
        }

    } catch (error) {

        console.error(
            "Failed to start new chat:",
            error
        );
    }
});