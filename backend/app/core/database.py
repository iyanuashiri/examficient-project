import json

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
import boto3

from app.core.config import settings
from app.models.base import Base


def _resolve_database_url() -> str:
    """
    Resolve the database URL.
    - Locally: use settings.database_url (SQLite or a local Postgres URL).
    - In production (ECS): settings.db_secret_arn is set, so fetch from
      Secrets Manager.
    """
    secret_arn = settings.db_secret_arn

    if secret_arn:
        # Running in ECS — fetch credentials from Secrets Manager at startup.
        # The task role already has secretsmanager:GetSecretValue on this secret.
        client = boto3.client("secretsmanager")
        secret = json.loads(
            client.get_secret_value(SecretId=secret_arn)["SecretString"]
        )
        return (
            f"postgresql+psycopg2://"
            f"{secret['username']}:{secret['password']}"
            f"@{secret['host']}:{secret['port']}"
            f"/{secret['dbname']}"
        )

    # Local dev — fall back to whatever is in .env / config
    return settings.database_url


def _create_engine():
    """Create a SQLAlchemy engine, using Postgres in production and SQLite locally."""
    # url = settings.database_url

    url = _resolve_database_url()
    connect_args = {}

    if url.startswith("sqlite"):
        # SQLite requires this to allow use across threads (FastAPI runs sync
        # endpoints in a threadpool).
        connect_args = {"check_same_thread": False}

    return create_engine(url, echo=True, connect_args=connect_args)


engine = _create_engine()


@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    """Enforce ON DELETE / ON UPDATE on SQLite.

    SQLite ignores foreign keys unless the pragma is set per connection, so on
    a local SQLite database a cascade delete silently leaves orphans. Postgres
    enforces them natively and is unaffected.
    """
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_db_and_tables():
    Base.metadata.create_all(engine)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()