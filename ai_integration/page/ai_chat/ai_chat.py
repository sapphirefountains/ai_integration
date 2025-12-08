import frappe
from google import genai
import json
import math
from frappe.utils import cstr
from ai_integration.ai_integration.doctype.ai_api_key.ai_api_key import get_api_key

def cosine_similarity(v1, v2):
	"""
	Compute cosine similarity between two vectors.
	"""
	if not v1 or not v2: return 0.0
	dot_product = sum(a*b for a, b in zip(v1, v2))
	magnitude1 = math.sqrt(sum(a*a for a in v1))
	magnitude2 = math.sqrt(sum(b*b for b in v2))
	if magnitude1 * magnitude2 == 0:
		return 0.0
	return dot_product / (magnitude1 * magnitude2)

@frappe.whitelist()
def message(message):
	"""
	Handle chat message with RAG.
	"""
	if not message: return

	# 1. Auth & Setup
	api_key = get_api_key("Gemini API Studio")
	if not api_key:
		frappe.throw("Gemini API Key not configured.")
	
	client = genai.Client(api_key=api_key)
	embed_model = "text-embedding-004"
	gen_model = "gemini-2.0-flash-exp" # Or gemini-1.5-flash

	# 2. Embed User Query
	try:
		query_resp = client.models.embed_content(
			model=embed_model,
			contents=message,
			config={"task_type": "RETRIEVAL_QUERY"}
		)
		user_element = query_resp.embeddings[0].values
		user_vector = list(user_element)
	except Exception as e:
		frappe.log_error(f"Embedding failed: {e}")
		return "Sorry, I had trouble processing your message (Embedding Error)."

	# 3. Vector Search
	# Fetch all embeddings (Optimize this with a vector DB in production)
	# For now, we perform linear scan + sort in Python (fine for small-medium scale)
	all_embeddings = frappe.get_all("AI Embedding", fields=["name", "reference_doctype", "reference_name", "original_text", "embedding_vector"])
	
	scored_chunks = []
	for item in all_embeddings:
		if not item.embedding_vector: continue
		
		# Parse vector
		try:
			doc_vector = json.loads(item.embedding_vector)
		except:
			continue

		score = cosine_similarity(user_vector, doc_vector)
		if score > 0.4: # Threshold
			scored_chunks.append({
				"score": score,
				"text": item.original_text,
				"doctype": item.reference_doctype,
				"docname": item.reference_name
			})

	# Sort by score descending
	scored_chunks.sort(key=lambda x: x['score'], reverse=True)
	top_chunks = scored_chunks[:5] # Top 5 relevant chunks

	# 4. Security Check (Crucial)
	allowed_context = []
	for chunk in top_chunks:
		if frappe.has_permission(chunk['doctype'], "read", chunk['docname']):
			allowed_context.append(f"Content from {chunk['doctype']} ({chunk['docname']}):\n{chunk['text']}")
		else:
			# Log silent security filter
			# frappe.logger().debug(f"Filtered {chunk['docname']} for user {frappe.session.user}")
			pass

	# 5. Generate Answer
	if not allowed_context:
		context_str = "No relevant documents found or you do not have permission to view them."
	else:
		context_str = "\n\n".join(allowed_context)

	system_instruction = (
		"You are a helpful assistant for a company using ERPNext/Frappe."
		"Answer the user's question using ONLY the provided context."
		"If the answer is not in the context, say so."
		"Keep answers concise and professional."
	)
	
	prompt = f"Context:\n{context_str}\n\nUser Question: {message}"

	try:
		response = client.models.generate_content(
			model=gen_model,
			contents=prompt,
			config=genai.types.GenerateContentConfig(
				system_instruction=system_instruction
			)
		)
		return response.text
	except Exception as e:
		frappe.log_error(f"Generation failed: {e}")
		return "Sorry, I encountered an error generating the response."
