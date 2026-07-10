export function ResultCard({ result }) {
  if (result.type === "event") return <EventCard e={result} />;
  return <RestaurantCard r={result} />;
}

function Stars({ rating }) {
  if (rating == null) return null;
  return (
    <span className="rating" title={`${rating} rating`}>
      ★ {Number(rating).toFixed(1)}
    </span>
  );
}

function RestaurantCard({ r }) {
  const meta = [r.price, ...(r.categories || [])].filter(Boolean).join(" · ");
  return (
    <div className="card">
      {r.image_url && (
        <div
          className="card-img"
          style={{ backgroundImage: `url(${r.image_url})` }}
          role="img"
          aria-label={r.name}
        />
      )}
      <div className="card-body">
        <div className="card-title-row">
          <span className="card-title">{r.name}</span>
          <Stars rating={r.rating} />
        </div>
        {meta && <div className="card-meta">{meta}</div>}
        {r.address && <div className="card-sub">{r.address}</div>}
        {r.is_closed && <div className="badge closed">Closed now</div>}
        <div className="card-actions">
          {r.reservation_url && (
            <a className="btn primary" href={r.reservation_url} target="_blank" rel="noreferrer">
              Reserve on {r.reservation_platform || "OpenTable"}
            </a>
          )}
          {r.url && (
            <a className="btn ghost" href={r.url} target="_blank" rel="noreferrer">
              Details
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

function EventCard({ e }) {
  return (
    <div className="card">
      {e.image_url && (
        <div
          className="card-img"
          style={{ backgroundImage: `url(${e.image_url})` }}
          role="img"
          aria-label={e.name}
        />
      )}
      <div className="card-body">
        <div className="card-title-row">
          <span className="card-title">{e.name}</span>
          {e.category && <span className="badge">{e.category}</span>}
        </div>
        <div className="card-meta">{formatWhen(e.date, e.time)}</div>
        {e.venue && (
          <div className="card-sub">
            {e.venue}
            {e.city ? `, ${e.city}` : ""}
          </div>
        )}
        <div className="card-actions">
          {e.url && (
            <a className="btn primary" href={e.url} target="_blank" rel="noreferrer">
              Get tickets
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

function formatWhen(date, time) {
  if (!date) return "Date TBA";
  try {
    const d = new Date(`${date}T${time || "00:00"}`);
    const dateStr = d.toLocaleDateString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
    if (!time) return dateStr;
    const timeStr = d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
    return `${dateStr} · ${timeStr}`;
  } catch {
    return date;
  }
}
