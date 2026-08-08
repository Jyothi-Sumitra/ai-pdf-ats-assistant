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

const bottomInputContainer =
    document.getElementById("bottom-input-container");

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
            const filenameLabel = document.createElement("span");
            const deleteButton = document.createElement("button");

            item.className = "document-item";
            filenameLabel.className = "document-name";
            filenameLabel.textContent = `📄 ${filename}`;

            deleteButton.className = "delete-document-button";
            deleteButton.type = "button";
            deleteButton.title = `Delete ${filename}`;
            deleteButton.setAttribute("aria-label", `Delete ${filename}`);
            deleteButton.textContent = "×";

            deleteButton.addEventListener("click", async (event) => {
                event.stopPropagation();
                await deleteDocument(filename);
            });

            item.addEventListener("click", () => {
                documentSelect.value = filename;
                documentSelect.dispatchEvent(new Event("change"));
            });

            item.append(filenameLabel, deleteButton);

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


/* =========================================================
   DELETE DOCUMENT
========================================================= */

async function deleteDocument(filename) {

    if (!window.confirm(`Delete ${filename}? This cannot be undone.`)) {
        return;
    }

    try {

        const response = await fetch(
            `/documents/${encodeURIComponent(filename)}`,
            { method: "DELETE" }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Failed to delete document");
        }

        await loadDocuments();

        if (data.documents.length === 0) {
            documentReady = false;
            fileInfo.hidden = true;
            statusText.textContent = "No document";
            bottomInputContainer.hidden = true;
        } else {
            statusText.textContent = "● Document ready";
            fileInfo.hidden = false;
            fileInfo.textContent = `📄 ${documentSelect.value}`;
        }

    } catch (error) {
        console.error("Document deletion failed:", error);
        statusText.textContent = "Delete failed";
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


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.error ||
                "Upload failed"
            );
        }


        /* Refresh dropdown and select uploaded PDF */

        await loadDocuments(
            data.filename
        );


        documentReady = true;

        fileInfo.textContent =
            `📄 ${data.filename}`;

        fileInfo.hidden = false;

        statusText.textContent =
            "● Document ready";


        setInputsEnabled(true);


        questionInput.placeholder = webSearchEnabled
            ? "Ask a question to search the web..."
            : "Ask anything about your document...";



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

    fileInfo.hidden = false;

    questionInput.placeholder =
        "Ask anything about your document...";

});

/* =========================================================
   SEND QUESTION
========================================================= */

async function sendQuestion(question = null, searchWeb = false) {

    if (!documentReady && !webSearchEnabled) {
        return;
    }


    const activeQuestion =
        question ||
        questionInput.value.trim();


    if (!activeQuestion) {
        return;
    }


    if (!webSearchEnabled && !documentSelect.value) {

        addMessage(
            "Assistant",
            "Please select a document first.",
            "assistant-message"
        );

        return;
    }


    removeWelcomeMessage();

    bottomInputContainer.hidden = false;

    questionInput.value = "";
    bottomQuestionInput.value = "";

    addMessage(
        "You",
        searchWeb ? "Yes, search the web." : activeQuestion,
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
                        webSearchEnabled,

                    search_web:
                        searchWeb
                })
            }
        );


        const data =
            await response.json();


        const messageContent = loadingMessage.querySelector(".message-content");

        messageContent.textContent =
            data.answer || data.error || "Something went wrong.";

        if (data.needs_web_confirmation) {
            addWebSearchConfirmation(loadingMessage, activeQuestion);
        }


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


function addWebSearchConfirmation(message, question) {

    const actions = document.createElement("div");
    const confirmButton = document.createElement("button");
    const cancelButton = document.createElement("button");

    actions.className = "web-search-confirmation";
    confirmButton.type = "button";
    confirmButton.textContent = "Search the web";
    cancelButton.type = "button";
    cancelButton.textContent = "No, keep PDF mode";

    confirmButton.addEventListener("click", () => {
        actions.remove();
        sendQuestion(question, true);
    });

    cancelButton.addEventListener("click", () => {
        actions.remove();
    });

    actions.append(confirmButton, cancelButton);
    message.querySelector(".message-content").appendChild(actions);
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
        documentSelect.disabled = !documentReady;
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
        sendQuestion(bottomQuestionInput.value.trim());
    }
);

bottomQuestionInput.addEventListener(
    "keydown",
    (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendQuestion(bottomQuestionInput.value.trim());
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

            bottomInputContainer.hidden = true;

            chatMessages
                .querySelectorAll(".message")
                .forEach(message => message.remove());

            questionInput.value = "";

            if (documentReady) {
                questionInput.focus();
            }


            questionInput.value = "";
            bottomQuestionInput.value = "";
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

    const canAskQuestion = documentReady || webSearchEnabled;

    webSearchToggle.classList.toggle(
        "active",
        webSearchEnabled
    );

    webSearchToggle.setAttribute(
        "aria-pressed",
        String(webSearchEnabled)
    );

    webSearchToggle.textContent = webSearchEnabled
        ? "🌐 Web Search On"
        : "🌐 Web Search";

    questionInput.placeholder = webSearchEnabled
        ? "Ask a question to search the web..."
        : documentReady
            ? "Ask anything about your document..."
            : "Upload a PDF to start asking questions...";

    setInputsEnabled(canAskQuestion);

    statusText.textContent = webSearchEnabled
        ? documentReady
            ? "● Document ready · Web fallback enabled"
            : "● Web search enabled"
        : documentReady
            ? "● Document ready"
            : "No document";

    if (webSearchEnabled) {
        questionInput.focus();
    }

});


/* =========================================================
   INITIAL PAGE LOAD
========================================================= */

/*
If documents already exist in documents_store during the
current server session, load them when the page refreshes.
*/

loadDocuments();
