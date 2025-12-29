import frappe
from ai_integration.ai_integration.mcp import mcp

@mcp.tool()
def list_documents(doctype: str, filters: dict = None, fields: list = None, limit: int = 20):
    """
    List documents of a given DocType.

    Args:
        doctype: The DocType to list documents from.
        filters: Dictionary of filters (e.g. {"status": "Open"}).
        fields: List of fields to fetch.
        limit: Number of documents to fetch (default 20).
    """
    return frappe.get_list(doctype, filters=filters, fields=fields, limit_page_length=limit)

@mcp.tool()
def get_document(doctype: str, name: str):
    """
    Get a specific document by name.

    Args:
        doctype: The DocType of the document.
        name: The name (ID) of the document.
    """
    doc = frappe.get_doc(doctype, name)
    return doc.as_dict()

@mcp.tool()
def get_doctype_schema(doctype: str):
    """
    Get the schema (field definitions) for a DocType.

    Args:
        doctype: The DocType to get schema for.
    """
    meta = frappe.get_meta(doctype)
    fields = []
    for field in meta.fields:
        fields.append({
            "fieldname": field.fieldname,
            "label": field.label,
            "fieldtype": field.fieldtype,
            "options": field.options,
            "reqd": field.reqd
        })
    return fields
