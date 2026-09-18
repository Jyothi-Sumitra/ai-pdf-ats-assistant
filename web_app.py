from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

import os
import shutil

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")

app = FastAPI(
    title="AI PDF Assistant",
    description="Chat with PDF documents using Retrieval-Augmented Generation",
    version="2.0.0"
)

# Keep the original UI exactly as-is. Static assets are served from /static.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# IMPORTANT FOR VERCEL:
# Do not import the LangChain/Chroma/LLM modules at application startup.
# Those packages are large and can have optional/native dependencies. Import
# them only inside the endpoint that actually needs them, so a simple GET /
# can start even if a backend-only dependency has a runtime problem.
llm = None

def get_runtime_llm():
    global llm
    if llm is None:
        from src.chatbot import get_llm
        llm = get_llm()
    return llm

documents_store = {}
chat_history = []


@app.get("/")
def home():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    from src.pdf_loader import load_pdf
    from src.text_splitter import split_documents
    from src.embeddings import get_embeddings
    from src.vector_store import get_vector_store
    from src.retriever import get_retriever

    global documents_store, chat_history

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_filename = os.path.basename(file.filename)
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    documents = load_pdf(file_path)
    chunks = split_documents(documents)

    if not chunks:
        try:
            os.remove(file_path)
        except OSError:
            pass

        raise HTTPException(
            status_code=400,
            detail="This PDF does not contain selectable text. Please upload a text-based PDF or run OCR on it first."
        )

    for chunk in chunks:
        chunk.metadata["filename"] = file.filename

    embedding_model = get_embeddings()
    vector_store = get_vector_store(file_path, chunks, embedding_model)
    document_retriever = get_retriever(vector_store, chunks)

    documents_store[file.filename] = {
        "retriever": document_retriever,
        "chunks": chunks,
        "summary": None
    }

    chat_history = []

    return {
        "message": "PDF uploaded and processed successfully",
        "filename": file.filename,
        "pages": len(documents),
        "chunks": len(chunks),
        "documents": list(documents_store.keys())
    }


@app.post("/ats/analyze")
async def ats_analyze(
    resume: UploadFile = File(...),
    job_description: UploadFile = File(...)
):
    from src.ats.parser import extract_pdf_text
    from src.ats.analyzer import analyze_resume

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    if not resume.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Resume must be a PDF file.")

    if not job_description.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Job description must be a PDF file.")

    resume_path = os.path.join(
        UPLOAD_DIR,
        "ats_resume_" + os.path.basename(resume.filename)
    )
    jd_path = os.path.join(
        UPLOAD_DIR,
        "ats_job_description_" + os.path.basename(job_description.filename)
    )

    try:
        with open(resume_path, "wb") as buffer:
            shutil.copyfileobj(resume.file, buffer)

        with open(jd_path, "wb") as buffer:
            shutil.copyfileobj(job_description.file, buffer)

        resume_text = extract_pdf_text(resume_path)
        job_description_text = extract_pdf_text(jd_path)

        if not resume_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from the resume PDF."
            )

        if not job_description_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from the job description PDF."
            )

        result = analyze_resume(
            resume_text=resume_text,
            job_description=job_description_text,
            llm=get_runtime_llm()
        )

        return result.model_dump()

    except HTTPException:
        raise

    except Exception as e:
        print(f"ATS analysis error: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while analyzing the resume."
        )

    finally:
        for path in [resume_path, jd_path]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass


@app.get("/ats-analysis")
def ats_analysis_page():
    return FileResponse(os.path.join(STATIC_DIR, "ats.html"))


@app.get("/documents")
def get_documents():
    return {"documents": list(documents_store.keys())}


class ChatRequest(BaseModel):
    question: str
    selected_document: str = ""
    use_web: bool = False
    search_web: bool = False


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
    return any(phrase in question for phrase in summary_phrases)


@app.post("/chat")
def chat(request: ChatRequest):
    from src.assistant import handle_question
    from src.summarizer import summarize_document

    global chat_history

    runtime_llm = get_runtime_llm()

    if request.use_web:
        return handle_question(
            question=request.question,
            llm=runtime_llm,
            retriever=None,
            chat_history=chat_history,
            use_web=True
        )

    if request.selected_document not in documents_store:
        return {
            "error": "Please select a valid PDF first or enable Web Search."
        }

    selected_pdf = documents_store[request.selected_document]
    retriever = selected_pdf["retriever"]
    chunks = selected_pdf["chunks"]

    if is_summary_request(request.question):
        if selected_pdf["summary"] is None:
            selected_pdf["summary"] = summarize_document(
                chunks,
                runtime_llm
            )

        result = {
            "answer": selected_pdf["summary"],
            "route": "pdf",
            "sources": [
                {"filename": request.selected_document}
            ]
        }

    else:
        result = handle_question(
            question=request.question,
            llm=runtime_llm,
            retriever=retriever,
            chat_history=chat_history,
            use_web=False
        )

    chat_history.append(f"User: {request.question}")
    chat_history.append(f"Assistant: {result['answer']}")

    return result


@app.post("/new-chat")
def new_chat():
    global chat_history
    chat_history = []
    return {"message": "New chat started"}


@app.delete("/documents/{filename}")
def delete_document(filename: str):
    from src.file_hash import calculate_file_hash
    from src.vector_store import DB_ROOT

    global chat_history

    if filename not in documents_store:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    file_path = os.path.join(
        UPLOAD_DIR,
        os.path.basename(filename)
    )

    vector_db_path = None

    if os.path.exists(file_path):
        vector_db_path = os.path.join(
            DB_ROOT,
            calculate_file_hash(file_path)
        )
        os.remove(file_path)

    if vector_db_path and os.path.exists(vector_db_path):
        shutil.rmtree(vector_db_path, ignore_errors=True)

    del documents_store[filename]
    chat_history = []

    return {
        "message": "Document deleted successfully",
        "documents": list(documents_store.keys())
    }
