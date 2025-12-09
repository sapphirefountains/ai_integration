import frappe
import json
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
    """Simple chunking by characters for now. Can be improved to token based."""
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
        docs = frappe.get_all(doctype, fields=["name"])

        for d in docs:
            doc = frappe.get_doc(doctype, d.name)
            try:
                create_embedding_for_doc(doc)
            except Exception as e:
                frappe.log_error(f"Failed to embed {doctype} {d.name}: {e}", "Embedding Generation Task")
