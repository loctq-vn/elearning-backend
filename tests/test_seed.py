import pytest

from app.db.seed import _required_admin_credentials


def test_seed_requires_admin_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEED_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("SEED_ADMIN_PASSWORD", raising=False)

    with pytest.raises(RuntimeError, match="SEED_ADMIN_EMAIL"):
        _required_admin_credentials()


def test_seed_rejects_short_admin_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEED_ADMIN_EMAIL", "admin@example.test")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "short")

    with pytest.raises(RuntimeError, match="SEED_ADMIN_PASSWORD"):
        _required_admin_credentials()
