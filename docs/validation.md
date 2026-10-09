# Validation record — 9 October 2026

## Locally verified

- **27 API/geospatial tests passed.** Separate roles, authentication failures, immutable retry/conflict handling, negative-evidence rules, stale evidence, review retraction, private photos, EXIF removal, public export redaction, GPS limits, time/coordinate validation, uploads, partial-edge catchments and network paths.
- **3 browser tests passed.** Offline draft reload → upload → review, mobile layout/report uncertainty, and GPS/photo observation → private pending evidence → approval. Tests use isolated temporary databases.
- **Production frontend build passed.** MapLibre 6.13.0 worker is emitted as a bundled asset; overlay loading is checked in browser tests.
- **Frontend dependency audit: 0 reported vulnerabilities** after upgrading MapLibre.
- Real OSM XML download succeeded; both Overpass services failed during the initial attempt. The larger OSM bbox exceeded API limits; the documented smaller bbox succeeded.
- User-selected pin: **22.4909012, 88.3677315**. Along-network limit: 500 m. Anchor-to-edge offset: approximately 5.3 m.
- Generated **425 unique valid segments**, totaling **15,059.60 m**, each ≤100 m. All geometry lies within the necessary 500 m straight-line upper bound. This is a geometric sanity check, not a claim of independently verified walkability.
- Re-import created **0** additional records, confirming idempotent import for this snapshot.
- Accessibility export produced **1,243 samples**, all correctly `unknown` with no verified field inventory.
- **2 OSM candidates** in the surrounding extract; **0 real field observations** and **0 reviewed coverage**. Candidate counts do not establish bin absence or physical asset totals.

## Infrastructure checks

The [GitHub Actions validation run](https://github.com/Sourabh9692/binmap-kolkata/actions/runs/37883200740) passed against code commit `53e8094`: **28 API/geospatial/PostGIS tests**, **3 browser workflow tests**, and the production frontend build. The PostGIS check confirms generated geometry, SRID, spatial length and GiST index creation.

The local machine has no Docker/PostGIS service, so that one integration test is skipped locally. Docker Compose execution and a full application-container build have not been verified; CI tested the backend against a real PostGIS service.

The running local API was also checked: 425 segments, 15,059.6 m of network, 2 OSM candidates, 0 reviewed coverage and 0 verified observations. All 1,243 accessibility samples remain unknown.

## Remaining uncertainties

Exact public entrance connection, current street accessibility, KMC ward attribution, actual bin locations/condition, independent survey validation and civic reporting remain field/data tasks. No fabricated observations are included.

## Known engineering limits

Single-pilot local deployment, shared role keys, declared survey completeness without GPS-track validation, no physical asset deduplication, local filesystem photo storage, no full migration framework or production operational hardening. The map bundle is large (~400 KB gzip main JS, plus worker); code-splitting is a future performance improvement. Dependency deprecation warnings exist for Shapely transform and the FastAPI/Starlette test client compatibility path.
