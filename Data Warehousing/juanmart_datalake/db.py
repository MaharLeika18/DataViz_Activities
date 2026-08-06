"""
Usage:

from juanmart_landing.db import get_db, health_check

db = get_db()
db.raw_pos_events.find_one({"_ingest.processed": False})

ok, detail = health_check()
"""

from __future__ import annotations
from dotenv import load_dotenv

import os
import threading
import logging
from dataclasses import dataclass
from typing import Optional

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import (
    ConnectionFailure,
    ServerSelectionTimeoutError,
    OperationFailure,
    ConfigurationError,
)

load_dotenv()
logger = logging.getLogger("juanmart_datalake.db")

# Config
@dataclass(frozen=True)
class MongoConfig:
    """
    Immutable configuration for the landing zone connection.
    Supports two modes:
      1. Atlas mode: a single ATLAS_URI env var (preferred for Atlas).
      2. Manual mode: separate MONGO_HOST/PORT/USER/PASSWORD vars
         (for self-hosted / on-prem MongoDB).
    """

    atlas_uri: Optional[str]
    host: Optional[str]
    port: int
    user: Optional[str]
    password: Optional[str]
    auth_source: str
    database: str
    replica_set: Optional[str]
    tls_enabled: bool
    max_pool_size: int
    min_pool_size: int
    connect_timeout_ms: int
    server_selection_timeout_ms: int
    app_name: str

    @staticmethod
    def _require(var_name: str) -> str:
        value = os.environ.get(var_name)
        if not value:
            raise ConfigurationError(
                f"Missing required environment variable: {var_name}"
            )
        return value

    @classmethod
    def from_env(cls) -> "MongoConfig":
        atlas_uri = os.environ.get("ATLAS_URI")

        if atlas_uri:
            # Atlas mode — host/user/password live inside the URI itself,
            # so none of them are required as separate env vars.
            return cls(
                atlas_uri=atlas_uri,
                host=None,
                port=27017,
                user=None,
                password=None,
                auth_source=os.environ.get("MONGO_AUTH_SOURCE", "admin"),
                database=os.environ.get("MONGO_DATABASE", "juanmart_landing_zone"),
                replica_set=None,
                tls_enabled=True,
                max_pool_size=int(os.environ.get("MONGO_MAX_POOL_SIZE", "50")),
                min_pool_size=int(os.environ.get("MONGO_MIN_POOL_SIZE", "5")),
                connect_timeout_ms=int(os.environ.get("MONGO_CONNECT_TIMEOUT_MS", "5000")),
                server_selection_timeout_ms=int(
                    os.environ.get("MONGO_SERVER_SELECTION_TIMEOUT_MS", "5000")
                ),
                app_name=os.environ.get("MONGO_APP_NAME", "juanmart-extraction-svc"),
            )

        # Manual mode — only reached if ATLAS_URI is NOT set.
        return cls(
            atlas_uri=None,
            host=cls._require("MONGO_HOST"),
            port=int(os.environ.get("MONGO_PORT", "27017")),
            user=cls._require("MONGO_USER"),
            password=cls._require("MONGO_PASSWORD"),
            auth_source=os.environ.get("MONGO_AUTH_SOURCE", "admin"),
            database=os.environ.get("MONGO_DATABASE", "juanmart_landing_zone"),
            replica_set=os.environ.get("MONGO_REPLICA_SET") or None,
            tls_enabled=os.environ.get("MONGO_TLS", "true").lower() == "true",
            max_pool_size=int(os.environ.get("MONGO_MAX_POOL_SIZE", "50")),
            min_pool_size=int(os.environ.get("MONGO_MIN_POOL_SIZE", "5")),
            connect_timeout_ms=int(os.environ.get("MONGO_CONNECT_TIMEOUT_MS", "5000")),
            server_selection_timeout_ms=int(
                os.environ.get("MONGO_SERVER_SELECTION_TIMEOUT_MS", "5000")
            ),
            app_name=os.environ.get("MONGO_APP_NAME", "juanmart-extraction-svc"),
        )

    def build_uri(self) -> str:
        if self.atlas_uri:
            return self.atlas_uri

        rs_part = f"&replicaSet={self.replica_set}" if self.replica_set else ""
        tls_part = "true" if self.tls_enabled else "false"
        return (
            f"mongodb://{self.user}:{self.password}@{self.host}:{self.port}/"
            f"?authSource={self.auth_source}"
            f"&tls={tls_part}"
            f"{rs_part}"
        )
    
