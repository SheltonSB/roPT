import { useEffect, useMemo, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";
const WS_URL = API_BASE.replace(/^http/, "ws").replace(/\/$/, "") + "/ws";

const VIEW = { width: 960, height: 560, padding: 32 };
const FRAME_WIDTH = Number(import.meta.env.VITE_FRAME_WIDTH || 0);
const FRAME_HEIGHT = Number(import.meta.env.VITE_FRAME_HEIGHT || 0);

function formatTime(ts) {
  if (!ts) return "n/a";
  const d = new Date(ts);
  return d.toLocaleTimeString();
}

function App() {
  const [zones, setZones] = useState([]);
  const [snapshot, setSnapshot] = useState(null);
  const [connection, setConnection] = useState("connecting");
  const [lastUpdate, setLastUpdate] = useState(null);
  const [error, setError] = useState(null);
  const [flashZones, setFlashZones] = useState({});
  const [ghostPaths, setGhostPaths] = useState([]);
  const [nodeIndex, setNodeIndex] = useState({});
  const [lockAspect, setLockAspect] = useState(true);
  const seenEventsRef = useRef(new Set());
  const flashTimersRef = useRef({});

  useEffect(() => {
    fetch(`${API_BASE}/zones`)
      .then((r) => r.json())
      .then((data) => setZones(data.zones || []))
      .catch((err) => setError(err.message));
  }, []);

  const fetchState = () => {
    fetch(`${API_BASE}/state`)
      .then((r) => r.json())
      .then((data) => {
        setSnapshot(data);
        setLastUpdate(Date.now());
      })
      .catch((err) => setError(err.message));
  };

  useEffect(() => {
    fetchState();
  }, []);

  useEffect(() => {
    fetch(`${API_BASE}/planning/graph`)
      .then((r) => r.json())
      .then((data) => {
        const nodes = data.graph?.nodes || [];
        const map = {};
        nodes.forEach((n) => {
          if (n.id) {
            map[n.id] = { x: n.x, y: n.y };
          }
        });
        setNodeIndex(map);
      })
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    setConnection("connecting");

    ws.onopen = () => setConnection("live");
    ws.onerror = () => setConnection("error");
    ws.onclose = () => setConnection("offline");
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "snapshot") {
          setSnapshot(msg.data);
          setLastUpdate(Date.now());
          handleFlashEvents(msg.data?.recent_events || []);
        } else if (msg.type === "route_update") {
          setGhostPaths(buildGhostPaths(msg.data));
        }
      } catch (err) {
        setError(err.message);
      }
    };

    return () => ws.close();
  }, []);

  useEffect(() => {
    if (connection === "live") return undefined;
    const id = setInterval(fetchState, 2000);
    return () => clearInterval(id);
  }, [connection]);

  const handleFlashEvents = (events) => {
    if (!events?.length) return;
    const seen = seenEventsRef.current;
    events.forEach((evt) => {
      const type = String(evt.event_type || "");
      if (!type.includes("ENTER")) return;
      const key = `${evt._id || evt.ts_ms}-${evt.actor_id}-${evt.zone_id}-${evt.event_type}`;
      if (seen.has(key)) return;
      seen.add(key);
      if (seen.size > 2000) {
        seen.clear();
      }
      if (evt.zone_id) {
        triggerZoneFlash(evt.zone_id);
      }
    });
  };

  const triggerZoneFlash = (zoneId) => {
    setFlashZones((prev) => ({ ...prev, [zoneId]: true }));
    if (flashTimersRef.current[zoneId]) {
      clearTimeout(flashTimersRef.current[zoneId]);
    }
    flashTimersRef.current[zoneId] = setTimeout(() => {
      setFlashZones((prev) => {
        const next = { ...prev };
        delete next[zoneId];
        return next;
      });
    }, 1200);
  };

  const buildGhostPaths = (payload) => {
    if (!payload) return [];
    const candidates = payload.candidates || [];
    const optimal = payload.optimal_path || [];
    const paths = candidates.map((path, idx) => ({
      id: `cand-${idx}`,
      nodes: path,
      best: false
    }));
    if (optimal.length) {
      paths.unshift({ id: "optimal", nodes: optimal, best: true });
    }
    return paths;
  };

  const bounds = useMemo(() => {
    if (FRAME_WIDTH > 0 && FRAME_HEIGHT > 0) {
      return { minX: 0, minY: 0, maxX: FRAME_WIDTH, maxY: FRAME_HEIGHT };
    }
    if (!zones.length) {
      return { minX: 0, minY: 0, maxX: 1, maxY: 1 };
    }
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    zones.forEach((z) => {
      z.polygon.forEach(([x, y]) => {
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
      });
    });
    return { minX, minY, maxX, maxY };
  }, [zones]);

  const transform = useMemo(() => {
    const { minX, minY, maxX, maxY } = bounds;
    const dx = maxX - minX || 1;
    const dy = maxY - minY || 1;
    const rawScaleX = (VIEW.width - VIEW.padding * 2) / dx;
    const rawScaleY = (VIEW.height - VIEW.padding * 2) / dy;
    if (lockAspect) {
      const scale = Math.min(rawScaleX, rawScaleY);
      const extraX = (VIEW.width - VIEW.padding * 2 - dx * scale) / 2;
      const extraY = (VIEW.height - VIEW.padding * 2 - dy * scale) / 2;
      return {
        minX,
        minY,
        scaleX: scale,
        scaleY: scale,
        offsetX: VIEW.padding + extraX,
        offsetY: VIEW.padding + extraY
      };
    }
    return {
      minX,
      minY,
      scaleX: rawScaleX,
      scaleY: rawScaleY,
      offsetX: VIEW.padding,
      offsetY: VIEW.padding
    };
  }, [bounds, lockAspect]);

  const mapPointToView = (p) => {
    const px = transform.offsetX + (p.x - transform.minX) * transform.scaleX;
    const py = transform.offsetY + (p.y - transform.minY) * transform.scaleY;
    return `${px.toFixed(1)},${py.toFixed(1)}`;
  };

  const mappedZones = useMemo(() => {
    const mapPoint = (p) => {
      const px = transform.offsetX + (p.x - transform.minX) * transform.scaleX;
      const py = transform.offsetY + (p.y - transform.minY) * transform.scaleY;
      return `${px.toFixed(1)},${py.toFixed(1)}`;
    };
    return zones.map((z) => {
      const points = z.polygon
        .map(([x, y]) => {
          return mapPoint({ x, y });
        })
        .join(" ");
      const center = z.polygon.reduce(
        (acc, [x, y]) => {
          acc.x += x;
          acc.y += y;
          return acc;
        },
        { x: 0, y: 0 }
      );
      const cx = center.x / z.polygon.length;
      const cy = center.y / z.polygon.length;
      const [mx, my] = mapPoint({ x: cx, y: cy }).split(",");
      return { ...z, points, center: { x: Number(mx), y: Number(my) } };
    });
  }, [zones, transform]);

  const actors = useMemo(() => {
    if (!snapshot?.actors) return [];
    return Object.entries(snapshot.actors).map(([actorId, actor]) => {
      const activeZones = Object.entries(actor.zones || {})
        .filter(([, inside]) => inside)
        .map(([zoneId]) => zoneId);
      return { actorId, ...actor, activeZones };
    });
  }, [snapshot]);

  const recentEvents = snapshot?.recent_events || [];
  const blockedZones = snapshot?.blocked_zones || [];

  const pathCost = (nodes) => {
    let cost = 0;
    for (let i = 1; i < nodes.length; i += 1) {
      const a = nodeIndex[nodes[i - 1]];
      const b = nodeIndex[nodes[i]];
      if (!a || !b) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      cost += Math.hypot(dx, dy);
    }
    return cost;
  };

  return (
    <div className="app">
      <header className="hero">
        <div>
          <p className="eyebrow">roPT control</p>
          <h1>Safety routing live view</h1>
          <p className="subtitle">
            Streaming zone occupancy and event flow from edge to backend in real time.
          </p>
        </div>
        <div className="status-card">
          <div>
            <p className="label">Connection</p>
            <p className={`badge badge-${connection}`}>{connection}</p>
          </div>
          <div>
            <p className="label">Last update</p>
            <p className="value">{formatTime(lastUpdate)}</p>
          </div>
          <div>
            <p className="label">Active actors</p>
            <p className="value">{actors.length}</p>
          </div>
          <label className="toggle">
            <input
              type="checkbox"
              checked={lockAspect}
              onChange={() => setLockAspect((prev) => !prev)}
            />
            <span>Lock aspect ratio</span>
          </label>
        </div>
      </header>

      <main className="grid">
        <section className="panel map-panel">
          <div className="panel-head">
            <h2>Zone map</h2>
            <p>{zones.length ? `${zones.length} zones loaded` : "No zones yet"}</p>
          </div>
          <div className="map">
            <svg
              viewBox={`0 0 ${VIEW.width} ${VIEW.height}`}
              role="img"
              aria-label="Zone layout"
            >
              <defs>
                <linearGradient id="zoneFill" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stopColor="#F8C777" stopOpacity="0.15" />
                  <stop offset="100%" stopColor="#F08A5D" stopOpacity="0.22" />
                </linearGradient>
              </defs>
              {ghostPaths.map((path) => (
                <polyline
                  key={path.id}
                  className={`ghost-path${path.best ? " best" : ""}`}
                  points={path.nodes
                    .map((nodeId) => nodeIndex[nodeId])
                    .filter(Boolean)
                    .map((p) => mapPointToView(p))
                    .join(" ")}
                >
                  <title>
                    {`Cost: ${pathCost(path.nodes).toFixed(1)} | Risk: ${
                      blockedZones.length ? "High" : "Low"
                    }`}
                  </title>
                </polyline>
              ))}
              {mappedZones.map((zone) => (
                <g
                  key={zone.zone_id}
                  className={`zone${flashZones[zone.zone_id] ? " flash" : ""}${
                    blockedZones.includes(zone.zone_id) ? " danger" : ""
                  }`}
                >
                  <polygon points={zone.points} />
                  <text x={zone.center.x} y={zone.center.y} textAnchor="middle">
                    {zone.zone_id}
                  </text>
                </g>
              ))}
              {actors.flatMap((actor) =>
                actor.activeZones.map((zoneId) => {
                  const zone = mappedZones.find((z) => z.zone_id === zoneId);
                  if (!zone) return null;
                  return (
                    <g key={`${actor.actorId}-${zoneId}`} className="actor-dot">
                      <circle cx={zone.center.x} cy={zone.center.y} r="9" />
                      <text x={zone.center.x} y={zone.center.y - 14} textAnchor="middle">
                        {actor.actorId}
                      </text>
                    </g>
                  );
                })
              )}
            </svg>
          </div>
        </section>

        <section className="panel side-panel">
          <div className="panel-block">
            <h3>Actors</h3>
            {actors.length ? (
              actors.map((actor) => (
                <div key={actor.actorId} className="actor-row">
                  <div>
                    <p className="actor-name">{actor.actorId}</p>
                    <p className="muted">Last seen {formatTime(actor.last_seen_ms)}</p>
                  </div>
                  <div className="chips">
                    {actor.activeZones.length ? (
                      actor.activeZones.map((zoneId) => (
                        <span key={zoneId} className="chip">
                          {zoneId}
                        </span>
                      ))
                    ) : (
                      <span className="chip muted">clear</span>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <p className="muted">No actors yet.</p>
            )}
          </div>
          <div className="panel-block">
            <h3>Recent events</h3>
            <div className="events">
              {recentEvents.length ? (
                recentEvents.slice(-8).reverse().map((evt, idx) => (
                  <div key={`${evt._id || idx}`} className="event-row">
                    <span className="event-type">{evt.event_type}</span>
                    <span className="muted">{evt.actor_id}</span>
                    <span className="muted">{formatTime(evt.ts_ms)}</span>
                  </div>
                ))
              ) : (
                <p className="muted">No events yet.</p>
              )}
            </div>
          </div>
          {error && (
            <div className="panel-block error">
              <p>API error: {error}</p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
