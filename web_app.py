from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import os
import shutil

from src.pdf_loader import load_pdf
from src.text_splitter import split_documents
from src.embeddings import get_embeddings
from src.vector_store import get_vector_store
from src.retriever import get_retriever
from src.chatbot import get_llm
from src.summarizer import summarize_document
from src.assistant import handle_question


# --------------------------------------------------
# FASTAPI APP
# --------------------------------------------------

app = FastAPI(
    title="AI PDF Assistant",
    description="Chat with PDF documents using Retrieval-Augmented Generation",
    version="2.0.0"
)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


# --------------------------------------------------
# GLOBAL STATE
# --------------------------------------------------

llm = get_llm()

# Stores all PDFs uploaded during the current server session.
#
# Example:
#
# documents_store = {
#     "Resume.pdf": {
#         "retriever": ...,
#         "chunks": [...],
#         "summary": None
#     },
#     "AI_Research.pdf": {
#         "retriever": ...,
#         "chunks": [...],
#         "summary": None
#     }
# }

documents_store = {}

chat_history = []


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.get("/")
def home():
    return FileResponse("static/index.html")


# --------------------------------------------------
# PDF UPLOAD
# --------------------------------------------------

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):

    global documents_store, chat_history

    # Make sure upload directory exists
    os.makedirs(
        "data/uploads",
        exist_ok=True
    )

    file_path = os.path.join(
        "data",
        "uploads",
        file.filename
    )

    # Save uploaded PDF
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(
            file.file,
            buffer
        )

    # Load PDF
    documents = load_pdf(file_path)

    # Split into chunks
    chunks = split_documents(documents)

    # Add filename metadata to every chunk.
    # This will be useful later for:
    #
    # Resume.pdf - Page 1
    # AI_Research.pdf - Page 4

    for chunk in chunks:
        chunk.metadata["filename"] = file.filename

    # Create embeddings
    embedding_model = get_embeddings()

    # Create/load this PDF's own vector database
    vector_store = get_vector_store(
        file_path,
        chunks,
        embedding_model
    )

    # Create retriever specifically for this document
    document_retriever = get_retriever(
        vector_store,
        chunks
    )

    # Register document
    documents_store[file.filename] = {
        "retriever": document_retriever,
        "chunks": chunks,
        "summary": None
    }

    # Start fresh conversation after upload
    chat_history = []

    return {
        "message": "PDF uploaded and processed successfully",
        "filename": file.filename,
        "pages": len(documents),
        "chunks": len(chunks),
        "documents": list(documents_store.keys())
    }


# --------------------------------------------------
# GET AVAILABLE DOCUMENTS
# --------------------------------------------------

@app.get("/documents")
def get_documents():

    return {
        "documents": list(
            documents_store.keys()
        )
    }


# --------------------------------------------------
# CHAT REQUEST MODEL
# --------------------------------------------------

class ChatRequest(BaseModel):
    question: str
    selected_document: str = ""
    use_web: bool = False
    search_web: bool = False


# --------------------------------------------------
# SUMMARY DETECTION
# --------------------------------------------------

def is_summary_request(question):

    summary_phrases = [
        "summarize",
        "summary",
        "what is this pdf about",
        "what is the pdf about",
        "what is this document about",
        "what is the document about",
        "overview of the pdf",
        "overview of the document"
    ]

    question = question.lower()

    return any(
        phrase in question
        for phrase in summary_phrases
    )


# --------------------------------------------------
# CHAT
# --------------------------------------------------

@app.post("/chat")
def chat(request: ChatRequest):

    global chat_history

    # Without an uploaded PDF, Web Search mode works as a normal web assistant.
    if request.selected_document not in documents_store:

        if not request.use_web:
            return {
                "error": "Please select a valid PDF first or enable Web Search."
            }

        result = handle_question(
            question=request.question,
            llm=llm,
            retriever=None,
            chat_history=chat_history,
            use_web=True
        )

        return result

    # A web fallback is performed only after the user confirms it in the UI.
    if request.search_web and request.use_web:

        return handle_question(
            question=request.question,
            llm=llm,
            retriever=None,
            chat_history=chat_history,
            use_web=True
        )

    # Get selected PDF information
    selected_pdf = documents_store[
        request.selected_document
    ]

    retriever = selected_pdf["retriever"]
    chunks = selected_pdf["chunks"]

    # ----------------------------------------------
    # DOCUMENT SUMMARY
    # ----------------------------------------------

    if is_summary_request(request.question):

        # Generate only once and cache it
        if selected_pdf["summary"] is None:

            selected_pdf["summary"] = summarize_document(
                chunks,
                llm
            )

        result = {
            "answer": selected_pdf["summary"],
            "route": "pdf",
            "sources": [
                {
                    "filename": request.selected_document
                }
            ]
        }

    # ----------------------------------------------
    # NORMAL PDF RAG
    # ----------------------------------------------

    else:

        result = handle_question(
            question=request.question,
            llm=llm,
            retriever=retriever,
            chat_history=chat_history,
            use_web=False
        )

        not_found_message = "I couldn't find that information in the document."

        if (
            request.use_web
            and not_found_message.lower() in result["answer"].lower()
        ):
            return {
                "answer": (
                    "I couldn't find that information in the document. "
                ),
                "route": "pdf",
                "sources": [],
                "needs_web_confirmation": True
            }

    # ----------------------------------------------
    # SAVE CONVERSATION
    # ----------------------------------------------

    chat_history.append(
        f"User: {request.question}"
    )

    chat_history.append(
        f"Assistant: {result['answer']}"
    )

    return result


# --------------------------------------------------
# NEW CHAT
# --------------------------------------------------

@app.post("/new-chat")
def new_chat():

    global chat_history

    chat_history = []

    return {
        "message": "New chat started"
    }


# --------------------------------------------------
# DELETE DOCUMENT
# --------------------------------------------------

@app.delete("/documents/{filename}")
def delete_document(filename: str):

    global chat_history

    if filename not in documents_store:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    # Only use the stored upload directory; never trust a filename as a path.
    file_path = os.path.join("data", "uploads", os.path.basename(filename))

    if os.path.exists(file_path):
        os.remove(file_path)

    del documents_store[filename]
    chat_history = []

    return {
        "message": "Document deleted successfully",
        "documents": list(documents_store.keys())
    }
