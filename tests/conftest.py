"""Shared rehearsal props for every test in this office."""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    """A visitor who can walk into the office without it actually being open for real traffic."""
    return TestClient(create_app())
