from langchain_chroma import Chroma
import os
import shutil
from langchain_chroma import Chroma

from src.pdf_loader import load_pdf
from src.text_splitter import split_documents
from src.file_hash import calculate_file_hash

DB_PATH = "chroma_db"
HASH_FILE = os.path.join(DB_PATH, "hash.txt")

def save_hash(file_hash):
    with open("chroma_db/hash.txt", "w") as file:
        file.write(file_hash)

def load_hash():
    if os.path.exists("chroma_db/hash.txt"):
        with open("chroma_db/hash.txt", "r") as file:
            return file.read().strip()

    return None

def get_vector_store(pdf_path, chunks, embedding_model):

    current_hash = calculate_file_hash(pdf_path)
    saved_hash = load_hash()

    if os.path.exists(DB_PATH):
        print("📂 Loading existing vector database...")

        return Chroma(persist_directory=DB_PATH, embedding_function=embedding_model)

    print("Creating vector database for the first time...")

    return Chroma.from_documents(documents=chunks, embedding=embedding_model, persist_directory=DB_PATH)