"""Remediation REST API 测试（mock DB）。"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.remediation_log import RemediationLog
from app.models.alert import Alert
from app.models.user import User


# ── Fixtures ──

def _fake_user():
    u = MagicMock(spec=User)
    u.id = 1
    u.username = "testuser"
    return u


def _fake_remediation_log(**overrides):
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=1,
        alert_id=10,
        host_id=5,
        status="pending_approval",
        risk_level="confirm",
        runbook_name="restart_service",
        diagnosis_json={"root_cause": "OOM"},
        command_results_json=[],
        verification_passed=None,
        blocked_reason=None,
        triggered_by="auto",
        approved_by=None,
        approved_at=None,
        started_at=now,
        completed_at=None,
        created_at=now,
    )
    defaults.update(overrides)
    obj = MagicMock(spec=RemediationLog)
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _fake_alert(**overrides):
    defaults = dict(id=10, host_id=5, status="firing", severity="warning", title="High CPU")
    defaults.update(overrides)
    obj = MagicMock(spec=Alert)
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class FakeScalarResult:
    """模拟 db.execute() 返回的 result，支持 .scalar() / .scalar_one_or_none() / .scalars().all()。"""
    def __init__(self, value=None, items=None):
        self._value = value
        self._items = items or []

    def scalar(self):
        return self._value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        return self._items


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def client(mock_db):
    user = _fake_user()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: mock_db

    transport = ASGITransport(app=app)
    c = AsyncClient(transport=transport, base_url="http://test")
    yield c
    app.dependency_overrides.clear()


# ── Tests ──

@pytest.mark.asyncio
async def test_list_remediations(client, mock_db):
    log1 = _fake_remediation_log(id=1)
    log2 = _fake_remediation_log(id=2, status="success")
    mock_db.execute = AsyncMock(side_effect=[
        FakeScalarResult(value=2),  # count
        FakeScalarResult(items=[log1, log2]),  # list
    ])

    resp = await client.get("/api/v1/remediations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_remediations_with_filters(client, mock_db):
    mock_db.execute = AsyncMock(side_effect=[
        FakeScalarResult(value=0),
        FakeScalarResult(items=[]),
    ])

    resp = await client.get("/api/v1/remediations?status=success&host_id=5")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_get_remediation_detail(client, mock_db):
    log = _fake_remediation_log()
    mock_db.execute = AsyncMock(return_value=FakeScalarResult(value=log))

    resp = await client.get("/api/v1/remediations/1")
    assert resp.status_code == 200
    assert resp.json()["id"] == 1


@pytest.mark.asyncio
async def test_get_remediation_not_found(client, mock_db):
    mock_db.execute = AsyncMock(return_value=FakeScalarResult(value=None))

    resp = await client.get("/api/v1/remediations/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_approve_remediation(client, mock_db):
    log = _fake_remediation_log(status="pending_approval")
    mock_db.execute = AsyncMock(return_value=FakeScalarResult(value=log))

    with patch("app.routers.remediation.log_audit", new_callable=AsyncMock):
        resp = await client.post("/api/v1/remediations/1/approve", json={"comment": "LGTM"})

    assert resp.status_code == 200
    assert log.status == "approved"
    assert log.approved_by == 1


@pytest.mark.asyncio
async def test_approve_wrong_status(client, mock_db):
    log = _fake_remediation_log(status="success")
    mock_db.execute = AsyncMock(return_value=FakeScalarResult(value=log))

    resp = await client.post("/api/v1/remediations/1/approve", json={})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_reject_remediation(client, mock_db):
    log = _fake_remediation_log(status="pending_approval")
    mock_db.execute = AsyncMock(return_value=FakeScalarResult(value=log))

    with patch("app.routers.remediation.log_audit", new_callable=AsyncMock):
        resp = await client.post("/api/v1/remediations/1/reject", json={"comment": "Too risky"})

    assert resp.status_code == 200
    assert log.status == "rejected"


@pytest.mark.asyncio
async def test_trigger_remediation(client, mock_db):
    alert = _fake_alert()
    # First call: find alert; Second call: check existing; then commit/refresh
    mock_db.execute = AsyncMock(side_effect=[
        FakeScalarResult(value=alert),      # alert lookup
        FakeScalarResult(value=None),       # no existing remediation
    ])

    with patch("app.routers.remediation.log_audit", new_callable=AsyncMock):
        resp = await client.post("/api/v1/alerts/10/remediate")

    assert resp.status_code == 200
    mock_db.add.assert_called_once()


@pytest.mark.asyncio
async def test_trigger_remediation_alert_not_found(client, mock_db):
    mock_db.execute = AsyncMock(return_value=FakeScalarResult(value=None))

    resp = await client.post("/api/v1/alerts/999/remediate")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_trigger_remediation_conflict(client, mock_db):
    alert = _fake_alert()
    existing = _fake_remediation_log(status="executing")
    mock_db.execute = AsyncMock(side_effect=[
        FakeScalarResult(value=alert),
        FakeScalarResult(value=existing),
    ])

    resp = await client.post("/api/v1/alerts/10/remediate")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_stats(client, mock_db):
    mock_db.execute = AsyncMock(side_effect=[
        FakeScalarResult(value=100),   # total
        FakeScalarResult(value=75),    # success
        FakeScalarResult(value=15),    # failed
        FakeScalarResult(value=10),    # pending
        FakeScalarResult(value=320.5), # avg duration
        FakeScalarResult(value=5),     # today
        FakeScalarResult(value=25),    # week
    ])

    resp = await client.get("/api/v1/remediations/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 100
    assert data["success_rate"] == 75.0
    assert data["avg_duration_seconds"] == 320.5
    assert data["today_count"] == 5
    assert data["week_count"] == 25
