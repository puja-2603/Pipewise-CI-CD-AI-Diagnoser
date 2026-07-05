from dotenv import load_dotenv
load_dotenv()

from app import ai_diagnosis, fingerprint, db

sample_log = """
=== Job: build ===
Collecting nonexistentpackage123==1.0.0
ERROR: Could not find a version that satisfies the requirement nonexistentpackage123==1.0.0
ERROR: No matching distribution found for nonexistentpackage123==1.0.0
Process completed with exit code 1.
"""

signature = ai_diagnosis.extract_error_signature(sample_log)
print("Extracted signature:", signature)

embedding = fingerprint.embed(signature)
past_failures = db.get_recent_failures("test/repo")
match, similarity = fingerprint.find_most_similar(embedding, past_failures)

print("Match found:", match is not None)
print("Similarity score:", similarity)