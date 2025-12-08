import frappe
import google.generativeai as genai
from frappe.utils import cleanhtml
from ai_integration.ai_integration.doctype.ai_api_key.ai_api_key import get_api_key
from ai_integration.ai_integration.doctype.ai_integration_settings.ai_integration_settings import get_allowed_doctypes

@frappe.whitelist()
def generate_embeddings():
	"""
	Generates embeddings for all records in allowed DocTypes.
	"""
	api_key = get_api_key("Gemini API Studio")
	if not api_key:
		frappe.throw("Gemini API Key not found or active in AI API Key DocType.")

	genai.configure(api_key=api_key)
	
	allowed_doctypes = get_allowed_doctypes()
	if not allowed_doctypes:
		frappe.throw("No allowed DocTypes configured in AI Integration Settings.")

	generated_count = 0
	
	try:
		model = "models/embedding-001" 
		
		for dt in allowed_doctypes:
			# Fetch records - basic logic: get all name + title/subject/description fields
			# Optimizing this requires clearer mapping, but for now we try common fields
			# or just 'name' if nothing else matches.
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

				# Check if embedding already exists to avoid re-work (optional optimization)
				existing = frappe.db.exists("AI Embedding", {
					"reference_doctype": dt,
					"reference_name": record.name
				})
				
				if not existing:
					# Call API
					result = genai.embed_content(
						model=model,
						content=original_text,
						task_type="retrieval_document",
						title=str(record.get(title_field))
					)
					
					embedding_vector = result['embedding']
					
					# Save
					doc = frappe.get_doc({
						"doctype": "AI Embedding",
						"reference_doctype": dt,
						"reference_name": record.name,
						"original_text": original_text,
						"embedding_vector": str(embedding_vector) # Storing as string representation of list
					})
					doc.insert(ignore_permissions=True)
					generated_count += 1

		frappe.msgprint(f"Successfully generated {generated_count} embeddings.")

	except Exception as e:
		frappe.log_error(f"Embedding Generation Error: {str(e)}")
		frappe.throw(f"Failed to generate embeddings: {str(e)}")
