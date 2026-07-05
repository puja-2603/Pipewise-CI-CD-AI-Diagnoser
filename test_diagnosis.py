from dotenv import load_dotenv
load_dotenv()

from app import ai_diagnosis

sample_log = """
=== Job: build ===
Collecting nonexistentpackage123==1.0.0
ERROR: Could not find a version that satisfies the requirement nonexistentpackage123==1.0.0
ERROR: No matching distribution found for nonexistentpackage123==1.0.0
Process completed with exit code 1.
"""

diagnosis, tokens = ai_diagnosis.diagnose(sample_log)
print(diagnosis)
print("Tokens used:", tokens)