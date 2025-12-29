import frappe
from ai_integration.utils.rag import answer_user_question

@frappe.whitelist()
def send_message(message):
    return answer_user_question(message)
