from src.web_search import search_web
from src.rag_chain import ask_question


def handle_question(question, llm, retriever, chat_history, use_web=False):
    # WEB SEARCH 
    if use_web:
        result = search_web(question, llm)

        return {
            "answer": result["answer"],
            "route": "web",
            "sources": result["sources"]
        }

    # PDF RAG 
    if retriever is None:
        return {
            "answer": "Please upload and select a PDF first.",
            "route": "pdf",
            "sources": []
        }

    answer = ask_question(retriever, llm, question, chat_history)

    return {
        "answer": answer,
        "route": "pdf",
        "sources": []
    }