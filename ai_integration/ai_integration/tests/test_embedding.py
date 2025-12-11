
import frappe
from frappe.tests.utils import FrappeTestCase
from ai_integration.utils.embedding import chunk_text, get_doc_content_text

class TestAIIntegration(FrappeTestCase):
    def test_chunking(self):
        text = "Hello world " * 100
        # chunk_size and overlap are now in tokens
        # "Hello world " is 2 tokens (Hello, world) + 1 token (space) = 3 tokens usually.
        # Actually with cl100k_base: 'Hello' (1), ' world' (1), ' ' (1). It varies.
        # Let's trust tiktoken works.
        chunks = chunk_text(text, chunk_size=50, overlap=10)
        self.assertTrue(len(chunks) > 1)
        # Check if chunks have content
        for chunk in chunks:
            self.assertTrue(len(chunk) > 0)

        # We can't easily check exact string overlap because token decoding might not yield exact boundary matches as chars
        # But we can check that we didn't lose text roughly, or just check that it runs.
        # For token-based chunking, overlap is in tokens.

        # Let's verify overlap existence by checking if end of first chunk is in start of second chunk
        # Note: Depending on token boundaries, strict string matching might fail if the cut is inside a token (which shouldn't happen with token slicing)
        # Since we slice tokens, the decoded string should be coherent.

        # Verify that there is some overlap in terms of content
        # The last few words of chunk 0 should appear in chunk 1
        chunk0_end = chunks[0][-20:]
        self.assertIn(chunk0_end, chunks[1])

    def test_get_content(self):
        # Create a dummy Note if Note doctype exists or just use User
        # Let's use User as it always exists
        user = frappe.get_doc("User", "Administrator")
        content = get_doc_content_text(user)
        self.assertTrue("Administrator" in content)
