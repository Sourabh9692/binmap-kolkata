# Architecture

React + TypeScript + MapLibre → same-origin FastAPI → SQLAlchemy → SQLite locally or PostgreSQL/PostGIS in Compose.

Dexie/IndexedDB holds private draft payloads and photo blobs. Sync creates an immutable survey session, uploads a photo when needed, then sends the observation/inspection. A successful response deletes the local draft. Server-side digest comparisons make retries idempotent; a reused ID with altered evidence is rejected. Access keys remain in React memory and are never stored in IndexedDB or the service worker.

The service worker caches only same-origin static files and an allowlist of public GET endpoints. Authenticated endpoints and external map tiles are excluded. Offline data can be stale; the interface shows offline status and snapshot time.

## Data model

- `street_segments`: reproducible OSM-derived geometry and length.
- `source_records`: raw OSM tags, source URLs and unverified point candidates.
- `survey_sessions`: pseudonymous surveyor alias, timestamp, consent.
- `segment_inspections`: immutable coverage/visibility/result declarations.
- `observations`: immutable GPS, time, type, condition, access and evidence reference.
- `evidence_files`: sanitized private image path and SHA-256 checksum.
- `verification_reviews`: append-only reviewer decisions; the latest decision governs visibility.
- `audit_events`: role-level audit of writes and reviews.

Physical `bin_assets` are deliberately not inferred from proximity in v0.1. Several observations can refer to one real bin. All UI counts say “observations” or “OSM candidates”; do not present their sum as unique assets.

Geometry JSON is portable. PostgreSQL adds generated PostGIS geometries and GiST indexes to street/source tables. SQLite uses Shapely/pyproj for validation. Schema bootstrap is idempotent for version 1; schema evolution requires a migration implementation.

## Evidence decisions

An imported OSM feature is never a field observation. A submission is never reviewed by default. Public export whitelists fields and omits notes, identities, and private photo references. Images are decoded and re-encoded with stripped EXIF and bounded dimensions.

A complete negative inspection records that no bin was observed under stated conditions. It does not become “verified underserved” merely because an online inventory is empty. The separate analysis command computes shortest network distances to known usable observations with explicit uncertainty.

## Geographic pipeline

Project to EPSG:32645 (metres). Locate the nearest edge, split it at the anchor projection, subtract the perpendicular connector from the 500 m budget, and run Dijkstra. Clip each reachable edge at the exact remaining path budget. Subdivide output into segments of at most 100 m. A 15 m buffer is only a display polygon.

The downloaded graph extends beyond the catchment. OSM node connectivity and access tags can be wrong; geometric proximity does not prove that a perpendicular connector crosses an accessible space. The generated graph and source hashes make the assumption reviewable.

XML fallback is bounded by its recorded API bbox, not the Overpass distance parameter. It removes non-walkable ways and isolated nodes. Street filtering does not claim field validation of gates, crossings or access restrictions.

## Deployment boundary

Local by default. Compose uses an unprivileged application user, a database healthcheck, named persistence volumes, and localhost-only port exposure. No cloud services or billable resources are created. Before public deployment, replace shared keys with individual identities, add upload/request limits at the reverse proxy, HTTPS, backups, monitoring and production evidence storage.
