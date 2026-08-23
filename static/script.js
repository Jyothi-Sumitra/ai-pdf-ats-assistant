// Shows a "waking up" banner if the backend is cold-starting
async function checkServerAwake() {
  const banner = document.getElementById("wake-banner");
  const start = Date.now();

  try {
    const res = await fetch("/health");
    const elapsed = Date.now() - start;

    // If it took more than ~2s, it was likely a cold start
    if (elapsed > 2000 && banner) {
      banner.style.display = "none";
    }
  } catch (err) {
    if (banner) banner.style.display = "block";
  }
}

// // Call this as soon as the page loads
// <<<<<<< HEAD

// =======
// >>>>>>> 4f7b8ad (Fix PDF upload script)
window.addEventListener("DOMContentLoaded", () => {
  const banner = document.createElement("div");
  banner.id = "wake-banner";
  banner.textContent = "⏳ Waking up the server — this can take up to a minute on first load...";
  banner.style.cssText =
    "position:fixed;top:0;left:0;right:0;background:#fff3cd;color:#856404;" +
    "padding:10px;text-align:center;font-family:sans-serif;z-index:9999;display:none;";
  document.body.prepend(banner);

  // Show banner immediately, then hide once server responds
  banner.style.display = "block";
  fetch("/health")
    .then(() => { banner.style.display = "none"; })
    .catch(() => { /* keep banner visible, will retry naturally on next action */ });
});

/* =========================================================
   DOM ELEMENTS
========================================================= */

const pdfUpload = document.getElementById("pdf-upload");
const documentList = document.getElementById("document-list");
const fileInfo = document.getElementById("file-info");
const documentSelect = document.getElementById("document-select");

const statusText = document.getElementById("status");

const questionInput = document.getElementById("question-input");
const sendButton = document.getElementById("send-button");

const webSearchToggle = document.getElementById("web-search-toggle");
let webSearchEnabled = false;

const bottomQuestionInput =
    document.getElementById("bottom-question-input");

const bottomSendButton =
    document.getElementById("bottom-send-button");

const chatMessages =
    document.getElementById("chat-messages");

const quickActions =
    document.querySelectorAll(".quick-action");

const suggestionCards =
    document.querySelectorAll(".suggestion-card");

const newChatButton =
    document.querySelector(".new-chat-button");


let documentReady = false;


/* =========================================================
   LOAD DOCUMENTS
========================================================= */

async function loadDocuments(selectedFilename = null) {

    try {

        const response = await fetch("/documents");

        if (!response.ok) {
            throw new Error("Failed to fetch documents");
        }

        const data = await response.json();
        
        documentSelect.innerHTML = "";
        documentList.innerHTML = "";
        
        data.documents.forEach((filename) => {

            const option = document.createElement("option");

            option.value = filename;
            option.textContent = filename;

            documentSelect.appendChild(option);

            const item = document.createElement("div");
            const name = document.createElement("span");
            const deleteButton = document.createElement("button");

            item.className = "document-item";
            name.className = "document-name";
            name.textContent = `📄 ${filename}`;
            name.title = filename;

            deleteButton.className = "delete-document-button";
            deleteButton.type = "button";
            deleteButton.setAttribute("aria-label", `Delete ${filename}`);
            deleteButton.title = "Delete document";
            deleteButton.textContent = "×";
            deleteButton.addEventListener("click", () => {
                deleteDocument(filename);
            });

            item.appendChild(name);
            item.appendChild(deleteButton);

            documentList.appendChild(item);

        });

        if (selectedFilename) 
        {
            documentSelect.value = selectedFilename;
        } 
        
        else if (data.documents.length > 0) 
        {
            documentSelect.value = data.documents[0];
        }

        /* Update document state */

        documentReady =
            documentSelect.value !== "";

        setInputsEnabled(documentReady);

    } catch (error) {

        console.error(
            "Failed to load documents:",
            error
        );
    }
}


