from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine
from sqlmodel.pool import StaticPool

from papertrials import db
from papertrials.config import get_settings
from papertrials.main import create_app
from papertrials.ml import predictor


@pytest.fixture(autouse=True)
def offline_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test talks to a real Ollama or loads real TabPFN weights unless it opts in."""
    settings = get_settings()
    monkeypatch.setattr(settings, "ollama_url", "http://127.0.0.1:9")
    monkeypatch.setattr(settings, "gemma_timeout_s", 0.5)
    monkeypatch.setattr(settings, "use_tabpfn", False)
    predictor._cache.clear()
    predictor._failed.clear()
    predictor.status.tabpfn_error = None


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    db.set_engine(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def client(session: Session) -> TestClient:
    return TestClient(create_app())
