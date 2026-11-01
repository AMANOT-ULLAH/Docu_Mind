from google import genai
from app import config

client = genai.Client(api_key=config.GEMINI_API_KEY)

print("--- embedContent সমর্থন করে এমন model ---")
for m in client.models.list():
    actions = getattr(m, "supported_actions", None) or []
    if "embedContent" in actions:
        print(m.name)

print("--- একটা নমুনা embedding ---")
for name in ["gemini-embedding-001", "gemini-embedding-2"]:
    try:
        r = client.models.embed_content(model=name, contents="invoice from ABC Trading")
        print(name, "OK, dimension =", len(r.embeddings[0].values))
        break
    except Exception as e:
        print(name, "FAILED:", type(e).__name__, str(e)[:150])