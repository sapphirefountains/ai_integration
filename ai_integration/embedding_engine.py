import frappe
from google import genai
from frappe.utils import cleanhtml
from ai_integration.ai_integration.doctype.ai_api_key.ai_api_key import get_api_key
from ai_integration.ai_integration.doctype.ai_integration_settings.ai_integration_settings import get_allowed_doctypes

@frappe.whitelist()
def generate_embeddings():
	"""
	Generates embeddings for all records in allowed DocTypes using the google-genai SDK.
	"""
	api_key = get_api_key("Gemini API Studio")
	if not api_key:
		frappe.throw("Gemini API Key not found or active in AI API Key DocType.")

	client = genai.Client(api_key=api_key)
	
	allowed_doctypes = get_allowed_doctypes()
	if not allowed_doctypes:
		frappe.throw("No allowed DocTypes configured in AI Integration Settings.")

	generated_count = 0
	
	try:
		# google-genai typically uses 'models/text-embedding-004' or similar.
		# Using a generic text embedding model.
		model_id = "text-embedding-004" 
		
		for dt in allowed_doctypes:
			meta = frappe.get_meta(dt)
			title_field = meta.title_field or "name"
			fields_to_fetch = ["name", title_field]
			
			if meta.has_field("description"):
				fields_to_fetch.append("description")
			if meta.has_field("subject"):
				fields_to_fetch.append("subject")
				
			records = frappe.get_all(dt, fields=fields_to_fetch, limit=50) # Limit for safety
			
			for record in records:
				# Construct text
				text_parts = [str(record.get(title_field, ""))]
				if "description" in record:
					text_parts.append(cleanhtml(str(record.get("description", ""))))
				if "subject" in record:
					text_parts.append(str(record.get("subject", "")))
				
				original_text = " ".join(text_parts).strip()
				if not original_text:
					continue

				existing = frappe.db.exists("AI Embedding", {
					"reference_doctype": dt,
					"reference_name": record.name
				})
				
				if not existing:
					# Call API using new SDK
					response = client.models.embed_content(
						model=model_id,
						contents=original_text,
						config={
							"task_type": "RETRIEVAL_DOCUMENT",
							"title": str(record.get(title_field))
						}
					)
					
					embedding_vector = response.embeddings[0].values
					
					doc = frappe.get_doc({
						"doctype": "AI Embedding",
						"reference_doctype": dt,
						"reference_name": record.name,
						"original_text": original_text,
						"embedding_vector": str(list(embedding_vector))
					})
					doc.insert(ignore_permissions=True)
					generated_count += 1

		frappe.msgprint(f"Successfully generated {generated_count} embeddings.")

	except Exception as e:
		frappe.log_error(f"Embedding Generation Error: {str(e)}")
		frappe.throw(f"Failed to generate embeddings: {str(e)}")
