from orchestrator.storage import resolve_database_url


def test_resolve_database_url_prefers_explicit(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./explicit.db")
    monkeypatch.setenv("DATABASE_MODE", "postgres")
    assert resolve_database_url() == "sqlite:///./explicit.db"


def test_resolve_database_url_postgres_mode(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_MODE", "postgres")
    monkeypatch.setenv("POSTGRES_USER", "user1")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pass1")
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DB", "dbname")
    assert resolve_database_url() == "postgresql://user1:pass1@db:5432/dbname"


def test_resolve_database_url_sqlite_mode(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_MODE", "sqlite")
    monkeypatch.setenv("SQLITE_PATH", "/tmp/a2a.db")
    assert resolve_database_url() == "sqlite:////tmp/a2a.db"
