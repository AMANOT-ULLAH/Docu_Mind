from pathlib import Path

HERE = Path(__file__).parent


def patch(path, old, new):
    s = path.read_text(encoding="utf-8")
    assert s.count(old) == 1, f"{path.name}: expected text not found exactly once: {old[:50]!r}"
    path.write_text(s.replace(old, new), encoding="utf-8")
    print("patched", path.name)


# config: timeout সেটিং
cfg = HERE / "app" / "config.py"
text = cfg.read_text(encoding="utf-8")
if "LLM_TIMEOUT_SECONDS" not in text:
    cfg.write_text(text.rstrip("\n") + '\nLLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "45"))\n',
                   encoding="utf-8")
    print("patched config.py")

ex = HERE / "app" / "extraction" / "llm_extractor.py"
patch(ex,
      "from app.config import (GEMINI_API_KEY, GEMINI_MODELS,\n"
      "                        OPENROUTER_API_KEY, OPENROUTER_MODELS)",
      "from app.config import (GEMINI_API_KEY, GEMINI_MODELS, LLM_TIMEOUT_SECONDS,\n"
      "                        OPENROUTER_API_KEY, OPENROUTER_MODELS)")
patch(ex,
      "client = genai.Client(api_key=GEMINI_API_KEY)",
      "client = genai.Client(\n"
      "        api_key=GEMINI_API_KEY,\n"
      "        http_options=types.HttpOptions(timeout=int(LLM_TIMEOUT_SECONDS * 1000)))")
patch(ex, "timeout=90,", "timeout=(10, LLM_TIMEOUT_SECONDS),")

# evaluator: কোন model উত্তর দিল সেটা প্রতি লাইনে দেখাও
ev = HERE.parent / "evaluation" / "run_eval.py"
patch(ev,
      "f\" {rec.get('seconds')}s  wrong=",
      "f\" {rec.get('seconds')}s [{(rec.get('provider') or '-').split('/')[-1]}] wrong=")