async function deleteDocument(filename) {
    if (!window.confirm(`Delete ${filename}?`)) {
        return;
    }

    try {
        const response = await fetch(
            `/documents/${encodeURIComponent(filename)}`,
            { method: "DELETE" }
        );
        const responseText = await response.text();
        const data = responseText ? JSON.parse(responseText) : {};

        if (!response.ok) {
            throw new Error(
                data.detail ||
                data.error ||
                `Delete failed (${response.status})`
            );
        }

        await loadDocuments();
        fileInfo.textContent = "";
        statusText.textContent = data.documents.length
            ? "Select a document"
            : "No document";
        questionInput.placeholder =
            "Upload a PDF to start asking questions...";
    } catch (error) {
        fileInfo.textContent = error.message || "Unable to delete document.";
        statusText.textContent = "Delete failed";
        console.error("Document deletion failed:", error);
    }
}


/* =========================================================
   PDF UPLOAD
========================================================= */

pdfUpload.addEventListener("change", async () => {

    const file = pdfUpload.files[0];

    if (!file) return;


    statusText.textContent =
        "Processing...";

    fileInfo.textContent =
        `Processing ${file.name}...`;

    setInputsEnabled(false);


    const formData = new FormData();

    formData.append(
        "file",
        file
    );


    try {

        const response = await fetch(
            "/upload",
            {
                method: "POST",
                body: formData
            }
        );


        const responseText = await response.text();
        let data = {};

        try {
            data = responseText ? JSON.parse(responseText) : {};
        } catch (parseError) {
            throw new Error(
                `Upload failed (${response.status}): ${responseText.slice(0, 160)}`
            );
        }


        if (!response.ok) {

            throw new Error(
                data.detail ||
                data.error ||
                `Upload failed (${response.status})`
            );
        }


        /* Refresh dropdown and select uploaded PDF */

        await loadDocuments(
            data.filename
        );


        documentReady = true;

        fileInfo.textContent =
            `📄 ${data.filename}`;

        statusText.textContent =
            "● Document ready";


        setInputsEnabled(true);


        questionInput.placeholder ="Ask anything about your document...";



        questionInput.focus();


        /*
        Allows uploading the same PDF again later.
        Without this, selecting the same file may not
        trigger the change event in some browsers.
        */

        pdfUpload.value = "";


    } catch (error) {

        statusText.textContent =
            "Upload failed";

        fileInfo.textContent =
            error.message ||
            "Something went wrong while processing the PDF.";


        /*
        Don't automatically destroy documentReady here.

        There may already be another valid document
        available in the dropdown.
        */

        documentReady =
            documentSelect.value !== "";

        setInputsEnabled(
            documentReady
        );


        console.error(
            "PDF upload failed:",
            error
        );
    }
});

/* =========================================================
   DOCUMENT SELECTION
========================================================= */

documentSelect.addEventListener("change", () => {

    const selectedDocument = documentSelect.value;

    documentReady = true;

    setInputsEnabled(true);

    statusText.textContent = "● Document ready";

    fileInfo.textContent =
        `📄 ${selectedDocument}`;

    questionInput.placeholder =
        "Ask anything about your document...";

});

/* =========================================================
   SEND QUESTION
========================================================= */

async function sendQuestion(question = null) {

    if (!documentReady) {
        return;
    }


    const activeQuestion =
        question ||
        questionInput.value.trim();


    if (!activeQuestion) {
        return;
    }


    if (!documentSelect.value) {

        addMessage(
            "Assistant",
            "Please select a document first.",
            "assistant-message"
        );

        return;
    }


    // removeWelcomeMessage();
    document.getElementById("bottom-composer").style.display = "block";
    document.querySelector(".hero-composer").style.display = "none";
    document.querySelector(".suggestion-grid").style.display = "none";
    // document.getElementById("chat-composer").classList.remove("hidden");

    questionInput.value = "";
    bottomQuestionInput.value = "";

    addMessage(
        "You",
        activeQuestion,
        "user-message"
    );


    setInputsEnabled(false);


    const loadingMessage =
        addMessage(
            "Assistant",
            "Thinking...",
            "assistant-message"
        );


    try {

        const response = await fetch(
            "/chat",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    question:
                        activeQuestion,

                    selected_document:
                        documentSelect.value,

                    use_web:
                        webSearchEnabled
                })
            }
        );


        const data =
            await response.json();


        loadingMessage
            .querySelector(
                ".message-content"
            )
            .textContent =
                data.answer ||
                data.error ||
                "Something went wrong.";


    } catch (error) {

        loadingMessage
            .querySelector(
                ".message-content"
            )
            .textContent =
                "Sorry, something went wrong while generating the answer.";


        console.error(
            "Chat request failed:",
            error
        );


    } finally {

        setInputsEnabled(true);
        bottomQuestionInput.focus();
        scrollToBottom();
    }
}


