# Copyright (c) 2024, AI Integration and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from ai_integration.utils.embedding import generate_all_embeddings_task

class AIIntegrationSettings(Document):
	def on_update(self):
		frappe.cache().delete_value("ai_integration:enabled_doctypes")

@frappe.whitelist()
def generate_all_embeddings():
	frappe.enqueue(generate_all_embeddings_task, queue='long', timeout=3600)
