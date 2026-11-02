import importlib
import os

from app import config


def test_omp_thread_limit_is_set_by_default(monkeypatch):
    monkeypatch.delenv("OMP_THREAD_LIMIT", raising=False)
    importlib.reload(config)
    assert os.environ["OMP_THREAD_LIMIT"] == "1"


def test_user_value_is_not_overridden(monkeypatch):
    monkeypatch.setenv("OMP_THREAD_LIMIT", "3")
    importlib.reload(config)
    assert os.environ["OMP_THREAD_LIMIT"] == "3"


def test_ocr_workers_default_is_positive():
    assert config.OCR_WORKERS >= 1