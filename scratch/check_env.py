import os
from dotenv import load_dotenv

# Try to load .env
load_dotenv(".env")

print(f"GOOGLE_API_KEY: {os.environ.get('GOOGLE_API_KEY')}")
print(f"GOOGLE_GENERATIVE_AI_API_KEY: {os.environ.get('GOOGLE_GENERATIVE_AI_API_KEY')}")
