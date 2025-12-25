import { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";
const WS_URL = API_BASE.replace(/^http/, "ws").replace(/\/$/, "") + "/ws";

const VIEW = { width: 960, height: 560, padding: 32 };

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

  const bounds = useMemo(() => {
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

  const mappedZones = useMemo(() => {
    const { minX, minY, maxX, maxY } = bounds;
    const dx = maxX - minX || 1;
    const dy = maxY - minY || 1;
    const scaleX = (VIEW.width - VIEW.padding * 2) / dx;
    const scaleY = (VIEW.height - VIEW.padding * 2) / dy;
    return zones.map((z) => {
      const points = z.polygon
        .map(([x, y]) => {
          const px = VIEW.padding + (x - minX) * scaleX;
          const py = VIEW.padding + (y - minY) * scaleY;
          return `${px.toFixed(1)},${py.toFixed(1)}`;
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
      const cx = VIEW.padding + ((center.x / z.polygon.length - minX) * scaleX);
      const cy = VIEW.padding + ((center.y / z.polygon.length - minY) * scaleY);
      return { ...z, points, center: { x: cx, y: cy } };
    });
  }, [zones, bounds]);

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
              {mappedZones.map((zone) => (
                <g key={zone.zone_id} className="zone">
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
