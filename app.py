from src.pdf_loader import load_pdf
from src.text_splitter import split_documents
from src.embeddings import get_embeddings
from src.vector_store import get_vector_store
from src.retriever import get_retriever
from src.chatbot import get_llm
from src.rag_chain import ask_question
from src.file_hash import calculate_file_hash
from src.vector_store import save_hash, load_hash

def main():

    pdf_path = "data/AI_Research.pdf"

    documents = load_pdf(pdf_path)
    chunks = split_documents(documents)

    embedding_model = get_embeddings()

    vector_store = get_vector_store(pdf_path, chunks, embedding_model)

    retriever = get_retriever(vector_store)

    llm = get_llm()
    
    chat_history = []
    while True:
        question = input("\n🧑 You: ")
        if question.lower() in ["exit", "bye"]:
            print("\n🤖 Assistant: Bye!")
            break

        answer = ask_question(retriever, llm, question, chat_history)
        chat_history.append(f"User: {question}")
        chat_history.append(f"Assistant: {answer}")
        
        print("\n🤖 Assistant: ", answer)

if __name__ == "__main__":
    main()