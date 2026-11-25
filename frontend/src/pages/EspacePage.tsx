import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import {
  endAllConnections,
  endConnection,
  getStatus,
  listConnections,
  type ConnectionRecord,
  type ConnectionStatus,
} from "../lib/facein/connections";
import { clearSession, getSession, type ClientSession } from "../lib/facein/session";
import { getRecord } from "../lib/facein/storage";

type Filter = "all" | "ended" | "refused";

const STATUS_LABELS: Record<ConnectionStatus, string> = {
  active: "En cours",
  ended: "Terminée",
  expired: "Expirée",
  refused: "Refusée",
};

const dateFormat = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

function formatRemaining(ms: number) {
  if (ms <= 0) return "expirée";
  const minutes = Math.floor(ms / 60_000);
  const seconds = Math.floor((ms % 60_000) / 1000);
  if (minutes >= 60) return `${Math.floor(minutes / 60)} h ${String(minutes % 60).padStart(2, "0")}`;
  return `${minutes} min ${String(seconds).padStart(2, "0")} s`;
}

function formatAgo(ms: number) {
  const minutes = Math.round(ms / 60_000);
  if (minutes < 1) return "à l’instant";
  if (minutes < 60) return `il y a ${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `il y a ${hours} h`;
  return `il y a ${Math.round(hours / 24)} j`;
}

function hostLabel(origin: string) {
  try {
    return new URL(origin).host;
  } catch {
    return origin;
  }
}

function PartnerAvatar({ name }: { name: string }) {
  const hue = [...name].reduce((sum, char) => sum + char.charCodeAt(0), 0) % 360;
  return (
    <span className="partner-avatar" style={{ background: `linear-gradient(140deg, hsl(${hue} 85% 62%), hsl(${(hue + 40) % 360} 80% 52%))` }} aria-hidden="true">
      {name.replace(/[^A-Za-zÀ-ÿ]/g, "").slice(0, 2).toUpperCase()}
    </span>
  );
}

export function EspacePage() {
  const reduce = useReducedMotion();
  const [session] = useState<ClientSession | null>(() => getSession());
  const [now, setNow] = useState(() => Date.now());
  const [version, setVersion] = useState(0);
  const [filter, setFilter] = useState<Filter>("all");
  const [enrolledAt, setEnrolledAt] = useState<string | null>(null);

  useEffect(() => {
    if (!session) window.location.replace("connexion.html#login");
  }, [session]);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!session) return;
    getRecord(session.userId).then((record) => setEnrolledAt(record?.dateEnregistrement ?? null)).catch(() => setEnrolledAt(null));
  }, [session]);

  useEffect(() => {
    if (session && session.expiresAt <= now) {
      clearSession();
      window.location.replace("connexion.html#login");
    }
  }, [session, now]);

  const { records, isExample } = useMemo(
    () => (session ? listConnections(session.userId) : { records: [] as ConnectionRecord[], isExample: false }),
    [session, version],
  );

  if (!session) return null;

  const active = records.filter((record) => getStatus(record, now) === "active");
  const history = records.filter((record) => getStatus(record, now) !== "active");
  const filtered = history.filter((record) => {
    const status = getStatus(record, now);
    if (filter === "refused") return status === "refused";
    if (filter === "ended") return status === "ended" || status === "expired";
    return true;
  });
  const authorized = records.filter((record) => !record.refused);
  const partners = new Set(authorized.map((record) => record.partnerName)).size;
  const renewal = enrolledAt ? new Date(new Date(enrolledAt).getTime() + 365 * 24 * 3_600_000) : null;

  function end(record: ConnectionRecord) {
    if (record.example) return;
    endConnection(record.id);
    setVersion((value) => value + 1);
  }

  function logout() {
    endAllConnections(session!.userId);
    clearSession();
    window.location.assign("index.html");
  }

  return (
    <div className="espace-page">
      <section className="espace-hero">
        <div className="container espace-hero__inner">
          <div>
            <p className="lead-label">Espace client</p>
            <h1>Bonjour, {session.userId}.</h1>
            <p className="espace-hero__lead">Retrouvez ici les sites partenaires auxquels votre identité FaceIN est connectée.</p>
          </div>
          <div className="session-card">
            <span className="status-dot status-dot--live" aria-hidden="true" />
            <div>
              <strong>Session active</strong>
              <span>Expire dans {formatRemaining(session.expiresAt - now)}</span>
            </div>
            <button className="button button-outline button-small" type="button" onClick={logout}>Se déconnecter</button>
          </div>
        </div>
      </section>

      <div className="container espace-body">
        {isExample && (
          <p className="callout callout--info">
            Aucune connexion à un site partenaire n’est encore enregistrée sur cet appareil. Les lignes marquées « Exemple » illustrent ce que vous verrez ensuite.
          </p>
        )}

        <div className="kpi-row">
          <div className="kpi"><span>Connexions en cours</span><strong>{active.length}</strong></div>
          <div className="kpi"><span>Connexions établies</span><strong>{authorized.length}</strong></div>
          <div className="kpi"><span>Sites partenaires</span><strong>{partners}</strong></div>
          <div className="kpi">
            <span>Photo de référence</span>
            <strong className="kpi__text">{renewal ? `À renouveler avant le ${renewal.toLocaleDateString("fr-FR")}` : "Enregistrée sur un autre appareil"}</strong>
          </div>
        </div>

        <section className="espace-section" aria-labelledby="active-title">
          <div className="espace-section__head">
            <h2 id="active-title">Connexions en cours</h2>
            <p>Chaque connexion reste valable une heure, puis expire d’elle-même.</p>
          </div>
          {active.length === 0 ? (
            <div className="empty-state">
              <p>Aucune connexion en cours. Utilisez le bouton « Se connecter avec FaceIN » sur un site partenaire pour en ouvrir une.</p>
            </div>
          ) : (
            <ul className="live-list">
              <AnimatePresence initial={false}>
                {active.map((record) => {
                  const total = record.expiresAt - record.startedAt;
                  const left = Math.max(0, record.expiresAt - now);
                  return (
                    <motion.li
                      key={record.id}
                      className="live-item"
                      layout={!reduce}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, x: reduce ? 0 : 24 }}
                      transition={{ duration: 0.25 }}
                    >
                      <PartnerAvatar name={record.partnerName} />
                      <div className="live-item__main">
                        <strong>{record.partnerName} {record.example && <em className="tag">Exemple</em>}</strong>
                        <span>{hostLabel(record.partnerOrigin)} · ouverte {formatAgo(now - record.startedAt)}</span>
                        <div className="live-item__bar" aria-hidden="true"><i style={{ transform: `scaleX(${total > 0 ? left / total : 0})` }} /></div>
                      </div>
                      <div className="live-item__time">
                        <span className="status-pill status-pill--active"><span className="status-dot status-dot--live" aria-hidden="true" />En cours</span>
                        <small>expire dans {formatRemaining(left)}</small>
                      </div>
                      <button
                        className="button button-secondary button-small"
                        type="button"
                        disabled={record.example}
                        title={record.example ? "Action indisponible sur un exemple" : undefined}
                        onClick={() => end(record)}
                      >
                        Mettre fin
                      </button>
                    </motion.li>
                  );
                })}
              </AnimatePresence>
            </ul>
          )}
        </section>

        <section className="espace-section" aria-labelledby="history-title">
          <div className="espace-section__head espace-section__head--row">
            <div>
              <h2 id="history-title">Historique</h2>
              <p>Les connexions terminées, expirées ou refusées.</p>
            </div>
            <div className="filter-tabs" role="group" aria-label="Filtrer l’historique">
              {([["all", "Toutes"], ["ended", "Terminées"], ["refused", "Refusées"]] as [Filter, string][]).map(([value, label]) => (
                <button key={value} type="button" aria-pressed={filter === value} className={filter === value ? "is-active" : ""} onClick={() => setFilter(value)}>
                  {filter === value && <motion.span layoutId="filter-pill" className="filter-tabs__pill" transition={{ type: "spring", stiffness: 420, damping: 34 }} />}
                  <span>{label}</span>
                </button>
              ))}
            </div>
          </div>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr><th scope="col">Site</th><th scope="col">Date</th><th scope="col">Durée</th><th scope="col">Statut</th></tr>
              </thead>
              <tbody>
                {filtered.length === 0 && (
                  <tr><td colSpan={4} className="data-table__empty">Aucune connexion dans cette catégorie.</td></tr>
                )}
                {filtered.map((record) => {
                  const status = getStatus(record, now);
                  const end = record.endedAt ?? record.expiresAt;
                  return (
                    <tr key={record.id}>
                      <td>
                        <div className="cell-partner">
                          <PartnerAvatar name={record.partnerName} />
                          <div><strong>{record.partnerName} {record.example && <em className="tag">Exemple</em>}</strong><span>{hostLabel(record.partnerOrigin)}</span></div>
                        </div>
                      </td>
                      <td>{dateFormat.format(record.startedAt)}</td>
                      <td>{status === "refused" ? "—" : `${Math.max(1, Math.round((end - record.startedAt) / 60_000))} min`}</td>
                      <td>
                        <span className={`status-pill status-pill--${status}`}>{STATUS_LABELS[status]}</span>
                        {record.reason && <small className="cell-reason">{record.reason}</small>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
