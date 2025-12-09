import frappe
from ai_integration.utils.embedding import create_embedding_for_doc, delete_embeddings_for_doc

def on_doc_update(doc, method):
    """
    Hook to generate embeddings when a document is saved.
    Checks if the DocType is enabled for embedding integration.
    """
    if doc.doctype == "AI Integration Settings":
        return

    # Check if this doctype is enabled
    # We use frappe.cache to avoid DB hitting on every save if possible,
    # but for now simpler is direct check or getting settings.

    # Getting settings every time might be slight overhead but safe for now.
    settings = frappe.get_single("AI Integration Settings")

    # Safely get the table, handling AttributeError or None if settings not fully loaded
    enabled_doctypes = getattr(settings, "enabled_doctypes", None)

    if not enabled_doctypes:
        return

    enabled = [d.doctype_name for d in enabled_doctypes]

    if doc.doctype in enabled:
        try:
            frappe.enqueue(create_embedding_for_doc, doc=doc, queue='default')
        except Exception:
            # Don't block the save if enqueue fails, but log it
            frappe.log_error(f"Failed to enqueue embedding for {doc.doctype} {doc.name}")

def on_doc_trash(doc, method):
    """
    Hook to delete embeddings when a document is deleted.
    """
    if doc.doctype == "AI Integration Settings":
        return

    settings = frappe.get_single("AI Integration Settings")

    # Safely get the table, handling AttributeError or None
    enabled_doctypes = getattr(settings, "enabled_doctypes", None)

    if not enabled_doctypes:
        return

    enabled = [d.doctype_name for d in enabled_doctypes]

    if doc.doctype in enabled:
        try:
            # Delete immediately, no need to queue as it's a quick DB delete
            delete_embeddings_for_doc(doc)
        except Exception:
            frappe.log_error(f"Failed to delete embedding for {doc.doctype} {doc.name}")
