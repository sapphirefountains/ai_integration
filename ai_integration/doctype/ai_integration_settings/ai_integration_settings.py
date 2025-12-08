import frappe
from frappe.model.document import Document

class AIIntegrationSettings(Document):
	pass

def get_allowed_doctypes():
	"""
	Returns a list of allowed DocType names from settings.
	"""
	doc = frappe.get_single("AI Integration Settings")
	return [row.doctype_name for row in doc.allowed_doctypes]
