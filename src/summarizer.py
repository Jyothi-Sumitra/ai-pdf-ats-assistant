from langchain_core.prompts import ChatPromptTemplate

chunk_summary_prompt = ChatPromptTemplate.from_template(
    """
You are summarizing part of a PDF document.

Summarize the following content clearly and concisely.
Focus on the main ideas, important concepts, and key information.

Content:
{content}
"""
)


final_summary_prompt = ChatPromptTemplate.from_template(
    """
You are given several summaries from different parts of a PDF document.

Combine them into one clear summary of the entire document.

The summary should:
- Explain what the document is mainly about
- Include the most important topics and ideas
- Avoid unnecessary repetition
- Be easy to understand

Partial summaries:
{summaries}
"""
)

def summarize_document(chunks, llm):

    partial_summaries = []

    group_size = 5

    for i in range(0, len(chunks), group_size):

        group = chunks[i:i + group_size]

        content = "\n\n".join(
            chunk.page_content for chunk in group
        )

        messages = chunk_summary_prompt.format_messages(
            content=content
        )

        response = llm.invoke(messages)

        partial_summaries.append(response.content)

    combined_summaries = "\n\n".join(partial_summaries)

    messages = final_summary_prompt.format_messages(
        summaries=combined_summaries
    )

    response = llm.invoke(messages)

    return response.content