from langchain_tavily import TavilySearch
from langchain_core.prompts import ChatPromptTemplate


def get_web_search_tool():
    search_tool = TavilySearch(max_results=5, topic="general")
    return search_tool


web_prompt = ChatPromptTemplate.from_template(
    """
You are a helpful AI assistant with access to web search results.

Answer the user's question using the search results provided below.

Rules:
- Base your answer on the provided search results.
- Do not invent information that is not supported by the results.
- Give a clear and concise answer.
- Do not include fake URLs or sources.

Search results:
{context}

Question:
{question}
"""
)


def search_web(question, llm):

    search_tool = get_web_search_tool()

    results = search_tool.invoke({
        "query": question
    })

    search_results = results.get("results", [])

    if not search_results:
        return {
            "answer": "I couldn't find relevant information on the web.",
            "sources": []
        }

    context_parts = []
    sources = []

    for result in search_results:

        title = result.get("title", "")
        url = result.get("url", "")
        content = result.get("content", "")

        context_parts.append(
            f"Title: {title}\n"
            f"Content: {content}\n"
            f"URL: {url}"
        )

        sources.append({
            "title": title,
            "url": url
        })

    context = "\n\n".join(context_parts)

    messages = web_prompt.format_messages(
        context=context,
        question=question
    )

    response = llm.invoke(messages)

    return {
        "answer": response.content,
        "sources": sources
    }