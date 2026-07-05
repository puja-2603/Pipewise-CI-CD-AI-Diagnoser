from dotenv import load_dotenv
load_dotenv()

from app import fingerprint, db

past_failures_full = db.get_recent_failures("test/repo")

# Pull full records including the actual stored text, not just embeddings
from app.db import _client
resp = _client.table("failures").select("id, error_summary, embedding").eq("repo_full_name", "test/repo").execute()

for row in resp.data:
    print("ID:", row["id"])
    print("Stored text:", row["error_summary"])
    emb = row["embedding"]
    print("Embedding type:", type(emb))
    print("Embedding length:", len(emb) if hasattr(emb, "__len__") else "N/A")
    print("First 5 values:", emb[:5] if hasattr(emb, "__getitem__") else emb)
    print("---")