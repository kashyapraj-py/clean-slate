from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from cleanslate.api import ScanSessions, create_app
from cleanslate.models import CleanSlateError, ScanResult
from conftest import python_project


def test_full_api_cleanup_restore_journey(workspace: Path, data_dir: Path):
    project = python_project(workspace)
    cache = project / "__pycache__"
    cache.mkdir()
    (cache / "x.pyc").write_bytes(b"test")
    app = create_app(data_dir=data_dir, ui_dir=workspace / "no-frontend")
    client = TestClient(app, base_url="http://localhost")
    response = client.get("/api/health")
    assert response.status_code == 200
    response = client.post("/api/scans", json={"root": str(workspace)})
    assert response.status_code == 200, response.text
    scan_result = response.json()
    assert scan_result["candidates"][0]["can_clean"] is True
    response = client.post("/api/cleanups", json={
        "scan_id": scan_result["scan_id"],
        "candidate_ids": [scan_result["candidates"][0]["id"]],
    })
    assert response.status_code == 200, response.text
    op = response.json()["operation"]
    assert not cache.exists()
    assert len(client.get("/api/history").json()) == 1
    response = client.post("/api/restores", json={"operation_id": op["id"]})
    assert response.status_code == 200
    assert (cache / "x.pyc").read_bytes() == b"test"
    # Scan receipts are single-use to prevent replaying stale plans.
    response = client.post("/api/cleanups", json={
        "scan_id": scan_result["scan_id"],
        "candidate_ids": [scan_result["candidates"][0]["id"]],
    })
    assert response.status_code == 400


def test_rejects_untrusted_browser_origins_and_form_posts(workspace: Path, data_dir: Path):
    client = TestClient(create_app(data_dir=data_dir), base_url="http://localhost")
    rejected = client.post("/api/scans", json={"root": str(workspace)},
                           headers={"Origin": "https://attacker.example"})
    assert rejected.status_code == 403
    rejected = client.post("/api/scans", data={"root": str(workspace)})
    assert rejected.status_code == 415
    accepted = client.post("/api/scans", json={"root": str(workspace)},
                           headers={"Origin": "http://localhost:5173"})
    assert accepted.status_code == 200


def test_scan_sessions_expire():
    sessions = ScanSessions(lifetime_seconds=-1)
    identifier = sessions.put(ScanResult(root="/tmp"))
    try:
        sessions.take(identifier)
    except CleanSlateError as exc:
        assert "expired" in str(exc)
    else:
        raise AssertionError("Expired scan receipt should not be accepted")


def test_api_requires_review_approval(workspace: Path, data_dir: Path):
    project = python_project(workspace)
    output = project / "dist"
    output.mkdir()
    (output / "output.whl").write_bytes(b"package")
    client = TestClient(create_app(data_dir=data_dir), base_url="http://localhost")
    scanned = client.post("/api/scans", json={"root": str(workspace)}).json()
    assert scanned["candidates"][0]["risk"] == "review"
    refused = client.post("/api/cleanups", json={"scan_id": scanned["scan_id"],
        "candidate_ids": [scanned["candidates"][0]["id"]], "confirm_review": False})
    assert refused.status_code == 400
    assert output.exists()
    rescanned = client.post("/api/scans", json={"root": str(workspace)}).json()
    approved = client.post("/api/cleanups", json={"scan_id": rescanned["scan_id"],
        "candidate_ids": [rescanned["candidates"][0]["id"]], "confirm_review": True})
    assert approved.status_code == 200
    assert not output.exists()
