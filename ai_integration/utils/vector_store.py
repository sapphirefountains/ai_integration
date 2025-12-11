import frappe
import json
import numpy as np
try:
    import faiss
except ImportError:
    faiss = None
from frappe.utils import get_datetime

class FaissVectorStore:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FaissVectorStore, cls).__new__(cls)
            cls._instance.index = None
            cls._instance.doc_map = [] # Maps index ID to AI Embedding name
            cls._instance.last_synced = None
        return cls._instance

    def sync(self):
        """
        Syncs the in-memory index with the database.
        Checks if the database has been modified since last sync.
        """
        if not faiss:
            frappe.throw("faiss-cpu is not installed. Please install it to use Vector Search.")

        # Get the latest modification time from DB
        # We use sql because get_value might cache? No, get_value is fine usually, but let's be safe
        # Actually frappe.db.get_value is cached in request but we want fresh.
        # But this code runs in a request context usually.
        last_modified = frappe.db.get_value("AI Embedding", {}, "max(modified)")

        if not last_modified:
             # No embeddings
             self.index = None
             self.doc_map = []
             return

        # If we have synced before and DB hasn't changed, return
        if self.last_synced and get_datetime(last_modified) <= get_datetime(self.last_synced):
            return

        # Reload everything
        self._reload_all()
        self.last_synced = last_modified

    def _reload_all(self):
        # Fetch all embeddings
        # We only need name and vector.
        # Explicit limit=None for fetching all.
        embeddings = frappe.get_all("AI Embedding", fields=["name", "vector"], limit=None)

        if not embeddings:
            self.index = None
            self.doc_map = []
            return

        vectors = []
        names = []

        for emb in embeddings:
            if not emb.vector:
                continue
            try:
                vec = json.loads(emb.vector)
                vectors.append(vec)
                names.append(emb.name)
            except Exception:
                continue

        if not vectors:
            self.index = None
            self.doc_map = []
            return

        # Convert to float32 numpy array
        d = len(vectors[0])
        matrix = np.array(vectors).astype('float32')

        # Normalize for cosine similarity (Inner Product)
        faiss.normalize_L2(matrix)

        # Create Index
        # IndexFlatIP is exact search using Inner Product (Cosine Similarity if normalized)
        self.index = faiss.IndexFlatIP(d)
        self.index.add(matrix)

        self.doc_map = names

    def search(self, query_vector, k=5):
        self.sync() # Ensure we are up to date

        if not self.index or self.index.ntotal == 0:
            return []

        # Prepare query vector
        q_vec = np.array([query_vector]).astype('float32')
        faiss.normalize_L2(q_vec)

        # Search
        D, I = self.index.search(q_vec, k)

        results = []
        # I[0] contains the indices for the first (and only) query vector
        for rank, idx in enumerate(I[0]):
            if idx == -1: continue

            score = float(D[0][rank])
            if idx < len(self.doc_map):
                doc_name = self.doc_map[idx]
                results.append({
                    "name": doc_name,
                    "score": score
                })

        return results

def get_vector_store():
    return FaissVectorStore()
