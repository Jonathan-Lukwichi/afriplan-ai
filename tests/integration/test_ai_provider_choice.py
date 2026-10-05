"""The user picks the AI reader per run: Claude or Gemini, among those whose key the server holds.
AI_PROVIDER stays the default; a run's own choice wins; a choice without a key is refused at upload."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import core.run_jobs as run_jobs
import routers.compare as compare_router
from agent.pdf_pipeline.llm import PdfLLM
from agent.pdf_pipeline.passes.run import EstimatorRun
from core.config import ai_providers_ready
from core.gemini_client import GeminiClient
from main import app

PDF = ("files", ("set.pdf", b"%PDF-1.4 stub", "application/pdf"))


@pytest.fixture
def keys(monkeypatch):
    """Clear every provider setting; the test sets the keys it needs."""
    for k in ("AI_PROVIDER", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    return monkeypatch


@pytest.fixture
def seen_llm(monkeypatch):
    """Stand-in for the PDF estimator: records the reader it was handed, calls no AI."""
    seen = {}

    def fake_estimator(files, *, llm=None, on_progress=None, **_):
        seen["llm"] = llm
        return EstimatorRun(run_id="fake", success=False, error="stub")

    monkeypatch.setattr(run_jobs, "run_pdf_estimator", fake_estimator)
    return seen


def test_only_providers_with_a_key_are_offered(keys):
    assert ai_providers_ready() == []
    keys.setenv("GEMINI_API_KEY", "AIza")
    assert ai_providers_ready() == ["gemini"]
    keys.setenv("ANTHROPIC_API_KEY", "sk-ant-x")
    assert ai_providers_ready() == ["claude", "gemini"]


def test_the_screen_learns_the_choices_and_the_default(keys):
    keys.setenv("ANTHROPIC_API_KEY", "sk-ant-x")
    keys.setenv("GEMINI_API_KEY", "AIza")
    keys.setenv("AI_PROVIDER", "gemini")
    body = TestClient(app).get("/api/ai/providers").json()
    assert body == {"available": ["claude", "gemini"], "default": "gemini"}


def test_no_key_means_no_choice_and_no_default(keys):
    assert TestClient(app).get("/api/ai/providers").json() == {"available": [], "default": None}


def test_a_chosen_provider_beats_the_server_default(keys):
    keys.setenv("ANTHROPIC_API_KEY", "sk-ant-x")       # the default would be Claude
    keys.setenv("GEMINI_API_KEY", "AIza-real")
    llm = PdfLLM(system_prompt="x", provider="gemini")
    assert isinstance(llm._client, GeminiClient) and llm._client._key == "AIza-real"


def test_a_pdf_run_is_read_by_the_provider_the_user_picked(keys, seen_llm):
    keys.setenv("ANTHROPIC_API_KEY", "sk-ant-x")
    keys.setenv("GEMINI_API_KEY", "AIza")
    r = TestClient(app).post("/api/runs", files=[PDF], data={"pipeline": "pdf", "ai_provider": "gemini"})
    assert r.status_code == 200
    assert isinstance(seen_llm["llm"]._client, GeminiClient)


def test_without_a_choice_the_server_default_reads_the_run(keys, seen_llm):
    keys.setenv("GEMINI_API_KEY", "AIza")
    r = TestClient(app).post("/api/runs", files=[PDF], data={"pipeline": "pdf"})
    assert r.status_code == 200
    assert seen_llm["llm"] is None          # the estimator builds its default reader itself


@pytest.mark.parametrize("choice", ["gemini", "openai"])
def test_a_provider_without_a_key_or_unknown_is_refused_at_upload(keys, seen_llm, choice):
    keys.setenv("ANTHROPIC_API_KEY", "sk-ant-x")       # Gemini has no key on this server
    r = TestClient(app).post("/api/runs", files=[PDF], data={"pipeline": "pdf", "ai_provider": choice})
    assert r.status_code == 400 and choice in r.json()["detail"]
    assert "llm" not in seen_llm


def test_both_compare_passes_the_choice_to_its_pdf_run(keys, seen_llm, monkeypatch):
    keys.setenv("ANTHROPIC_API_KEY", "sk-ant-x")
    keys.setenv("GEMINI_API_KEY", "AIza")
    monkeypatch.setattr(compare_router, "run_dxf_job", lambda run_id, pairs: None)
    r = TestClient(app).post("/api/compare", data={"ai_provider": "gemini"}, files=[
        ("pdf_files", ("set.pdf", b"%PDF-1.4 stub", "application/pdf")),
        ("dxf_files", ("a.dxf", b"0\nEOF\n", "application/dxf")),
    ])
    assert r.status_code == 200
    assert isinstance(seen_llm["llm"]._client, GeminiClient)
