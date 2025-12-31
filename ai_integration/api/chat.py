import frappe
from ai_integration.utils.rag import answer_user_question

@frappe.whitelist()
def send_message(message, session_id=None):
    if not message:
        return {"error": "Message is required."}

    user = frappe.session.user

    # Create or Get Session
    if not session_id:
        # Create new session
        # Use first 30 chars of message as title
        title = message[:30] + "..." if len(message) > 30 else message
        session_doc = frappe.get_doc({
            "doctype": "AI Chat Session",
            "title": title,
            "user": user
        })
        session_doc.insert(ignore_permissions=True)
        session_id = session_doc.name
    else:
        # Validate Session and Permission
        if not frappe.db.exists("AI Chat Session", session_id):
             return {"error": "Invalid Session ID."}

        # Check ownership
        if not frappe.has_permission("AI Chat Session", doc=session_id, ptype="read"):
             return {"error": "Permission Denied."}

    # Save User Message
    user_msg_doc = frappe.get_doc({
        "doctype": "AI Chat Message",
        "session": session_id,
        "role": "user",
        "content": message
    })
    user_msg_doc.insert(ignore_permissions=True)

    # Fetch Recent History (Last 20 messages)
    # We fetch descending to get the LATEST messages, then reverse for prompt order
    history_docs = frappe.get_all("AI Chat Message",
        filters={"session": session_id},
        fields=["role", "content"],
        order_by="creation desc",
        limit=20
    )
    history_docs.reverse()

    # Call RAG Logic
    rag_response = answer_user_question(message, chat_history=history_docs)

    ai_content = ""
    if "response" in rag_response:
        ai_content = rag_response["response"]
    elif "error" in rag_response:
        ai_content = f"Error: {rag_response['error']}"
    else:
        ai_content = "Sorry, I encountered an unknown error."

    # Save AI Response
    ai_msg_doc = frappe.get_doc({
        "doctype": "AI Chat Message",
        "session": session_id,
        "role": "ai",
        "content": ai_content
    })
    ai_msg_doc.insert(ignore_permissions=True)

    # Return result with session_id so frontend can update URL
    return {
        "response": ai_content,
        "session_id": session_id,
        "context_used": rag_response.get("context_used", [])
    }

@frappe.whitelist()
def get_user_sessions():
    user = frappe.session.user
    sessions = frappe.get_all("AI Chat Session",
        filters={"user": user},
        fields=["name", "title", "creation"],
        order_by="modified desc"
    )
    return sessions

@frappe.whitelist()
def get_session_history(session_id):
    if not frappe.db.exists("AI Chat Session", session_id):
        return {"error": "Session not found"}

    if not frappe.has_permission("AI Chat Session", doc=session_id, ptype="read"):
        return {"error": "Permission denied"}

    messages = frappe.get_all("AI Chat Message",
        filters={"session": session_id},
        fields=["role", "content", "creation"],
        order_by="creation asc",
        limit=1000 # Increase limit to ensure full history is loaded
    )
    return messages

@frappe.whitelist()
def delete_session(session_id):
    if not frappe.db.exists("AI Chat Session", session_id):
        return {"error": "Session not found"}

    doc = frappe.get_doc("AI Chat Session", session_id)
    if not doc.has_permission("delete"):
         return {"error": "Permission denied"}

    # Delete messages first (though cascade might handle it if configured, but let's be safe)
    frappe.db.delete("AI Chat Message", {"session": session_id})
    doc.delete()
    return {"status": "success"}
