import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("No API Key found")
else:
    genai.configure(api_key=api_key)
    try:
        print("Listing models...")
    except Exception as e:
        print(f"Error listing models: {e}")
    else:
        print("Listing GEMINI models only...")
        for m in genai.list_models():
            if 'gemini' in m.name:
                print(f"Name: {m.name}")
