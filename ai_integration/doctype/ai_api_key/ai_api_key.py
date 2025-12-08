import frappe
from frappe.model.document import Document

class AIAPIKey(Document):
	def before_save(self):
		if self.is_active:
			# Ensure only one active key per provider if needed, or leave logic open.
			# For now, allowing multiple active keys is fine, but we might want a utility to get the 'default' one.
			pass

	def get_password(self, fieldname="api_key", raise_exception=True):
		"""
		Wrapper to get password with decryption.
		"""
		return super().get_password(fieldname, raise_exception=raise_exception)

def get_api_key(provider):
	"""
	Utility to fetch the active API Key for a given provider.
	"""
	key_doc = frappe.db.get_value("AI API Key", {"api_provider": provider, "is_active": 1}, "name")
	if key_doc:
		doc = frappe.get_doc("AI API Key", key_doc)
		return doc.get_password("api_key")
	return None
