import time
from google import genai
from google.genai import types
from app.config import GEMINI_API_KEY

CANDIDATES = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.8-flash",
    "gemini-3-flash-preview",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
]

client = genai.Client(api_key=GEMINI_API_KEY)
for name in CANDIDATES:
    try:
        t = time.perf_counter()
        r = client.models.generate_content(
            model=name,
            contents="Reply with the single word: OK",
            config=types.GenerateContentConfig(max_output_tokens=20, temperature=0),
        )
        print(f"OK     {name:28} {time.perf_counter()-t:.1f}s  -> {(r.text or '').strip()[:20]}")
    except Exception as e:
        print(f"FAIL   {name:28} {str(e)[:110]}")
    time.sleep(2)