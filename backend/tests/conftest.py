import os
import tempfile

# Point the app at a throwaway data folder before anything imports the settings.
os.environ["STUDIO_DATA_DIR"] = tempfile.mkdtemp(prefix="studio-test-")
os.environ["STUDIO_DEMO_MODE"] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def as_role(role: str) -> dict:
    return {"X-Studio-Role": role, "X-Studio-User": f"test.{role}"}