# Singleton connection pool
class _MongoConnectionManager:
    """
    Thread-safe singleton wrapper around a single MongoClient instance.

    MongoClient itself already manages an internal connection pool, so the
    goal here is *not* to pool clients — it's to guarantee only ONE
    MongoClient (and therefore one pool) is ever created per process,
    since creating multiple clients defeats pooling entirely and can
    exhaust server-side connection limits under load.
    """

    _instance: Optional["_MongoConnectionManager"] = None
    _lock = threading.Lock()

    def __init__(self, config: MongoConfig):
        self._config = config
        self._client: MongoClient = self._build_client(config)

    @staticmethod
    def _build_client(config: MongoConfig) -> MongoClient:
        try:
            client = MongoClient(
                config.build_uri(),
                maxPoolSize=config.max_pool_size,
                minPoolSize=config.min_pool_size,
                connectTimeoutMS=config.connect_timeout_ms,
                serverSelectionTimeoutMS=config.server_selection_timeout_ms,
                appname=config.app_name,
                retryWrites=True,
                retryReads=True,
            )
            return client
        except ConfigurationError:
            logger.exception("Invalid MongoDB configuration while building client.")
            raise

    @classmethod
    def get_instance(cls, config: Optional[MongoConfig] = None) -> "_MongoConnectionManager":
        # Fast path: no lock needed once initialized.
        if cls._instance is not None:
            return cls._instance

        # Slow path: double-checked locking to avoid a race where two
        # threads both see _instance as None and both start building clients.
        with cls._lock:
            if cls._instance is None:
                resolved_config = config or MongoConfig.from_env()
                instance = cls.__new__(cls)
                instance.__init__(resolved_config)
                cls._instance = instance  
                logger.info(
                    "MongoClient initialized (pool max=%s min=%s db=%s)",
                    resolved_config.max_pool_size,
                    resolved_config.min_pool_size,
                    resolved_config.database,
                )
        return cls._instance

    @property
    def client(self) -> MongoClient:
        return self._client

    @property
    def config(self) -> MongoConfig:
        return self._config

    def get_database(self) -> Database:
        return self._client[self._config.database]

    def close(self) -> None:
        """
        Closes the pool and clears the singleton so a fresh client can be
        built on next access. Intended for graceful shutdown hooks and
        test teardown — not for use mid-request.
        """
        with _MongoConnectionManager._lock:
            if self._client is not None:
                self._client.close()
                logger.info("MongoClient connection pool closed.")
            _MongoConnectionManager._instance = None

# Public accessors
def get_client() -> MongoClient:
    """Returns the process-wide singleton MongoClient."""
    return _MongoConnectionManager.get_instance().client


def get_db() -> Database:
    """Returns the landing zone Database handle bound to the singleton client."""
    return _MongoConnectionManager.get_instance().get_database()


def close_connection() -> None:
    """Call this from application shutdown hooks (e.g. atexit, FastAPI lifespan)."""
    instance = _MongoConnectionManager._instance
    if instance is not None:
        instance.close()

# Health check
def health_check(timeout_ms: int = 3000) -> tuple[bool, dict]:
    """
    Performs a real round-trip health check against MongoDB rather than
    just confirming a client object exists in memory. Uses the `ping`
    command, which is the lightest possible operation that still proves
    the server is reachable and authenticated.

    Returns:
        (is_healthy: bool, detail: dict) — detail includes latency and
        error info suitable for logging or exposing on a /health endpoint.
    """
    import time

    manager = _MongoConnectionManager.get_instance()
    client = manager.client

    start = time.monotonic()
    try:
        # 'ping' requires no auth beyond connection-level auth and touches
        # the server directly — a valid proxy for "can we actually talk
        # to Mongo right now," unlike checking pool state locally.
        client.admin.command("ping", maxTimeMS=timeout_ms)
        latency_ms = round((time.monotonic() - start) * 1000, 2)

        return True, {
            "status": "healthy",
            "latency_ms": latency_ms,
            "database": manager.config.database,
            "host": manager.config.host,
        }

    except (ServerSelectionTimeoutError, ConnectionFailure) as exc:
        logger.error("MongoDB health check failed — connection issue: %s", exc)
        return False, {
            "status": "unreachable",
            "error": "connection_failure",
            "message": str(exc),
        }

    except OperationFailure as exc:
        # Distinguish auth/permission failures from connectivity failures —
        # these need different on-call responses (rotate creds vs. check network).
        logger.error("MongoDB health check failed — auth/permission issue: %s", exc)
        return False, {
            "status": "unauthorized",
            "error": "operation_failure",
            "message": str(exc),
        }

    except Exception as exc:  # noqa: BLE001 — health checks must never raise
        logger.exception("MongoDB health check failed — unexpected error.")
        return False, {
            "status": "error",
            "error": "unexpected",
            "message": str(exc),
        }