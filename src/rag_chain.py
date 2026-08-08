from langchain_core.prompts import ChatPromptTemplate
from src.chatbot import get_llm

prompt = ChatPromptTemplate.from_template(
    """
You are a helpful AI assistant.

Answer the user's question ONLY using the context below.

If the answer is not found in the context, say:
"I couldn't find that information in the document."

Context:
{context}

Question:
{question}
"""
)

history_prompt = ChatPromptTemplate.from_template(
    """
Your task is to rewrite the latest user question ONLY if it depends on
the conversation history.

IMPORTANT:
- First determine whether the latest question is already understandable on its own.
- If it is already standalone, return it EXACTLY as written.
- Only use conversation history to resolve missing or ambiguous references.
- Preserve the user's exact intent.
- Never carry the intent of a previous question into a new standalone question.
- Do not answer the question.
- Do not ask a new question.
- Output only the final question.

Conversation history:
{chat_history}

Latest question:
{question}
"""
)

#chain = prompt | llm

def ask_question(retriever, llm, question, chat_history):
    history_messages = history_prompt.format_messages(chat_history=chat_history, question=question)
    rewritten_response = llm.invoke(history_messages)

    standalone_question = rewritten_response.content

    docs = retriever.invoke(standalone_question)
    context = "\n\n".join(
        doc.page_content for doc in docs
    )

    messages = prompt.format_messages(context=context, question=question)
    response = llm.invoke(messages)
    answer = response.content

    if "i couldn't find that information in the document." in answer.lower():
        return answer

    pages = sorted(
        set(
            doc.metadata["page"] + 1
            for doc in docs
            if "page" in doc.metadata
        )
    )

    if pages:
        sources = ", ".join(str(page) for page in pages)

        return (
            f"{answer}"
            f"\n\n📄 Sources: Page(s) {sources}"
        )

    return answer
