"""
juanmart_datalake/03_raw_ingest_lake.py

Ingests a mock multi-stream checkout payload batch into the Data Lake
landing collection and prints a formatted landing audit.

Usage:
    python 03_raw_ingest_lake.py
"""

from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime, timezone

from pymongo.errors import PyMongoError

from juanmart_datalake.db import get_db, get_client, close_connection

# =============================================================================
# LOGGING — format matches the required audit output exactly
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger()

COLLECTION_NAME = "raw_checkout_landing"

# Stream mix — proportions of the mock batch, matching the target log output.
STREAM_MIX = {
    "web_store": 820,
    "pos_terminals": 450,
    "mobile_app": 230,
}


def build_mock_payload(source_system: str, ingest_batch: str) -> dict:
    """
    Generates one mock checkout payload for the given stream, wrapped in
    the standard _ingest metadata contract.
    """
    raw_payload = {
        "order_id": str(uuid.uuid4()),
        "amount": round(random.uniform(50, 5000), 2),
        "currency": "PHP",
        "source_system": source_system,
        "checkout_ts": datetime.now(timezone.utc).isoformat(),
    }
    return {
        "_ingest": {
            "received_at": datetime.now(timezone.utc),
            "source_system": source_system,
            "ingest_batch": ingest_batch,
            "processed": False,
        },
        "payload": raw_payload,
    }


def main() -> int:
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
    documents = []
    for source_system, count in STREAM_MIX.items():
        documents.extend(
            build_mock_payload(source_system, ingest_batch) for _ in range(count)
        )
    random.shuffle(documents)  # simulate interleaved multi-stream arrival

    total_count = len(documents)
    logger.info(
        "[-] Staging %s raw JSON documents into collection: %s",
        f"{total_count:,}", COLLECTION_NAME,
    )

    try:
        collection = db[COLLECTION_NAME]
        result = collection.insert_many(documents, ordered=False)
        acknowledged = result.acknowledged
        inserted_count = len(result.inserted_ids)
    except PyMongoError as exc:
        logger.error("[!] Bulk insert failed: %s", exc)
        close_connection()
        return 1

    logger.info("[+] Ingestion Complete. Bulk Insert Acknowledged: %s", acknowledged)

    # --- Landing audit summary ---
    logger.info("=" * 54)
    logger.info("DATA LAKE LANDING AUDIT ")
    logger.info("=" * 54)
    logger.info("TOTAL DOCUMENTS LANDED : %s", inserted_count)

    stream_counts = {source: 0 for source in STREAM_MIX}
    for doc in documents:
        stream_counts[doc["_ingest"]["source_system"]] += 1

    for source_system, count in stream_counts.items():
        logger.info("%s STREAM : %s documents", source_system.upper(), count)

    logger.info("=" * 54)

    close_connection()
    logger.info("[+] Data Lake MongoClient connection pool gracefully closed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())