/* =========================================================
   DISPLAY MESSAGES
========================================================= */

function addMessage(
    label,
    content,
    className
) {

    const message =
        document.createElement("div");


    message.className =
        `message ${className}`;


    const messageLabel =
        document.createElement("div");


    messageLabel.className =
        "message-label";

    messageLabel.textContent =
        label;


    const messageContent =
        document.createElement("div");


    messageContent.className =
        "message-content";

    messageContent.textContent =
        content;


    message.appendChild(
        messageLabel
    );

    message.appendChild(
        messageContent
    );


    chatMessages.appendChild(
        message
    );


    scrollToBottom();


    return message;
}


/* =========================================================
   INPUT STATE
========================================================= */

function setInputsEnabled(enabled) {

    if (questionInput)
        questionInput.disabled = !enabled;

    if (sendButton)
        sendButton.disabled = !enabled;

    if (bottomQuestionInput)
        bottomQuestionInput.disabled = !enabled;

    if (bottomSendButton)
        bottomSendButton.disabled = !enabled;

    quickActions.forEach(button => {
        button.disabled = !enabled;
    });

    suggestionCards.forEach(card => {
        card.disabled = !enabled;
    });

    if (documentSelect)
        documentSelect.disabled = !enabled;
}


/* =========================================================
   HELPERS
========================================================= */

function removeWelcomeMessage() {

    const welcome =
        document.querySelector(".welcome-message");

    if (welcome) {

        welcome.style.display = "none";

    }
}


function scrollToBottom() {

    chatMessages.scrollTop =
        chatMessages.scrollHeight;
}


/* =========================================================
   MAIN COMPOSER
========================================================= */

sendButton.addEventListener(
    "click",
    () => {

        const question =
            questionInput.value.trim();

        sendQuestion(
            question
        );
    }
);


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

            sendQuestion(
                question
            );
        }
    }
);


/* =========================================================
   BOTTOM COMPOSER
========================================================= */

bottomSendButton.addEventListener(
    "click",
    () => {

        const question =
            bottomQuestionInput.value.trim();

        sendQuestion(
            question
        );
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
                bottomQuestionInput
                    .value
                    .trim();

            sendQuestion(
                question
            );
        }
    }
);


/* =========================================================
   QUICK ACTIONS
========================================================= */

quickActions.forEach(
    (button) => {

        button.addEventListener(
            "click",
            () => {

                if (!documentReady) {
                    return;
                }

                const question =
                    button.dataset.question;

                sendQuestion(
                    question
                );
            }
        );
    }
);


/* =========================================================
   SUGGESTION CARDS
========================================================= */

suggestionCards.forEach(
    (card) => {

        card.addEventListener(
            "click",
            () => {

                if (!documentReady) {
                    return;
                }

                const question =
                    card.dataset.question;

                sendQuestion(
                    question
                );
            }
        );
    }
);


/* =========================================================
   NEW CHAT
========================================================= */

newChatButton.addEventListener("click", async () => {

        try {

            await fetch(
                "/new-chat",
                {
                    method: "POST"
                }
            );


            const welcome = document.querySelector(".welcome-message");

            if (welcome) {
                welcome.style.display = "flex";
            }

            chatMessages
                .querySelectorAll(".message")
                .forEach(message => message.remove());

            questionInput.value = "";

            if (documentReady) {
                questionInput.focus();
            }


            questionInput.value = "";
            // bottomQuestionInput.value = "";
            if (documentReady) {
                questionInput.focus();
            }


        } catch (error) {

            console.error(
                "Failed to start new chat:",
                error
            );
        }
    }
);

webSearchToggle.addEventListener("click", () => {

    webSearchEnabled = !webSearchEnabled;

    webSearchToggle.classList.toggle(
        "active",
        webSearchEnabled
    );

});


/* =========================================================
   INITIAL PAGE LOAD
========================================================= */

/*
If documents already exist in documents_store during the
current server session, load them when the page refreshes.
*/

loadDocuments();
