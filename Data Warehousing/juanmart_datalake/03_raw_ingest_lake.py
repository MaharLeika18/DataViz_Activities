"""
juanmart_datalake/03_raw_ingest_lake.py

Ingests raw checkout payloads into the Data Lake landing collection and
prints a formatted landing audit.

Two modes:
  1. File mode  (--file provided): reads a real mock JSON/NDJSON file,
     stamps ingestion metadata, and infers each document's source stream
     from its own "source_system" field (falls back to "unknown").
  2. Synthetic mode (no --file): generates a mock batch across
     web_store / pos_terminals / mobile_app per STREAM_MIX, useful for
     quick smoke tests without needing a payload file on disk.

Usage:
    python -m juanmart_datalake.raw_ingest_lake
    python -m juanmart_datalake.raw_ingest_lake --file mock_checkout_payloads.json
    python -m juanmart_datalake.raw_ingest_lake --file mock_webhooks.ndjson --batch-size 500
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from pymongo.errors import BulkWriteError, PyMongoError

from juanmart_datalake.db import close_connection, get_client, get_db

from pathlib import Path

# =============================================================================
# LOGGING — format matches the required audit output exactly
# =============================================================================


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
log_run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
log_path = LOG_DIR / f"raw_ingest_lake_{log_run_id}.log"

formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

file_handler = logging.FileHandler(log_path, encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

COLLECTION_NAME = "raw_checkout_landing"

# Proportions used only in synthetic mode (no --file supplied).
STREAM_MIX = {
    "web_store": 820,
    "pos_terminals": 450,
    "mobile_app": 230,
}


# =============================================================================
# FILE PARSING (file mode) — handles single object, JSON array, or NDJSON
# =============================================================================

def load_payloads(file_path: Path) -> Iterator[Any]:
    raw_text = file_path.read_text(encoding="utf-8").strip()

    if not raw_text:
        logger.warning("Input file %s is empty.", file_path)
        return

    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, list):
            for item in parsed:
                yield item
        else:
            yield parsed
        return
    except json.JSONDecodeError:
        pass  # fall through to NDJSON handling

    line_errors = 0
    for line_num, line in enumerate(raw_text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError as exc:
            line_errors += 1
            logger.warning(
                "Skipping malformed JSON on line %s of %s: %s",
                line_num, file_path.name, exc,
            )

    if line_errors:
        logger.warning("%s line(s) skipped due to parse errors.", line_errors)


# =============================================================================
# METADATA STAMPING
# =============================================================================

def _infer_source_id(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("terminal_id", "device_id", "webhook_source", "tracker_id", "vendor_id"):
        if key in payload and payload[key]:
            return str(payload[key])
    return None


def _infer_schema_hint(payload: Any) -> str:
    if not isinstance(payload, dict):
        return "non_object_payload"
    return payload.get("schema_version") or payload.get("api_version") or "unversioned"


def stamp_ingestion_metadata(payload: Any, ingest_batch: str) -> dict:
    """
    Wraps a raw payload with ingestion metadata. source_system is pulled
    from the payload itself when present (file mode), otherwise "unknown" —
    this lets the audit summary group by stream regardless of which mode
    produced the document.
    """
    source_system = (
        payload.get("source_system", "unknown") if isinstance(payload, dict) else "unknown"
    )
    return {
        "_ingest": {
            "received_at": datetime.now(timezone.utc),
            "source_system": source_system,
            "source_id": _infer_source_id(payload) or "unknown",
            "ingest_batch": ingest_batch,
            "schema_hint": _infer_schema_hint(payload),
            "processed": False,
        },
        "payload": payload,
    }


# =============================================================================
# SYNTHETIC MOCK GENERATION (fallback when no --file is given)
# =============================================================================

def build_mock_payload(source_system: str, ingest_batch: str) -> dict:
    raw_payload = {
        "order_id": str(uuid.uuid4()),
        "amount": round(random.uniform(50, 5000), 2),
        "currency": "PHP",
        "source_system": source_system,
        "checkout_ts": datetime.now(timezone.utc).isoformat(),
    }
    return stamp_ingestion_metadata(raw_payload, ingest_batch)


def generate_synthetic_batch(ingest_batch: str) -> list[dict]:
    documents = []
    for source_system, count in STREAM_MIX.items():
        documents.extend(
            build_mock_payload(source_system, ingest_batch) for _ in range(count)
        )
    random.shuffle(documents)  # simulate interleaved multi-stream arrival
    return documents


def load_documents_from_file(file_path: Path, ingest_batch: str) -> list[dict]:
    return [
        stamp_ingestion_metadata(raw_payload, ingest_batch)
        for raw_payload in load_payloads(file_path)
    ]


# =============================================================================
# BATCH INSERT — ordered=False so one bad document doesn't abort the batch
# =============================================================================

def insert_documents(collection, documents: list[dict], batch_size: int) -> dict:
    stats = {"inserted": 0, "failed": 0}
    acknowledged = True

    for i in range(0, len(documents), batch_size):
        batch = documents[i : i + batch_size]
        try:
            result = collection.insert_many(batch, ordered=False)
            acknowledged = acknowledged and result.acknowledged
            stats["inserted"] += len(result.inserted_ids)
        except BulkWriteError as bwe:
            details = bwe.details
            n_inserted = details.get("nInserted", 0)
            errors = details.get("writeErrors", [])
            stats["inserted"] += n_inserted
            stats["failed"] += len(errors)
            for err in errors:
                logger.error(
                    "Insert failed at batch index %s: %s",
                    err.get("index"), err.get("errmsg"),
                )
        except PyMongoError as exc:
            stats["failed"] += len(batch)
            acknowledged = False
            logger.error(
                "Batch insert failed entirely (connectivity/server error): %s", exc
            )

    return {**stats, "acknowledged": acknowledged}


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest raw checkout payloads into the Data Lake landing collection."
    )
    parser.add_argument(
        "--file", type=Path, default=None,
        help="Path to a mock JSON/NDJSON payload file. Omit to generate a synthetic batch.",
    )
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()

    if args.file is not None and not args.file.exists():
        logger.error("File not found: %s", args.file)
        return 1

    logger.info("Initializing Data Lake MongoClient connection pool...")

    try:
        client = get_client()
        db = get_db()
        client.admin.command("ping")
    except PyMongoError as exc:
        logger.error("[!] Failed to establish Data Lake connection: %s", exc)
        return 1

    logger.info("[+] Successfully established Data Lake connection to: %s", db.name)
    logger.info("[*] Commencing raw JSON payload stream ingestion...")

    ingest_batch = str(uuid.uuid4())

    if args.file is not None:
        documents = load_documents_from_file(args.file, ingest_batch)
    else:
        documents = generate_synthetic_batch(ingest_batch)

    total_count = len(documents)
    logger.info(
        "[-] Staging %s raw JSON documents into collection: %s",
        f"{total_count:,}", COLLECTION_NAME,
    )

    collection = db[COLLECTION_NAME]
    result = insert_documents(collection, documents, args.batch_size)

    logger.info("[+] Ingestion Complete. Bulk Insert Acknowledged: %s", result["acknowledged"])

    # --- Landing audit summary ---
    logger.info("=" * 54)
    logger.info("DATA LAKE LANDING AUDIT ")
    logger.info("=" * 54)
    logger.info("TOTAL DOCUMENTS LANDED : %s", result["inserted"])

    stream_counts: dict[str, int] = {}
    for doc in documents:
        source = doc["_ingest"]["source_system"]
        stream_counts[source] = stream_counts.get(source, 0) + 1

    for source_system, count in stream_counts.items():
        logger.info("%s STREAM : %s documents", source_system.upper(), count)

    logger.info("=" * 54)

    if result["failed"] > 0:
        logger.warning("%s document(s) failed to insert — check logs above.", result["failed"])

    close_connection()
    logger.info("[+] Data Lake MongoClient connection pool gracefully closed.")

    return 0 if result["failed"] == 0 else 2

if __name__ == "__main__":
    raise SystemExit(main())