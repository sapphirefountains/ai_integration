import frappe
import json
import tiktoken
from google import genai
from frappe.utils import get_site_name

def get_api_key():
    settings = frappe.get_single("AI Integration Settings")
    if not settings.google_api_key:
        frappe.throw("Please configure Google API Key in AI Integration Settings")
    return settings.get_password("google_api_key")

def get_embedding_model():
    return "gemini-embedding-001"

def generate_embedding_vector(text):
    api_key = get_api_key()
    client = genai.Client(api_key=api_key)

    # Gemini embedding model
    model = get_embedding_model()

    try:
        result = client.models.embed_content(
            model=model,
            contents=text,
        )
        return result.embeddings[0].values
    except Exception as e:
        frappe.log_error(f"Error generating embedding: {str(e)}", "AI Embedding Error")
        return None

def chunk_text(text, chunk_size=1000, overlap=100):
    """Chunking by tokens using tiktoken (cl100k_base)."""
    if not text:
        return []

    try:
        enc = tiktoken.get_encoding("cl100k_base")
    except Exception:
        # Fallback if tiktoken fails for some reason
        frappe.log_error("tiktoken encoding load failed, falling back to char chunking", "AI Embedding")
        return _chunk_text_char(text, chunk_size * 4, overlap * 4)

    tokens = enc.encode(text)
    if not tokens:
        return []

    chunks = []
    start = 0
    tokens_len = len(tokens)

    while start < tokens_len:
        end = min(start + chunk_size, tokens_len)
        chunk_tokens = tokens[start:end]
        chunks.append(enc.decode(chunk_tokens))

        if end == tokens_len:
            break

        start += (chunk_size - overlap)

    return chunks

def _chunk_text_char(text, chunk_size, overlap):
    """Simple chunking by characters."""
    if not text:
        return []

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)

    return chunks

def get_doc_content_text(doc):
    """Extracts text content from a document."""
    content = []

    # Standard fields to ignore
    ignore = ['name', 'owner', 'creation', 'modified', 'modified_by', 'docstatus', 'idx', 'doctype']

    for field in doc.meta.fields:
        if field.fieldtype in ['Text', 'Text Editor', 'Small Text', 'Long Text', 'Code', 'Data', 'Select']:
            value = doc.get(field.fieldname)
            if value:
                content.append(f"{field.label}: {value}")

    # Also handle child tables if needed?
    # For now, let's stick to main parent fields to keep it simple, or simple recursion.

    return "\n".join(content)

def create_embedding_for_doc(doc):
    """Generates and saves embeddings for a single document."""

    # Delete existing embeddings for this doc
    delete_embeddings_for_doc(doc)

    text = get_doc_content_text(doc)
    if not text:
        return

    chunks = chunk_text(text)

    for idx, chunk in enumerate(chunks):
        vector = generate_embedding_vector(chunk)
        if vector:
            embedding_doc = frappe.get_doc({
                "doctype": "AI Embedding",
                "reference_doctype": doc.doctype,
                "reference_name": doc.name,
                "chunk_index": idx,
                "content": chunk,
                "vector": json.dumps(vector)
            })
            embedding_doc.insert(ignore_permissions=True)

    frappe.db.commit()

def delete_embeddings_for_doc(doc):
    frappe.db.delete("AI Embedding", {
        "reference_doctype": doc.doctype,
        "reference_name": doc.name
    })

def clear_all_embeddings():
    """Clears all entries in the AI Embedding DocType."""
    frappe.db.delete("AI Embedding")
    frappe.db.commit()

def rebuild_all_embeddings():
    """Clears all existing embeddings and regenerates them for enabled doctypes."""
    clear_all_embeddings()
    generate_all_embeddings_task()

def generate_all_embeddings_task():
    """Iterates through all enabled doctypes and generates embeddings."""
    settings = frappe.get_single("AI Integration Settings")

    if not settings.enabled_doctypes:
        return

    for row in settings.enabled_doctypes:
        doctype = row.doctype_name
        # Get all docs of this type
        docs = frappe.get_all(doctype, pluck="name", limit=None)

        # Get existing embeddings
        existing_embeddings = set(frappe.get_all("AI Embedding",
            filters={"reference_doctype": doctype},
            pluck="reference_name",
            limit=None
        ))

        for name in docs:
            if name in existing_embeddings:
                continue

            doc = frappe.get_doc(doctype, name)
            try:
                create_embedding_for_doc(doc)
            except Exception as e:
                frappe.log_error(f"Failed to embed {doctype} {name}: {e}", "Embedding Generation Task")
