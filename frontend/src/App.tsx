import { useEffect, useState, type FormEvent } from "react";
import type { FeatureCollection } from "geojson";
import {
  Map,
  ClipboardList,
  ShieldCheck,
  FileDown,
  ArrowUpRight,
  MapPin,
  Wifi,
  WifiOff,
  Trash2,
  Leaf,
  LocateFixed,
  UploadCloud,
  Check,
  KeyRound,
  ArrowRight,
  RefreshCw,
} from "lucide-react";
import MapView from "./MapView";
import { api, db, syncDrafts, type Draft } from "./store";

type Tab = "overview" | "survey" | "review" | "report";
type Pilot = {
  name: string;
  center: [number, number];
  anchor_status: string;
  ward_status: string;
  network_status: string;
  generated_at?: string;
  network_m?: number;
  source?: string;
};
type Summary = {
  network_m: number;
  inspected_m: number;
  coverage_percent: number;
  verified_usable_observations: number;
  osm_candidates: number;
  street_segments: number;
};
type ReviewItem = {
  target_type: string;
  id: string;
  payload: Record<string, any>;
};
const empty: FeatureCollection = { type: "FeatureCollection", features: [] };
const zero: Summary = {
  network_m: 0,
  inspected_m: 0,
  coverage_percent: 0,
  verified_usable_observations: 0,
  osm_candidates: 0,
  street_segments: 0,
};
const initialPilot: Pilot = {
  name: "Narkelbagan Kali Mandir",
  center: [88.3677315, 22.4909012],
  anchor_status: "unverified",
  ward_status: "unverified",
  network_status: "not_imported",
};
const labels = {
  overview: "Explore the pilot",
  survey: "Field notebook",
  review: "Evidence review",
  report: "Pilot report",
};
const date = (value?: string) =>
  value
    ? new Date(value).toLocaleString("en-IN", {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "Not yet recorded";

export default function App() {
  const [tab, setTab] = useState<Tab>("overview"),
    [pilot, setPilot] = useState(initialPilot),
    [summary, setSummary] = useState(zero);
  const [streets, setStreets] = useState<FeatureCollection>(empty),
    [bins, setBins] = useState<FeatureCollection>(empty),
    [boundary, setBoundary] = useState<FeatureCollection>(empty);
  const [selected, setSelected] = useState(""),
    [online, setOnline] = useState(navigator.onLine),
    [message, setMessage] = useState(""),
    [loading, setLoading] = useState(true);
  const [key, setKey] = useState(""),
    [showKey, setShowKey] = useState(false),
    [drafts, setDrafts] = useState<Draft[]>([]),
    [syncing, setSyncing] = useState(false);
  async function load() {
    try {
      const [p, s, st, b, bo] = await Promise.all(
        ["/pilot", "/summary", "/streets", "/bins", "/boundary"].map((path) =>
          api(path),
        ),
      );
      setPilot(p);
      setSummary(s);
      setStreets(st);
      setBins(b);
      setBoundary(bo);
    } catch (error) {
      setMessage("Could not refresh data. " + String(error));
    } finally {
      setLoading(false);
    }
  }
  async function refreshDrafts() {
    setDrafts(await db.drafts.orderBy("createdAt").toArray());
  }
  useEffect(() => {
    load();
    refreshDrafts();
    const update = () => setOnline(navigator.onLine);
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);
  async function sync() {
    if (!key) {
      setShowKey(true);
      setMessage("Enter the survey access key to sync your drafts.");
      return;
    }
    setSyncing(true);
    try {
      const n = await syncDrafts(key);
      setMessage(`${n} draft${n === 1 ? "" : "s"} synced for review.`);
      await load();
    } catch (e) {
      setMessage(String(e));
    } finally {
      setSyncing(false);
      refreshDrafts();
    }
  }
  function select(id: string) {
    setSelected(id);
    setTab("survey");
  }
  const provisional = pilot.anchor_status !== "manually_verified";
  return (
    <div className="app">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="BinMap home">
          <span className="brand-icon">
            <Trash2 size={23} />
          </span>
          <span>
            BinMap<small>K O L K A T A</small>
          </span>
        </a>
        <div className="workspace-label">
          CIVIC FIELD LAB <span>01</span>
        </div>
        <nav>
          {(
            [
              { id: "overview", icon: Map },
              { id: "survey", icon: ClipboardList },
              { id: "review", icon: ShieldCheck },
              { id: "report", icon: FileDown },
            ] as const
          ).map(({ id, icon: Icon }) => (
            <button
              key={id}
              className={tab === id ? "nav-item active" : "nav-item"}
              onClick={() => setTab(id)}
            >
              <Icon size={19} />
              {labels[id]}
              {tab === id && <span className="nav-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <Leaf size={25} />
          <h3>
            Better streets start
            <br />
            with better evidence.
          </h3>
          <p>
            One neighborhood.
            <br />
            Every observation counts.
          </p>
          <span>COMMUNITY PILOT ↗</span>
        </div>
        <div className="sidebar-bottom">
          <span className="avatar">SG</span>
          <div>
            Pilot workspace<small>Local research · v0.1</small>
          </div>
          <button
            className="icon-button"
            aria-label="Access settings"
            onClick={() => setShowKey(!showKey)}
          >
            <KeyRound size={18} />
          </button>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <span>/</span> <b>Jadavpur pilot</b>
          </div>
          <div className="top-actions">
            <span className={"connection " + (!online ? "offline" : "")}>
              {online ? <Wifi size={14} /> : <WifiOff size={14} />}{" "}
              {online ? "Online" : "Offline · saved data"}
            </span>
            <button
              className="button small subtle"
              onClick={() => setShowKey(!showKey)}
            >
              <KeyRound size={14} /> Access
            </button>
          </div>
        </header>
        <div className="content">
          {showKey && (
            <section className="access-panel">
              <div>
                <strong>Workspace access</strong>
                <p>
                  Use the local survey key for uploads, or the review key for
                  moderation. Keys stay in memory for this visit.
                </p>
              </div>
              <input
                aria-label="Access key"
                type="password"
                value={key}
                onChange={(e) => setKey(e.target.value)}
                placeholder="Paste your access key"
                autoComplete="off"
              />
              <button className="button" onClick={() => setShowKey(false)}>
                Done
              </button>
            </section>
          )}
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                <span /> KOLKATA, WEST BENGAL
              </div>
              <h1>
                {tab === "overview" ? "Every street counts." : labels[tab]}
              </h1>
              <p>
                {tab === "overview"
                  ? "Mapping public bin access, one verified observation at a time."
                  : tab === "survey"
                    ? "Observe carefully. Save locally. Sync when you’re ready."
                    : tab === "review"
                      ? "Check the evidence before it becomes a public finding."
                      : "A transparent snapshot of what we know—and what we don’t."}
              </p>
            </div>
            {tab === "overview" ? (
              <button
                className="button primary"
                onClick={() => setTab("survey")}
              >
                Start a survey <ArrowUpRight size={17} />
              </button>
            ) : (
              <button
                className="button subtle"
                onClick={() => setTab("overview")}
              >
                <Map size={16} /> Back to map
              </button>
            )}
          </div>
          {message && (
            <div className="notice" role="status">
              <span>{message}</span>
              <button
                aria-label="Dismiss message"
                onClick={() => setMessage("")}
              >
                ×
              </button>
            </div>
          )}
          {provisional && (
            <div className="verification-banner">
              <span className="status-dot" />
              <strong>Provisional pilot</strong>
              <span>
                Temple entrance and KMC ward await confirmation. Street geometry
                is{" "}
                {pilot.network_status === "downloaded"
                  ? "from OpenStreetMap"
                  : "not yet imported"}
                .
              </span>
            </div>
          )}
          {tab === "overview" && (
            <>
              <div className="stats">
                <Stat
                  label="PILOT WALKING NETWORK"
                  value={loading ? "…" : (summary.network_m / 1000).toFixed(2)}
                  unit="km"
                  detail={`${summary.street_segments} survey segments`}
                />
                <Stat
                  label="REVIEWED SURVEY COVERAGE"
                  value={`${summary.coverage_percent}%`}
                  detail={`${(summary.inspected_m / 1000).toFixed(2)} km adequately inspected`}
                  progress={summary.coverage_percent}
                />
                <Stat
                  label="VERIFIED USABLE OBSERVATIONS"
                  value={String(summary.verified_usable_observations)}
                  detail="Reviewed field evidence"
                />
                <Stat
                  label="OSM BIN CANDIDATES"
                  value={String(summary.osm_candidates)}
                  detail="Awaiting field verification"
                />
              </div>
              <div className="map-grid">
                <section className="card map-card">
                  <div className="section-title">
                    <div>
                      <h2>The neighborhood, on the ground</h2>
                      <p>Select a street to begin an inspection.</p>
                    </div>
                    <span className="pill">OSM SNAPSHOT</span>
                  </div>
                  <MapView
                    streets={streets}
                    bins={bins}
                    boundary={boundary}
                    center={pilot.center}
                    onSelect={select}
                  />
                </section>
                <aside className="pilot-card">
                  <span className="eyebrow">OUR FIRST NEIGHBORHOOD</span>
                  <span className="location-symbol">
                    <MapPin size={25} />
                  </span>
                  <h2>
                    Narkelbagan
                    <br />
                    Kali Mandir
                  </h2>
                  <p>
                    Bade Raipur Road, Jadavpur
                    <br />
                    Kolkata 700032
                  </p>
                  <div className="pilot-divider" />
                  <dl>
                    <div>
                      <dt>Study extent</dt>
                      <dd>500 m walking distance</dd>
                    </div>
                    <div>
                      <dt>Anchor verification</dt>
                      <dd>
                        {pilot.anchor_status === "user_confirmed_map_pin"
                          ? "Map pin confirmed"
                          : provisional
                            ? "Pending"
                            : "Confirmed"}
                      </dd>
                    </div>
                    <div>
                      <dt>KMC ward</dt>
                      <dd>
                        {pilot.ward_status === "unverified"
                          ? "Not confirmed"
                          : pilot.ward_status}
                      </dd>
                    </div>
                    <div>
                      <dt>Network snapshot</dt>
                      <dd>{date(pilot.generated_at)}</dd>
                    </div>
                  </dl>
                  <button
                    onClick={() => setTab("report")}
                    className="text-button"
                  >
                    View methodology <ArrowRight size={16} />
                  </button>
                </aside>
              </div>
              <div className="bottom-grid">
                <section className="card">
                  <div className="section-title">
                    <div>
                      <h2>A map is a starting point.</h2>
                      <p>
                        Missing from a map doesn’t mean missing from a street.
                      </p>
                    </div>
                    <ShieldCheck size={23} />
                  </div>
                  <div className="evidence-steps">
                    <div>
                      <span>01</span>
                      <strong>Observe</strong>
                      <p>Walk both sides and record visibility.</p>
                    </div>
                    <div>
                      <span>02</span>
                      <strong>Verify</strong>
                      <p>Review photos, position, and condition.</p>
                    </div>
                    <div>
                      <span>03</span>
                      <strong>Understand</strong>
                      <p>Measure access using walkable routes.</p>
                    </div>
                  </div>
                </section>
                <section className="card next-step">
                  <span className="eyebrow">NEXT IN THE FIELD</span>
                  <h2>
                    Your first survey
                    <br /> starts here.
                  </h2>
                  <p>
                    No field results have been assumed. Bring the neighborhood
                    into focus.
                  </p>
                  <button
                    className="text-button"
                    onClick={() => setTab("survey")}
                  >
                    Open field notebook <ArrowUpRight size={18} />
                  </button>
                </section>
              </div>
              <details className="card street-list">
                <summary>
                  Browse all {streets.features.length} survey segments
                </summary>
                <div className="street-rows">
                  {streets.features.map((f) => (
                    <button
                      key={String(f.id)}
                      onClick={() => select(String(f.properties?.id))}
                    >
                      <span>
                        {String(f.properties?.name || "Unnamed lane")}
                      </span>
                      <code>{String(f.properties?.id).slice(0, 8)}</code>
                      <span>{Math.round(f.properties?.length_m || 0)} m</span>
                      <span>{String(f.properties?.status)}</span>
                      <ArrowRight size={16} />
                    </button>
                  ))}
                </div>
              </details>
            </>
          )}
          {tab === "survey" && (
            <div className="form-grid">
              <Survey
                streets={streets}
                selected={selected}
                setSelected={setSelected}
                onSaved={() => {
                  refreshDrafts();
                  setMessage(
                    "Draft saved on this device. Sync it when you have a connection.",
                  );
                }}
              />
              <aside className="card draft-panel">
                <div className="section-title">
                  <h2>On this device</h2>
                  <span className="count">{drafts.length}</span>
                </div>
                <p>
                  Drafts include private evidence. They are removed from this
                  device after a successful upload.
                </p>
                <button
                  className="button primary full"
                  onClick={sync}
                  disabled={syncing || !online || !drafts.length}
                >
                  <UploadCloud size={17} />
                  {syncing ? "Syncing…" : "Sync for review"}
                </button>
                {drafts.length === 0 && (
                  <div className="empty-state">
                    <Check size={26} />
                    <strong>Notebook is clear</strong>
                    <p>Saved drafts will appear here.</p>
                  </div>
                )}
                {drafts.map((d) => (
                  <div className="draft" key={d.id}>
                    <strong>
                      {d.kind === "inspection"
                        ? "Street inspection"
                        : "Bin observation"}
                    </strong>
                    <small>{date(d.createdAt)}</small>
                    {d.error && <p className="error">{d.error}</p>}
                    <button
                      className="text-button danger"
                      onClick={async () => {
                        if (
                          window.confirm(
                            "Delete this unsynced draft and its local photo?",
                          )
                        ) {
                          await db.drafts.delete(d.id);
                          refreshDrafts();
                        }
                      }}
                    >
                      Delete draft
                    </button>
                  </div>
                ))}
                <div className="soft-note">
                  Offline mode saves forms and loaded street data. Basemap tiles
                  need a connection. Keep this device’s browser data until
                  drafts are synced.
                </div>
              </aside>
            </div>
          )}
          {tab === "review" && (
            <ReviewPanel
              accessKey={key}
              onMessage={setMessage}
              onReviewed={load}
            />
          )}
          {tab === "report" && (
            <section className="card report">
              <div className="section-title">
                <div>
                  <span className="eyebrow">
                    BINMAP KOLKATA · PILOT EVIDENCE
                  </span>
                  <h2>Narkelbagan field report</h2>
                </div>
                <button
                  className="button subtle"
                  onClick={() => window.print()}
                >
                  Print / Save PDF
                </button>
              </div>
              <div className="report-stats">
                <Stat
                  label="NETWORK LENGTH"
                  value={(summary.network_m / 1000).toFixed(2)}
                  unit="km"
                  detail="OSM-derived streets"
                />
                <Stat
                  label="REVIEWED COVERAGE"
                  value={`${summary.coverage_percent}%`}
                  detail="Recent, adequately inspected streets"
                />
                <Stat
                  label="USABLE OBSERVATIONS"
                  value={String(summary.verified_usable_observations)}
                  detail="Not a deduplicated asset count"
                />
              </div>
              <h3>What this report establishes</h3>
              <p>
                The pilot contains {summary.street_segments} street segments and{" "}
                {summary.osm_candidates} unverified OSM bin candidates.{" "}
                {summary.inspected_m === 0
                  ? "There are no adequately inspected, reviewed streets yet. No conclusion about missing bins can be drawn."
                  : "Reviewed coverage reflects dated street inspections. Inspection results alone do not establish walking accessibility."}
              </p>
              <h3>Method and limitations</h3>
              <ul>
                <li>
                  The study follows 500 metres of pedestrian-network distance.
                  Its buffered polygon is for display, not an administrative
                  boundary.
                </li>
                <li>
                  Anchor status: {pilot.anchor_status}. KMC ward status:{" "}
                  {pilot.ward_status}.
                </li>
                <li>
                  Negative findings require both sides inspected, clear
                  visibility, and at least 95% declared coverage. This version
                  does not validate a recorded GPS track.
                </li>
                <li>
                  Photos are private and review-only. GPS accuracy above 15 m
                  blocks approval. Evidence older than 30 days needs rechecking.
                </li>
                <li>
                  Imported OSM records have not been field verified. No online
                  inventory can establish that unmapped bins are absent.
                </li>
                <li>
                  Walking-distance analysis is generated separately from the
                  validated graph and approved observations. A 150 m access
                  threshold is experimental.
                </li>
              </ul>
              <h3>Data provenance</h3>
              <p>
                Street and mapped infrastructure data © OpenStreetMap
                contributors, ODbL 1.0. Snapshot: {date(pilot.generated_at)}.
                The landmark coordinate follows the user-selected Google Maps
                pin; entrance access still requires field verification.
              </p>
              <div className="report-actions">
                <a className="button primary" href="/api/export" download>
                  <FileDown size={17} /> Export public GeoJSON
                </a>
                <a
                  className="button subtle"
                  href="https://www.kmcgov.in/KMCPortal/jsp/KMCMap.jsp"
                  target="_blank"
                  rel="noreferrer"
                >
                  KMC maps <ArrowUpRight size={16} />
                </a>
              </div>
              <p className="fine-print">
                Export excludes surveyor identifiers, notes, and photographs.
                Review again before sharing externally.
              </p>
            </section>
          )}
          <footer>
            <span>
              <Leaf size={13} /> Built for streets. Grounded in evidence.
            </span>
            <span>BinMap Kolkata · Pilot 01</span>
          </footer>
        </div>
      </main>
    </div>
  );
}
function Stat({
  label,
  value,
  unit,
  detail,
  progress,
}: {
  label: string;
  value: string;
  unit?: string;
  detail: string;
  progress?: number;
}) {
  return (
    <div className="stat">
      <span className="stat-label">{label}</span>
      <div className="stat-value">
        {value}
        <small>{unit}</small>
      </div>
      {progress !== undefined && (
        <div className="progress">
          <span style={{ width: `${progress}%` }} />
        </div>
      )}
      <p>{detail}</p>
    </div>
  );
}

function Survey({
  streets,
  selected,
  setSelected,
  onSaved,
}: {
  streets: FeatureCollection;
  selected: string;
  setSelected: (s: string) => void;
  onSaved: () => void;
}) {
  const [kind, setKind] = useState<"inspection" | "observation">("inspection"),
    [gps, setGps] = useState<{
      latitude: number;
      longitude: number;
      accuracy_m: number;
    } | null>(null),
    [gpsError, setGpsError] = useState(""),
    [saving, setSaving] = useState(false),
    [error, setError] = useState("");
  async function locate() {
    setGpsError("Locating…");
    if (!navigator.geolocation) {
      setGpsError("Location is unavailable in this browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (p) => {
        setGps({
          latitude: p.coords.latitude,
          longitude: p.coords.longitude,
          accuracy_m: p.coords.accuracy,
        });
        setGpsError("");
      },
      (e) => setGpsError(e.message),
      { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 },
    );
  }
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSaving(true);
    const form = event.currentTarget;
    const data = new FormData(form);
    try {
      if (!selected)
        throw new Error("Select an imported street segment first.");
      if (kind === "observation" && !gps)
        throw new Error("Capture your GPS location before saving a bin.");
      const id = crypto.randomUUID(),
        sessionId = crypto.randomUUID(),
        time = new Date().toISOString();
      const session = {
        id: sessionId,
        surveyor: String(data.get("surveyor")),
        started_at: time,
        consent: true,
      };
      const common = {
        id,
        session_id: sessionId,
        segment_id: selected,
        observed_at: time,
        notes: String(data.get("notes") || ""),
      };
      let draft: Draft;
      if (kind === "inspection") {
        draft = {
          id,
          kind,
          session,
          createdAt: time,
          body: {
            ...common,
            sides: data.get("sides"),
            visibility: data.get("visibility"),
            coverage: Number(data.get("coverage")) / 100,
            result: data.get("result"),
          },
        };
      } else {
        const photo = data.get("photo") as File;
        if (!photo?.size) throw new Error("A photo is required.");
        if (photo.size > 8 * 1024 * 1024)
          throw new Error("Choose a photo smaller than 8 MB.");
        const evidenceId = crypto.randomUUID();
        draft = {
          id,
          kind,
          session,
          createdAt: time,
          photo,
          evidenceId,
          body: {
            ...common,
            ...gps,
            category: data.get("category"),
            condition: data.get("condition"),
            public_access: data.get("public_access") === "on",
            evidence_id: evidenceId,
          },
        };
      }
      await db.drafts.add(draft);
      form.reset();
      setGps(null);
      onSaved();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }
  return (
    <section className="card survey-card">
      <div className="section-title">
        <div>
          <h2>Record what you see</h2>
          <p>All submissions start as unverified evidence.</p>
        </div>
        <ClipboardList size={24} />
      </div>
      <div className="segmented">
        <button
          className={kind === "inspection" ? "chosen" : ""}
          onClick={() => setKind("inspection")}
        >
          Inspect a street
        </button>
        <button
          className={kind === "observation" ? "chosen" : ""}
          onClick={() => setKind("observation")}
        >
          Record a bin
        </button>
      </div>
      <form onSubmit={save}>
        <label>
          Street segment
          <select
            required
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            <option value="">Choose a street segment</option>
            {streets.features.map((f) => (
              <option key={String(f.id)} value={String(f.properties?.id)}>
                {String(f.properties?.name || "Unnamed lane")} ·{" "}
                {Math.round(f.properties?.length_m || 0)} m ·{" "}
                {String(f.properties?.id).slice(0, 6)}
              </option>
            ))}
          </select>
        </label>
        {!streets.features.length && (
          <p className="soft-note">
            Import the real pedestrian network before recording survey evidence.
          </p>
        )}
        <label>
          Surveyor alias
          <input
            required
            name="surveyor"
            minLength={2}
            maxLength={60}
            placeholder="Use a pseudonym, e.g. surveyor-01"
          />
        </label>
        {kind === "inspection" ? (
          <>
            <div className="field-pair">
              <label>
                Sides inspected
                <select name="sides">
                  <option value="both">Both sides</option>
                  <option value="left">Left only</option>
                  <option value="right">Right only</option>
                  <option value="neither">Neither</option>
                </select>
              </label>
              <label>
                Visibility
                <select name="visibility">
                  <option value="clear">Clear throughout</option>
                  <option value="partial">Partly obstructed</option>
                  <option value="obstructed">Obstructed</option>
                </select>
              </label>
            </div>
            <div className="field-pair">
              <label>
                Coverage (%)
                <input
                  name="coverage"
                  type="number"
                  min="0"
                  max="100"
                  required
                  defaultValue="100"
                />
              </label>
              <label>
                Finding
                <select name="result">
                  <option value="no_bin_observed">No bin observed</option>
                  <option value="bins_observed">
                    One or more bins observed
                  </option>
                  <option value="unable_to_inspect">Unable to inspect</option>
                </select>
              </label>
            </div>
            <p className="soft-note">
              Only choose “No bin observed” after walking the segment. Partial
              visibility remains incomplete evidence.
            </p>
          </>
        ) : (
          <>
            <div className="gps-box">
              <div>
                <strong>
                  {gps ? "Location captured" : "Capture field location"}
                </strong>
                <small>
                  {gps
                    ? `${gps.latitude.toFixed(6)}, ${gps.longitude.toFixed(6)} · ±${Math.round(gps.accuracy_m)} m`
                    : "Location is collected only when you press this button."}
                </small>
              </div>
              <button type="button" className="button subtle" onClick={locate}>
                <LocateFixed size={16} /> Locate me
              </button>
            </div>
            {gpsError && <p role="status">{gpsError}</p>}
            {gps && gps.accuracy_m > 15 && (
              <p className="error">
                GPS uncertainty is above 15 m. Try again outside before review.
              </p>
            )}
            <div className="field-pair">
              <label>
                Bin category
                <select name="category">
                  <option value="public_litter_bin">Public litter bin</option>
                  <option value="community_container">
                    Community container
                  </option>
                  <option value="recycling">Recycling facility</option>
                  <option value="private_bin">Private bin</option>
                </select>
              </label>
              <label>
                Condition
                <select name="condition">
                  <option value="usable">Usable</option>
                  <option value="overflowing">Overflowing</option>
                  <option value="damaged">Damaged</option>
                  <option value="blocked">Blocked</option>
                  <option value="missing">
                    Previously present, now missing
                  </option>
                </select>
              </label>
            </div>
            <label className="checkbox">
              <input name="public_access" type="checkbox" defaultChecked />{" "}
              Accessible from a public walking route
            </label>
            <label>
              Photograph
              <input
                name="photo"
                type="file"
                accept="image/*"
                capture="environment"
                required
              />
            </label>
            <p className="fine-print">
              Avoid faces and vehicle plates. Photos remain private; image
              metadata is removed on upload.
            </p>
          </>
        )}
        <label>
          Field notes
          <textarea
            name="notes"
            maxLength={2000}
            placeholder="Access restrictions, landmarks, visibility gaps…"
            rows={3}
          />
        </label>
        <label className="checkbox">
          <input type="checkbox" required /> I consent to storing this
          observation and confirm it reflects my actual inspection.
        </label>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <button
          disabled={saving || !streets.features.length}
          className="button primary full"
          type="submit"
        >
          {saving ? "Saving…" : "Save draft on this device"} <Check size={17} />
        </button>
      </form>
    </section>
  );
}
function ReviewPanel({
  accessKey,
  onMessage,
  onReviewed,
}: {
  accessKey: string;
  onMessage: (s: string) => void;
  onReviewed: () => void;
}) {
  const [items, setItems] = useState<ReviewItem[]>([]),
    [loaded, setLoaded] = useState(false),
    [busy, setBusy] = useState(false);
  async function load() {
    setBusy(true);
    try {
      setItems(
        await api("/review-queue", {
          headers: { Authorization: "Bearer " + accessKey },
        }),
      );
      setLoaded(true);
    } catch (e) {
      onMessage(String(e));
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    setItems([]);
    setLoaded(false);
  }, [accessKey]);
  async function review(item: ReviewItem, decision: string, reason: string) {
    if (reason.trim().length < 5) {
      onMessage("Add a review reason of at least five characters.");
      return;
    }
    setBusy(true);
    try {
      await api("/reviews", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer " + accessKey,
        },
        body: JSON.stringify({
          target_type: item.target_type,
          target_id: item.id,
          decision,
          reason,
        }),
      });
      setItems((old) => old.filter((x) => x.id !== item.id));
      onMessage("Review recorded in the audit log.");
      onReviewed();
    } catch (e) {
      onMessage(String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="card">
      <div className="section-title">
        <div>
          <h2>Review queue</h2>
          <p>A separate reviewer access key is required.</p>
        </div>
        <button className="button primary" disabled={busy} onClick={load}>
          <RefreshCw size={16} /> Load evidence
        </button>
      </div>
      {!loaded ? (
        <div className="empty-state">
          <ShieldCheck size={34} />
          <h3>Evidence earns its place on the map.</h3>
          <p>Enter your review key in Access, then load the queue.</p>
        </div>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <Check size={30} />
          <h3>No pending evidence</h3>
          <p>Synced field submissions will appear here.</p>
        </div>
      ) : (
        items.map((item) => (
          <ReviewCard
            key={item.id}
            item={item}
            accessKey={accessKey}
            busy={busy}
            review={review}
          />
        ))
      )}
    </section>
  );
}
function ReviewCard({
  item,
  accessKey,
  busy,
  review,
}: {
  item: ReviewItem;
  accessKey: string;
  busy: boolean;
  review: (i: ReviewItem, d: string, r: string) => void;
}) {
  const [reason, setReason] = useState(""),
    [photo, setPhoto] = useState(""),
    [error, setError] = useState("");
  useEffect(() => {
    let active = true,
      url = "";
    if (item.payload.evidence_id)
      fetch("/api/evidence/" + item.payload.evidence_id, {
        headers: { Authorization: "Bearer " + accessKey },
      })
        .then((r) => {
          if (!r.ok) throw new Error("Photo could not be loaded");
          return r.blob();
        })
        .then((b) => {
          url = URL.createObjectURL(b);
          if (active) setPhoto(url);
          else URL.revokeObjectURL(url);
        })
        .catch((e) => {
          if (active) setError(String(e));
        });
    return () => {
      active = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [item.id, accessKey]);
  return (
    <article className="review-card">
      <h3>
        {item.target_type === "inspection"
          ? "Street inspection"
          : "Bin observation"}{" "}
        <small>{date(item.payload.observed_at)}</small>
      </h3>
      <div className="review-data">
        {Object.entries(item.payload)
          .filter(([k]) => !["id", "session_id", "evidence_id"].includes(k))
          .map(([k, v]) => (
            <div key={k}>
              <span>{k.replaceAll("_", " ")}</span>
              <strong>{String(v)}</strong>
            </div>
          ))}
      </div>
      {photo && (
        <img
          src={photo}
          className="evidence-photo"
          alt="Submitted bin evidence"
        />
      )}
      {error && <p className="error">{error}</p>}
      <label>
        Review reason
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Explain how you assessed location, photo, visibility, and condition."
        />
      </label>
      <div className="report-actions">
        <button
          className="button primary"
          disabled={busy || (item.target_type === "observation" && !photo)}
          onClick={() => review(item, "approved", reason)}
        >
          Approve evidence
        </button>
        <button
          className="button subtle"
          disabled={busy}
          onClick={() => review(item, "rejected", reason)}
        >
          Reject / request resurvey
        </button>
      </div>
    </article>
  );
}
