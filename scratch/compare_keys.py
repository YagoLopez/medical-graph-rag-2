import os
from dotenv import load_dotenv

# Replicate what was in the file
load_dotenv(".env")
env_key = os.environ.get("GOOGLE_API_KEY")
hardcoded_key = os.environ.get("GOOGLE_API_KEY") # Fixed: removed hardcoded key

print(f"Env Key:        '{env_key}' (len: {len(env_key)})")
print(f"Hardcoded Key:  '{hardcoded_key}' (len: {len(hardcoded_key)})")
print(f"Are they equal? {env_key == hardcoded_key}")

if env_key != hardcoded_key:
    for i, (a, b) in enumerate(zip(env_key, hardcoded_key)):
        if a != b:
            print(f"Difference at index {i}: '{a}' (ord: {ord(a)}) vs '{b}' (ord: {ord(b)})")
            break
    else:
        if len(env_key) != len(hardcoded_key):
            print(f"Length mismatch: {len(env_key)} vs {len(hardcoded_key)}")
