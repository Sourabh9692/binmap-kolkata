import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import type { GeoJSONSource } from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
maplibregl.setWorkerUrl(workerUrl);
import type { FeatureCollection } from "geojson";
import "maplibre-gl/dist/maplibre-gl.css";
export default function MapView({
  streets,
  bins,
  boundary,
  center,
  onSelect,
}: {
  streets: FeatureCollection;
  bins: FeatureCollection;
  boundary: FeatureCollection;
  center: [number, number];
  onSelect: (id: string) => void;
}) {
  const host = useRef<HTMLDivElement>(null),
    map = useRef<maplibregl.Map | null>(null),
    select = useRef(onSelect);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const marker = useRef<maplibregl.Marker | null>(null);
  select.current = onSelect;
  useEffect(() => {
    if (!host.current) return;
    let m: maplibregl.Map;
    try {
      m = new maplibregl.Map({
        container: host.current,
        center,
        zoom: 15.8,
        style: {
          version: 8,
          sources: {
            osm: {
              type: "raster",
              tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
              tileSize: 256,
              attribution:
                '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
            },
          },
          layers: [
            {
              id: "base",
              type: "raster",
              source: "osm",
              paint: { "raster-saturation": -0.7, "raster-opacity": 0.7 },
            },
          ],
        },
      });
    } catch {
      setError("Interactive maps require WebGL. Use the street list below.");
      return;
    }
    const resize = new ResizeObserver(() => m.resize());
    resize.observe(host.current);
    map.current = m;
    marker.current = new maplibregl.Marker({ color: "#173f35" })
      .setLngLat(center)
      .addTo(m);
    m.addControl(
      new maplibregl.NavigationControl({ showCompass: false }),
      "top-right",
    );
    m.on("error", () =>
      setError(
        "The map could not fully load. Saved streets are available in the list below.",
      ),
    );
    m.on("sourcedata", (e) => {
      if (e.sourceId === "streets" && e.isSourceLoaded) setReady(true);
    });
    m.on("load", () => {
      for (const [id, data] of Object.entries({ streets, bins, boundary }))
        m.addSource(id, { type: "geojson", data });
      m.addLayer({
        id: "boundary-fill",
        type: "fill",
        source: "boundary",
        paint: { "fill-color": "#9dc5a4", "fill-opacity": 0.15 },
      });
      m.addLayer({
        id: "streets-line",
        type: "line",
        source: "streets",
        paint: {
          "line-color": [
            "match",
            ["get", "status"],
            "inspected",
            "#2f805a",
            "partial",
            "#dc9b43",
            "needs_recheck",
            "#b36877",
            "#557b86",
          ],
          "line-width": 4,
          "line-opacity": 0.85,
        },
      });
      m.addLayer({
        id: "streets-hit",
        type: "line",
        source: "streets",
        paint: { "line-color": "#000", "line-opacity": 0, "line-width": 20 },
      });
      m.addLayer({
        id: "bin-points",
        type: "circle",
        source: "bins",
        paint: {
          "circle-radius": 7,
          "circle-color": [
            "match",
            ["get", "status"],
            "verified_usable",
            "#247954",
            "osm_unverified",
            "#e6ad57",
            "#a4737c",
          ],
          "circle-stroke-color": "white",
          "circle-stroke-width": 2,
        },
      });
      m.on("click", "streets-hit", (e) => {
        const id = e.features?.[0]?.properties?.id;
        if (id) select.current(id);
      });
      m.on(
        "mouseenter",
        "streets-hit",
        () => (m.getCanvas().style.cursor = "pointer"),
      );
      m.on(
        "mouseleave",
        "streets-hit",
        () => (m.getCanvas().style.cursor = ""),
      );
      m.on("click", "bin-points", (e) => {
        const p = e.features?.[0]?.properties;
        const el = document.createElement("div");
        el.textContent =
          p?.status === "osm_unverified"
            ? "OSM candidate · not field verified"
            : `${p?.condition} · ${p?.status}`;
        new maplibregl.Popup().setLngLat(e.lngLat).setDOMContent(el).addTo(m);
      });
    });
    return () => {
      resize.disconnect();
      m.remove();
      map.current = null;
    };
  }, []);
  useEffect(() => {
    const m = map.current;
    if (!m) return;
    const update = () => {
      for (const [id, data] of Object.entries({ streets, bins, boundary }))
        (m.getSource(id) as GeoJSONSource | undefined)?.setData(data);
    };
    if (m.isStyleLoaded()) update();
    else m.once("load", update);
    return () => {
      m.off("load", update);
    };
  }, [streets, bins, boundary]);
  useEffect(() => {
    map.current?.jumpTo({ center });
    marker.current?.setLngLat(center);
  }, [center[0], center[1]]);
  return (
    <div className="map-shell" data-ready={ready}>
      <div ref={host} className="map" aria-label="Pilot street map" />
      {error && <div className="map-error">{error}</div>}
      <div className="map-label">
        <span className="pulse" /> JADAVPUR PILOT{" "}
        <small>500 m walking catchment</small>
      </div>
      <div className="legend">
        <span>
          <i style={{ background: "#557b86" }} />
          Unsurveyed
        </span>
        <span>
          <i style={{ background: "#2f805a" }} />
          Inspected
        </span>
        <span>
          <i style={{ background: "#dc9b43" }} />
          Partial
        </span>
      </div>
    </div>
  );
}
