from fastapi import FastAPI, UploadFile, File
import os
import shutil
from src.pdf_loader import load_pdf
from src.text_splitter import split_documents
from src.embeddings import get_embeddings
from src.vector_store import get_vector_store
from src.retriever import get_retriever
from src.chatbot import get_llm
from pydantic import BaseModel
from src.rag_chain import ask_question
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.summarizer import summarize_document

app = FastAPI(
    title="AI PDF Assistant",
    description="Chat with PDF documents using Retrieval-Augmented Generation",
    version="1.0.0"
)

app.mount("/static", StaticFiles(directory="static"), name="static")

retriever = None
llm = get_llm()

chat_history = []
document_chunks = []
document_summary = None

@app.get("/")
def home():
    return FileResponse("static/index.html")

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):

    os.makedirs("data/uploads", exist_ok=True)

    file_path = f"data/uploads/{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    global retriever, chat_history, document_chunks, document_summary

    documents = load_pdf(file_path)
    chunks = split_documents(documents)
    document_chunks = chunks
    document_summary = None

    embedding_model = get_embeddings()

    vector_store = get_vector_store(
        file_path,
        chunks,
        embedding_model
    )

    retriever = get_retriever(vector_store, chunks)
    chat_history = []

    

    return {
    "message": "PDF uploaded and processed successfully",
    "filename": file.filename,
    "pages": len(documents),
    "chunks": len(chunks)
}

class ChatRequest(BaseModel):
        question: str

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

@app.post("/chat")
def chat(request: ChatRequest):
    global chat_history, document_summary

    # Make sure a PDF has been uploaded first
    if retriever is None:
        return {
            "error": "Please upload a PDF first."
        }

    # Handle document summary requests
    if is_summary_request(request.question):

        if document_summary is None:
            document_summary = summarize_document(
                document_chunks,
                llm
            )

        return {
            "answer": document_summary
        }

    # Normal conversational RAG
    answer = ask_question(
        retriever,
        llm,
        request.question,
        chat_history
    )

    chat_history.append(f"User: {request.question}")
    chat_history.append(f"Assistant: {answer}")

    return {
        "answer": answer
    }

@app.post("/new-chat")
def new_chat():
    global chat_history

    chat_history = []

    return {
        "message": "New chat started"
    }