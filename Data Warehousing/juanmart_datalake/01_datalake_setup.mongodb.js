// DATABASE SELECTION
use('juanmart_datalake');

// COLLECTIONS
function ensureCollection(name, options) {
  if (db.getCollectionNames().includes(name)) {
    print(`Skipping ${name} — already exists.`);
  } else {
    db.createCollection(name, options);
    print(`Created ${name}.`);
  }
}

// POS Terminal Stream 
db.createCollection("raw_pos_events", {
  capped: true,
  size: 10 * 1024 * 1024,     // disk size cap 
  max: 50000                  // max document count
});

// Mobile Webhook Stream 
db.createCollection("raw_mobile_webhooks", {
  capped: true,
  size: 10 * 1024 * 1024, // 
  max: 50000
});

// Regional Logistics Tracker Stream 
db.createCollection("raw_logistics_events");

// Disable Validation
db.runCommand({ collMod: "raw_pos_events",        validator: {}, validationLevel: "off" });
db.runCommand({ collMod: "raw_mobile_webhooks",   validator: {}, validationLevel: "off" });
db.runCommand({ collMod: "raw_logistics_events",  validator: {}, validationLevel: "off" });

// INDEXES
// Logistics
db.raw_logistics_events.createIndex(
  { "_ingest.received_at": 1 },
  { expireAfterSeconds: 60 * 60 * 24 * 14, name: "ttl_received_at_14d" }
);

// Common query patterns 
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

// Debugging/replay lookups by originating vendor id.
db.raw_pos_events.createIndex({ "_ingest.source_id": 1 }, { name: "idx_pos_source_id" });
db.raw_mobile_webhooks.createIndex({ "_ingest.source_id": 1 }, { name: "idx_mobile_source_id" });
db.raw_logistics_events.createIndex({ "_ingest.source_id": 1 }, { name: "idx_logistics_source_id" });

// SECURE DRIVER INTERFACE 
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

// Verification
use ('juanmart_datalake');
print("Collections:");
db.getCollectionInfos().forEach(c => printjson(c));
print("Indexes per collection:");
["raw_pos_events", "raw_mobile_webhooks", "raw_logistics_events"].forEach(c => {
  print(`-- ${c} --`);
  db.getCollection(c).getIndexes().forEach(i => printjson(i));
});