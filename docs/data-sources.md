# Source register

| Source | Purpose | Status / limits |
|---|---|---|
| User-provided [Google Maps landmark link](https://maps.app.goo.gl/fjJ3G3CQi7iCdz4h7) | Select Narkel Bagan Kali Temple pin at 22.4909012, 88.3677315 | User-selected landmark; entrance access not field verified. Do not use viewport coordinates. |
| [Temples of India listing](https://templesofindia.org/temple-view/narkel-bagan-kali-mandir-kolkata-west-bengal-697gno) | Initial location candidate | Superseded by user's pin; differs by roughly 70 m. |
| [OSM map API](https://api.openstreetmap.org/api/0.6/map?bbox=88.3585,22.483,88.3762,22.500) | Actual raw XML streets and infrastructure | Download succeeded 9 October 2026. Preserve `source.osm`, bbox and SHA-256. ODbL 1.0. |
| [OpenStreetMap copyright](https://www.openstreetmap.org/copyright) | Attribution / license | OSM contributors, Open Database License. |
| [Overpass public instances](https://wiki.openstreetmap.org/wiki/Overpass_API) | Preferred geometry extraction | Default and private.coffee endpoints failed during setup; XML fallback used. |
| [KMC municipal maps](https://www.kmcgov.in/KMCPortal/jsp/KMCMap.jsp) | Official administrative reference | Ward attribution unresolved. |
| [KMC ward-wise smart maps](https://www.kmcgov.in/KMCPortal/jsp/WardwiseSmartMap.jsp) | Administrative/drainage reference | Page available; no machine-readable ward geometry verified during implementation. |
| [OSM waste basket tag](https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dwaste_basket) | Pedestrian bin classification | Separate from waste disposal and recycling facilities. |
| [OSM tile policy](https://operations.osmfoundation.org/policies/tiles/) | Basemap use | No offline tile prefetch or bulk downloading. |
| Field surveys | Primary dated evidence | Not started. Software tests are not field evidence. |

The downloaded bbox is larger than the 500 m walking catchment. OSM candidate bins may lie outside the pilot; that is intentional for access analysis. Candidates are neither complete nor verified. XML relation features are excluded, and way features use approximate representative positions.

Source metadata is stored with each generated pilot. No municipal deployment counts or official bin inventories have been asserted without verification in this repository.
