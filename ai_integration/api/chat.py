import frappe
import json
import numpy as np
from google import genai
from ai_integration.utils.embedding import generate_embedding_vector

def get_settings():
    return frappe.get_single("AI Integration Settings")

def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

@frappe.whitelist()
def send_message(message):
    """
    RAG Implementation:
    1. Embed User Query
    2. Search Vector DB (AI Embedding DocType)
    3. Filter by Permission
    4. Construct Prompt
    5. Call Gemini
    """
    try:
        settings = get_settings()
        if not settings.google_api_key:
            return {"error": "Google API Key not configured."}

        # 1. Embed Query
        query_vector = generate_embedding_vector(message)
        if not query_vector:
            return {"error": "Failed to generate embedding for query."}

        # 2. Search Vector DB
        # Optimization: Use Faiss based Vector Store
        from ai_integration.utils.vector_store import get_vector_store
        vector_store = get_vector_store()

        # Get more candidates than needed to account for permission filtering
        search_results = vector_store.search(query_vector, k=20)

        scored_docs = []
        if search_results:
            # Filter by threshold
            valid_results = [r for r in search_results if r['score'] > 0.4]

            if valid_results:
                names = [r['name'] for r in valid_results]
                # Bulk fetch content for matched embeddings
                docs = frappe.get_all("AI Embedding",
                    filters={"name": ["in", names]},
                    fields=["name", "reference_doctype", "reference_name", "content"]
                )
                doc_map = {d.name: d for d in docs}

                for res in valid_results:
                    if res['name'] in doc_map:
                        scored_docs.append({
                            "score": res['score'],
                            "doc": doc_map[res['name']]
                        })

        # 3. Filter by Permission & Top K
        top_k = 5
        context_chunks = []

        for item in scored_docs:
            if len(context_chunks) >= top_k:
                break

            ref_doctype = item['doc'].reference_doctype
            ref_name = item['doc'].reference_name

            if frappe.has_permission(ref_doctype, doc=ref_name, ptype="read"):
                context_chunks.append(f"Context from {ref_doctype} ({ref_name}):\n{item['doc'].content}")

        # 4. Construct Prompt
        context_text = "\n\n---\n\n".join(context_chunks)

        system_instruction = (
            "You are a helpful assistant integrated into ERPNext. "
            "Use the provided context to answer the user's question. "
            "If the answer is not in the context, say you don't know based on the available data, "
            "but try to be helpful if it's a general question. "
            "Always be polite and professional."
        )

        full_prompt = f"{system_instruction}\n\nContext:\n{context_text}\n\nUser Question: {message}"

        # 5. Call Gemini
        api_key = settings.get_password("google_api_key")
        client = genai.Client(api_key=api_key)

        model_name = settings.google_model or "gemini-3-pro-preview"

        # Handle 'preview' model names or standard names properly
        # Google GenAI library expects specific model names.
        # If user typed 'gemini-1.5-pro', we use that.
        model_name = model_name.strip()
        if model_name.startswith("models/"):
            model_name = model_name[7:]

        response = client.models.generate_content(
            model=model_name,
            contents=full_prompt
        )

        return {
            "response": response.text,
            "context_used": [c[:100] + "..." for c in context_chunks] # Debug info
        }

    except Exception as e:
        frappe.log_error(f"Chat Error: {str(e)}")
        return {"error": str(e)}
