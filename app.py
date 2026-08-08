from src.pdf_loader import load_pdf
from src.text_splitter import split_documents
from src.embeddings import get_embeddings
from src.vector_store import get_vector_store
from src.retriever import get_retriever
from src.chatbot import get_llm
from src.rag_chain import ask_question
from src.file_hash import calculate_file_hash
from src.vector_store import save_hash, load_hash
from src.web_search import get_web_search_tool
from src.web_search import search_web


def main():

    # Temporary Tavily test
    search_tool = get_web_search_tool()

    results = search_tool.invoke({
        "query": "Latest developments in generative AI"
    })

    # print(results)

    # return

    # Existing PDF code
    pdf_path = "data/AI_Research.pdf"

    documents = load_pdf(pdf_path)
    chunks = split_documents(documents)

    embedding_model = get_embeddings()

    vector_store = get_vector_store(
        pdf_path,
        chunks,
        embedding_model
    )

    retriever = get_retriever(
        vector_store,
        chunks
    )

    chat_history = []

    llm = get_llm()

    while True:
        question = input("\n🧑 You: ")

        if question.lower() in ["exit", "bye"]:
            print("\n🤖 Assistant: Bye!")
            break

        answer = ask_question(
            retriever,
            llm,
            question,
            chat_history
        )

        print("\n🤖 Assistant:", answer)

if __name__ == "__main__":
    main()