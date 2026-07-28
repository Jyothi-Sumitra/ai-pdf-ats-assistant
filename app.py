from src.pdf_loader import load_pdf
from src.text_splitter import split_documents

documents = load_pdf("data/AI_Research.pdf")
chunks = split_documents(documents)

print(f"Pages: {len(documents)}")
print(f"Chunks: {len(chunks)}")