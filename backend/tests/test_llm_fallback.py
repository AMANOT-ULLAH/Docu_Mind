import pytest

from app.extraction import llm_extractor as L


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setattr(L, "_chain", lambda: [("gemini", "m1"), ("gemini", "m2")])
    monkeypatch.setattr(L, "_blocked", {})
    monkeypatch.setattr(L, "_parse", lambda raw: raw)


def test_falls_back_when_first_model_times_out(monkeypatch):
    calls = []

    def fake(model, text):
        calls.append(model)
        if model == "m1":
            raise TimeoutError("timed out")
        return "RESULT", model

    monkeypatch.setattr(L, "_call_gemini", fake)
    result, meta = L.extract_invoice("x")
    assert result == "RESULT"
    assert meta["model"] == "m2"
    assert calls == ["m1", "m2"]
    assert "TimeoutError" in meta["attempts"][0]


def test_slow_model_is_skipped_on_next_call(monkeypatch):
    calls = []

    def fake(model, text):
        calls.append(model)
        if model == "m1":
            raise TimeoutError("t")
        return "R", model

    monkeypatch.setattr(L, "_call_gemini", fake)
    L.extract_invoice("a")
    L.extract_invoice("b")
    assert calls == ["m1", "m2", "m2"]


def test_all_fail_raises(monkeypatch):
    def fake(model, text):
        raise TimeoutError("t")

    monkeypatch.setattr(L, "_call_gemini", fake)
    with pytest.raises(L.AllProvidersFailed):
        L.extract_invoice("x")