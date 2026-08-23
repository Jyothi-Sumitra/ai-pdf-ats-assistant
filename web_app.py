from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

import os
import shutil

# Load environment variables from .env file
load_dotenv()

from src.pdf_loader import load_pdf
from src.text_splitter import split_documents
from src.embeddings import get_embeddings
from src.vector_store import get_vector_store
from src.retriever import get_retriever
from src.chatbot import get_llm
from src.summarizer import summarize_document
from src.assistant import handle_question
from src.file_hash import calculate_file_hash
from src.vector_store import DB_ROOT

# ATS
from src.ats.parser import extract_pdf_text
from src.ats.analyzer import analyze_resume

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
# HEALTH CHECK (for uptime pinger)
# --------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


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

    if not chunks:
        try:
            os.remove(file_path)
        except OSError:
            pass

        raise HTTPException(
            status_code=400,
            detail=(
                "This PDF does not contain selectable text. "
                "Please upload a text-based PDF or run OCR on it first."
            )
        )

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
# ATS ANALYSIS
# --------------------------------------------------

@app.post("/ats/analyze")
async def ats_analyze(
    resume: UploadFile = File(...),
    job_description: UploadFile = File(...)
):
    """
    Analyze a resume against a job description.

    The frontend uploads two PDFs:
    - resume
    - job description

    The ATS analyzer extracts their text and performs
    deterministic scoring.
    """

    # Make sure the upload directory exists
    os.makedirs(
        "data/uploads",
        exist_ok=True
    )

    # --------------------------------------------------
    # Validate file types
    # --------------------------------------------------

    if not resume.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Resume must be a PDF file."
        )

    if not job_description.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Job description must be a PDF file."
        )

    # --------------------------------------------------
    # Create safe filenames
    # --------------------------------------------------

    resume_filename = (
        "ats_resume_"
        + os.path.basename(resume.filename)
    )

    jd_filename = (
        "ats_job_description_"
        + os.path.basename(job_description.filename)
    )

    resume_path = os.path.join(
        "data",
        "uploads",
        resume_filename
    )

    jd_path = os.path.join(
        "data",
        "uploads",
        jd_filename
    )

    try:

        # --------------------------------------------------
        # Save resume
        # --------------------------------------------------

        with open(resume_path, "wb") as buffer:
            shutil.copyfileobj(
                resume.file,
                buffer
            )

        # --------------------------------------------------
        # Save job description
        # --------------------------------------------------

        with open(jd_path, "wb") as buffer:
            shutil.copyfileobj(
                job_description.file,
                buffer
            )

        # --------------------------------------------------
        # Extract text
        # --------------------------------------------------

        resume_text = extract_pdf_text(
            resume_path
        )

        job_description_text = extract_pdf_text(
            jd_path
        )

        if not resume_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from the resume PDF."
            )

        if not job_description_text.strip():
            raise HTTPException(
                status_code=400,
                detail=(
                    "Could not extract text from the "
                    "job description PDF."
                )
            )

        # --------------------------------------------------
        # Run ATS analysis
        # --------------------------------------------------

        result = analyze_resume(
            resume_text=resume_text,
            job_description=job_description_text,
            llm=llm
        )

        # --------------------------------------------------
        # Return JSON
        # --------------------------------------------------

        return result.model_dump()

    except HTTPException:
        raise

    except Exception as e:

        print(
            f"ATS analysis error: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "An error occurred while analyzing "
                "the resume."
            )
        )

    finally:

        # --------------------------------------------------
        # Clean temporary ATS files
        # --------------------------------------------------

        for path in [
            resume_path,
            jd_path
        ]:

            if os.path.exists(path):

                try:
                    os.remove(path)

                except OSError:
                    pass
                
# --------------------------------------------------
# ATS ANALYSIS PAGE
# --------------------------------------------------

@app.get("/ats-analysis")
def ats_analysis_page():
    return FileResponse("static/ats.html")

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

    # If web search is enabled, use it directly regardless of PDF selection
    if request.use_web:

        result = handle_question(
            question=request.question,
            llm=llm,
            retriever=None,
            chat_history=chat_history,
            use_web=True
        )

        return result

    # Without web search, a PDF must be selected
    if request.selected_document not in documents_store:

        return {
            "error": "Please select a valid PDF first or enable Web Search."
        }

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
    vector_db_path = None

    if os.path.exists(file_path):
        vector_db_path = os.path.join(
            DB_ROOT,
            calculate_file_hash(file_path)
        )

    if os.path.exists(file_path):
        os.remove(file_path)

    if vector_db_path and os.path.exists(vector_db_path):
        shutil.rmtree(vector_db_path, ignore_errors=True)

    del documents_store[filename]
    chat_history = []

    return {
        "message": "Document deleted successfully",
        "documents": list(documents_store.keys())
    }
