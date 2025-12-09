
import frappe
from frappe.tests.utils import FrappeTestCase
from ai_integration.utils.embedding import chunk_text, get_doc_content_text

class TestAIIntegration(FrappeTestCase):
    def test_chunking(self):
        text = "Hello world" * 100
        chunks = chunk_text(text, chunk_size=50, overlap=10)
        self.assertTrue(len(chunks) > 1)
        # Check overlap
        self.assertTrue(chunks[0][-10:] == chunks[1][:10])

    def test_get_content(self):
        # Create a dummy Note if Note doctype exists or just use User
        # Let's use User as it always exists
        user = frappe.get_doc("User", "Administrator")
        content = get_doc_content_text(user)
        self.assertTrue("Administrator" in content)
