// -------------------------------------------------------------------------
// 1. DATABASE SELECTION
// -------------------------------------------------------------------------
use('juanmart_datalake');

// -------------------------------------------------------------------------
// 2. COLLECTIONS
//    One collection per source stream so schema drift in one vendor
//    never contaminates another, and so retention policy can differ
//    per source.
// -------------------------------------------------------------------------

function ensureCollection(name, options) {
  if (db.getCollectionNames().includes(name)) {
    print(`Skipping ${name} — already exists.`);
  } else {
    db.createCollection(name, options);
    print(`Created ${name}.`);
  }
}

// --- 2a. POS Terminal Stream (high volume, short-lived raw buffer) -----
// Capped: fixed size, FIFO eviction, no schema validator (accepts anything).
db.createCollection("raw_pos_events", {
  capped: true,
  size: 10 * 1024 * 1024, // disk size cap 
  max: 50000                  // max document count
});

// --- 2b. Mobile Webhook Stream (also bursty/high volume) ----------------
db.createCollection("raw_mobile_webhooks", {
  capped: true,
  size: 10 * 1024 * 1024, // 
  max: 50000
});

// --- 2c. Regional Logistics Tracker Stream (needs durability, not just
//         a rolling buffer — trackers may be delayed/replayed, and you
//         may need to look back further than a capped collection allows).
//         Uses a normal collection + TTL index instead of capping.
db.createCollection("raw_logistics_events");
// idk the instructions didnt say what to validate for this one so leave as is?

// -------------------------------------------------------------------------
// 3. EXPLICITLY DISABLE VALIDATION (defensive — in case these collections
//    already existed with a validator attached from an earlier schema).
// -------------------------------------------------------------------------
db.runCommand({ collMod: "raw_pos_events",        validator: {}, validationLevel: "off" });
db.runCommand({ collMod: "raw_mobile_webhooks",   validator: {}, validationLevel: "off" });
db.runCommand({ collMod: "raw_logistics_events",  validator: {}, validationLevel: "off" });

// -------------------------------------------------------------------------
// 4. INGESTION METADATA CONTRACT (enforced in your Python/Node ingestion
//    service, NOT by Mongo — documented here so indexes below make sense).
//
//    Every inbound payload gets wrapped like this before insertOne():
//
//    {
//      _ingest: {
//        received_at:   ISODate(),      // server clock, authoritative
//        source_system: "pos" | "mobile_webhook" | "logistics_tracker",
//        source_id:     "<vendor/terminal/tracker id>",
//        ingest_batch:  "<uuid>",       // for replay/debug
//        schema_hint:   "<vendor payload version, if known>",
//        processed:     false           // downstream ETL flips this
//      },
//      payload: { ...raw, unvalidated, vendor JSON as-is... }
//    }
// -------------------------------------------------------------------------

// -------------------------------------------------------------------------
// 5. INDEXES
//    Kept minimal and metadata-only — indexing into the raw `payload`
//    blob is deliberately avoided since its shape is unknown/unstable.
// -------------------------------------------------------------------------

// -- 5a. Logistics: TTL index instead of capping (self-purges after 14 days,
//        giving ETL a real window to catch up on delayed tracker replays).
db.raw_logistics_events.createIndex(
  { "_ingest.received_at": 1 },
  { expireAfterSeconds: 60 * 60 * 24 * 14, name: "ttl_received_at_14d" }
);

// -- 5b. Common query patterns across all three: "give me unprocessed
//        docs for source X since time Y" — this is what your Python
//        extraction workers will run constantly.
db.raw_pos_events.createIndex(
  { "_ingest.processed": 1, "_ingest.received_at": 1 },
  { name: "idx_pos_processed_time" }
);
db.raw_mobile_webhooks.createIndex(
  { "_ingest.processed": 1, "_ingest.received_at": 1 },
  { name: "idx_mobile_processed_time" }
);
db.raw_logistics_events.createIndex(
  { "_ingest.processed": 1, "_ingest.received_at": 1 },
  { name: "idx_logistics_processed_time" }
);

// -- 5c. Debugging/replay lookups by originating vendor id.
db.raw_pos_events.createIndex({ "_ingest.source_id": 1 }, { name: "idx_pos_source_id" });
db.raw_mobile_webhooks.createIndex({ "_ingest.source_id": 1 }, { name: "idx_mobile_source_id" });
db.raw_logistics_events.createIndex({ "_ingest.source_id": 1 }, { name: "idx_logistics_source_id" });

// -------------------------------------------------------------------------
// 6. SECURE DRIVER INTERFACE — least-privilege users for the two halves
//    of the pipeline. Run this against the `admin` db.
// -------------------------------------------------------------------------

/*
IMPORTANT: THIS IS NOT APPLICABLE FOR MONGODB ATLAS, I am just putting this here incase
again, really wish we had proper instructions but oh well 
If you want to test this w/ Atlas, comment out this code block and do the following:
  In Atlas: Database & Network Access -> Database Access -> Database Users -> Add New Database User
  Create lz_ingest_svc and lz_extractor_svc there, with autogenerated or custom passwords
  Under "Built-in Role" select Read and write (skip the custom role scoping)
*/

/*
use ('admin');

  // Insert only ingestion service account
db.createRole({
  role: "landingZoneWriter",
  privileges: [
    {
      resource: { db: "juanmart_landing_zone", collection: "" },
      actions: ["insert", "createIndex"] // createIndex only if writer auto-provisions; drop if not needed
    }
  ],
  roles: []
});

db.createUser({
  user: "lz_ingest_svc",
  pwd: passwordPrompt(),        
  roles: [{ role: "landingZoneWriter", db: "admin" }]
});

  // Python extraction account
  db.createRole({
  role: "landingZoneExtractor",
  privileges: [
    {
      resource: { db: "juanmart_landing_zone", collection: "" },
      actions: ["find", "update"]  // update needed only to mark processed:true
    }
  ],
  roles: []
});

db.createUser({
  user: "lz_extractor_svc",
  pwd: passwordPrompt(),
  roles: [{ role: "landingZoneExtractor", db: "admin" }]
});
*/

// Verification
use ('juanmart_datalake');
print("Collections:");
db.getCollectionInfos().forEach(c => printjson(c));
print("Indexes per collection:");
["raw_pos_events", "raw_mobile_webhooks", "raw_logistics_events"].forEach(c => {
  print(`-- ${c} --`);
  db.getCollection(c).getIndexes().forEach(i => printjson(i));
});