import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

import requests
from google import genai
from google.genai import types

from app.config import (ALLOW_OPENROUTER, GEMINI_API_KEY, GEMINI_MODELS,
                        LLM_TIMEOUT_SECONDS, OPENROUTER_API_KEY, OPENROUTER_MODELS)
from .prompts import SYSTEM_PROMPT
from .schemas import InvoiceExtraction

FIELDS = ["invoice_number", "invoice_date", "supplier_name",
          "customer_name", "subtotal", "tax", "total", "currency"]

_blocked = {}   # (provider, model) -> কখন পর্যন্ত এড়িয়ে চলব


class AllProvidersFailed(Exception):
    pass


def _call_gemini(model: str, text: str):
    client = genai.Client(
        api_key=GEMINI_API_KEY,
        http_options=types.HttpOptions(timeout=int(LLM_TIMEOUT_SECONDS * 1000)))
    resp = client.models.generate_content(
        model=model,
        contents=f"DOCUMENT TEXT:\n{text}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=InvoiceExtraction,
            temperature=0,
        ),
    )
    return resp.text, model


def _call_openrouter(model: str, text: str):
    schema = json.dumps(InvoiceExtraction.model_json_schema())
    system = (SYSTEM_PROMPT +
              "\nReturn ONLY one JSON object matching this JSON schema, "
              "with no other text:\n" + schema)
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
        json={
            "model": model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": f"DOCUMENT TEXT:\n{text}"},
            ],
        },
        timeout=(10, LLM_TIMEOUT_SECONDS),
    )
    r.raise_for_status()
    body = r.json()
    # 'openrouter/free' নিজে model বাছে, তাই আসল নামটা response থেকে নিই
    return body["choices"][0]["message"]["content"], body.get("model", model)


def _parse(raw: str) -> InvoiceExtraction:
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    return InvoiceExtraction.model_validate_json(raw)   # schema না মিললে error


def _chain():
    chain = []
    if GEMINI_API_KEY:
        chain += [("gemini", m) for m in GEMINI_MODELS]
    if OPENROUTER_API_KEY and ALLOW_OPENROUTER:   # তৃতীয় পক্ষে নথি পাঠানো: ডিফল্টে বন্ধ
        chain += [("openrouter", m) for m in OPENROUTER_MODELS]
    return chain


def _cooldown_for(err: Exception) -> int:
    msg = str(err)
    if "404" in msg or "NOT_FOUND" in msg:
        return 3600     # model নেই: ঘণ্টাখানেক আর চেষ্টা নয়
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
        return 300      # limit ছুঁয়েছে: ৫ মিনিট অপেক্ষা
    return 30           # অন্য সাময়িক সমস্যা


HARD_DEADLINE_MARGIN = 5.0   # SDK-র নিজস্ব timeout-এর পরেও এতক্ষণ অপেক্ষা, তারপর call ছেড়ে দিই


def _with_deadline(fn, *args):
    """call আলাদা thread-এ চালায়; সময়সীমা পেরোলে ছেড়ে দিয়ে পরের model-এ যায়।"""
    pool = ThreadPoolExecutor(max_workers=1)
    fut = pool.submit(fn, *args)
    try:
        return fut.result(timeout=LLM_TIMEOUT_SECONDS + HARD_DEADLINE_MARGIN)
    except FutureTimeout:
        raise TimeoutError(f"no answer within {LLM_TIMEOUT_SECONDS + HARD_DEADLINE_MARGIN:g}s")
    finally:
        pool.shutdown(wait=False)


def extract_invoice(text: str):
    """একটার পর একটা model চেষ্টা করে। (result, meta) ফেরত দেয়।
    প্রতি model-এ একবারই চেষ্টা, কারণ OpenRouter-এর দৈনিক ৫০টা খরচ হয়ে যায়।"""
    attempts = []
    for provider, model in _chain():
        if _blocked.get((provider, model), 0) > time.time():
            attempts.append(f"{provider}/{model}: skipped (cooling down)")
            continue
        try:
            call = _call_gemini if provider == "gemini" else _call_openrouter
            raw, actual_model = _with_deadline(call, model, text)
            result = _parse(raw)
            return result, {"provider": provider, "model": actual_model,
                            "attempts": attempts}
        except Exception as e:
            attempts.append(f"{provider}/{model}: {type(e).__name__}: {str(e)[:120]}")
            _blocked[(provider, model)] = time.time() + _cooldown_for(e)
    raise AllProvidersFailed("; ".join(attempts) or "no provider configured (check .env)")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


NUMBER_RE = re.compile(r"\d[\d,]*\.?\d*")


def _value_in_evidence(name: str, value, evidence: str) -> bool:
    """মানটা সত্যিই evidence লাইনের ভেতরে আছে কি না।"""
    if name == "invoice_date":      # তারিখ ফরম্যাট বদলে লেখা হয়, তাই সরাসরি মেলে না
        return True
    if isinstance(value, (int, float)):
        for n in NUMBER_RE.findall(evidence):
            try:
                if abs(float(n.replace(",", "")) - float(value)) < 0.005:
                    return True
            except ValueError:
                pass
        return False
    return _norm(str(value)) in _norm(evidence)


def verify_evidence(result: InvoiceExtraction, source_text: str) -> list[str]:
    """(1) evidence সত্যিই document-এ আছে কি না, (2) মানটা evidence-এর ভেতরে আছে কি না।
    কোনোটা না মিললে confidence 'low' হয়ে manual review-এ যায়।"""
    src = _norm(source_text)
    flags = []
    for name in FIELDS:
        field = getattr(result, name)
        if field.value is None:
            continue
        if not field.evidence or _norm(field.evidence) not in src:
            field.confidence = "low"
            flags.append(f"{name}: evidence not found in source text")
        elif not _value_in_evidence(name, field.value, field.evidence):
            field.confidence = "low"
            flags.append(f"{name}: value does not match its evidence line")
    return flags