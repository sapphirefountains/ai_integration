from ai_integration.ai_integration.mcp import mcp
from ai_integration.utils.rag import answer_user_question

@mcp.tool()
def search_knowledge_base(query: str):
    """
    Search the knowledge base using RAG (Retrieval Augmented Generation) to answer a question.
    This searches the vector database of indexed documents and uses an LLM to generate an answer.

    Args:
        query: The question or search query.
    """
    return answer_user_question(query)
