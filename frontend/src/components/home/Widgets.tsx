import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { PointerEvent } from "react";
import { AnimatePresence, motion, useInView, useMotionValue, useReducedMotion, useSpring, useTransform } from "motion/react";
import { BrandMark } from "../BrandMark";
import { useLoopStep } from "./useLoopStep";

const Check = () => (
  <svg className="tick" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="8" /><path d="M4.6 8.2 7 10.5l4.4-4.8" /></svg>
);

/* ------------------------------------------------------------------ */
/* 1. Connexion sur un site partenaire                                 */
/* ------------------------------------------------------------------ */

const verificationRows = [
  { label: "Vecteur calculé sur l’appareil", value: "128 valeurs", mono: true },
  { label: "Image effacée", value: "check" },
  { label: "Preuve générée", value: "zk-SNARK", mono: true },
];
const nodes = [
  { label: "Nœud A", ok: true },
  { label: "Nœud B", ok: true },
  { label: "Nœud C", ok: false },
];

export function PartnerLoginVisual() {
  const { ref, step } = useLoopStep<HTMLDivElement>(8, 480);
  const scanning = step >= 1 && step < 7;
  const done = step >= 8;

  return (
    <div className="partner-visual" ref={ref}>
      <div className="laptop">
        <div className="laptop__screen">
          <div className="laptop__bar"><b>atelier lune</b><span>Boutique</span><span>Journal</span><span>Compte</span></div>
          <div className="laptop__content">
            <p>Connexion à votre compte</p>
            <div className={`scan-hex${scanning ? " is-scanning" : ""}${done ? " is-done" : ""}`}>
              <svg viewBox="0 0 100 100" aria-hidden="true">
                <path className="scan-hex__outline" d="M50 6 88 28v44L50 94 12 72V28Z" />
                {!done && <><circle cx="38" cy="44" r="2.6" /><circle cx="62" cy="44" r="2.6" /><circle cx="50" cy="55" r="2" /><circle cx="42" cy="66" r="2" /><circle cx="58" cy="66" r="2" /><path className="scan-hex__lines" d="M38 44 50 55 62 44M42 66 50 55 58 66" /></>}
                {done && <path className="scan-hex__check" d="M35 51l10 10 21-22" />}
              </svg>
              {scanning && <span className="scan-hex__beam" aria-hidden="true" />}
            </div>
            <small>L’image reste sur cet appareil</small>
            <span className={`fake-button${done ? " is-done" : ""}`}><BrandMark inverted /> {done ? "Connecté avec FaceIN" : "Se connecter avec FaceIN"}</span>
          </div>
        </div>
        <div className="laptop__base" />
      </div>

      <div className="verify-popover">
        <div className="verify-popover__bar"><i /><i /><i /><span>verify.facein.fr</span></div>
        <strong>Récapitulatif de la vérification</strong>
        <ul>
          {verificationRows.map((row, index) => (
            <li key={row.label} className={step > index ? "is-on" : ""}>
              <span>{row.label}</span>
              {row.value === "check" ? <Check /> : <code>{row.value}</code>}
            </li>
          ))}
        </ul>
        <ul>
          {nodes.map((node, index) => (
            <li key={node.label} className={step > index + 3 ? "is-on" : ""}>
              <span>{node.label}</span>
              {node.ok ? <Check /> : <em className="tag tag--warn">Délai dépassé</em>}
            </li>
          ))}
        </ul>
        <div className={`verify-popover__total${step > 6 ? " is-on" : ""}`}><span>Consensus</span><b>2 sur 3</b></div>
        <div className={`verify-popover__result${step > 7 ? " is-on" : ""}`}>Connexion autorisée</div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* 2. Niveau de sécurité                                               */
/* ------------------------------------------------------------------ */

const plans = {
  standard: { name: "Offre Standard", vector: "Vecteur de 128 valeurs", level: 0.56, speed: "plus rapide", price: "Gratuit" },
  reinforced: { name: "Offre Renforcée", vector: "Vecteur de 256 valeurs", level: 0.86, speed: "un peu plus long", price: "2,99 € / mois" },
};
const bars = [38, 52, 44, 61, 57, 74, 66, 83, 78, 92, 88, 104, 97, 112];

export function SecurityVisual() {
  const [plan, setPlan] = useState<keyof typeof plans>("reinforced");
  const pillId = useId();
  const [hovered, setHovered] = useState<number | null>(null);
  const chartRef = useRef<HTMLDivElement>(null);
  const inView = useInView(chartRef, { once: true, amount: 0.4 });
  const reduce = useReducedMotion();
  const current = plans[plan];
  const max = Math.max(...bars);
  const total = bars.reduce((sum, value) => sum + value, 0);

  return (
    <div className="security-visual">
      <div className="plan-card" data-interactive>
        <div className="plan-switch" role="group" aria-label="Choisir une offre">
          {(Object.keys(plans) as (keyof typeof plans)[]).map((key) => (
            <button key={key} type="button" aria-pressed={plan === key} className={plan === key ? "is-active" : ""} onClick={() => setPlan(key)}>
              {plan === key && <motion.span layoutId={`plan-pill-${pillId}`} className="plan-switch__pill" transition={{ type: "spring", stiffness: 500, damping: 36 }} />}
              <span>{key === "standard" ? "Standard" : "Renforcée"}</span>
            </button>
          ))}
        </div>
        <div className="plan-card__head">
          <span className="plan-card__icon"><BrandMark /></span>
          <div>
            <AnimatePresence mode="wait" initial={false}>
              <motion.strong key={current.name} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.16 }}>{current.name}</motion.strong>
            </AnimatePresence>
            <small>{current.vector}</small>
          </div>
          <span className="tag tag--violet">ZK</span>
        </div>
        <div className="meter">
          <span>Sécurité</span>
          <div className="meter__track"><motion.i animate={{ scaleX: current.level }} initial={false} transition={{ type: "spring", stiffness: 140, damping: 20 }} /></div>
        </div>
        <dl className="plan-card__facts">
          <div><dt>Temps de connexion</dt><dd>{current.speed}</dd></div>
          <div><dt>Tarif</dt><dd>{current.price}</dd></div>
        </dl>
      </div>

      <div className="chart-card" ref={chartRef}>
        <small>Connexions des 14 derniers jours</small>
        <strong>{hovered === null ? total.toLocaleString("fr-FR") : bars[hovered]}</strong>
        <span className="chart-card__hint">{hovered === null ? "au total" : `jour ${hovered + 1}`}</span>
        <div className="bars" role="img" aria-label="Exemple de graphique : connexions quotidiennes en hausse">
          {bars.map((value, index) => (
            <motion.i
              key={index}
              data-interactive
              className={hovered === index ? "is-hovered" : ""}
              style={{ height: `${(value / max) * 100}%` }}
              initial={reduce ? false : { scaleY: 0 }}
              animate={inView || reduce ? { scaleY: 1 } : undefined}
              transition={{ delay: index * 0.035, type: "spring", stiffness: 200, damping: 22 }}
              onPointerEnter={() => setHovered(index)}
              onPointerLeave={() => setHovered(null)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* 3. Preuve à divulgation nulle                                       */
/* ------------------------------------------------------------------ */

export function ProofVisual() {
  const dots = useMemo(() => {
    const result: { x: number; y: number; color: string; delay: number }[] = [];
    for (let y = 8; y <= 192; y += 7.4) {
      for (let x = 8; x <= 192; x += 7.4) {
        const dx = x - 100;
        const dy = y - 100;
        const r = Math.hypot(dx, dy);
        if (r < 46 || r > 88) continue;
        const angle = (Math.atan2(dy, dx) * 180) / Math.PI + 180;
        const color = angle < 150 ? "#7a5cff" : angle < 250 ? "#ef6fb4" : "#ff9a3d";
        result.push({ x, y, color, delay: (angle / 360) * 1.6 });
      }
    }
    return result;
  }, []);

  return (
    <div className="proof-visual">
      <span className="chip chip--mono">vecteur <b>••••••••</b></span>
      <svg viewBox="0 0 200 200" className="proof-visual__ring" aria-hidden="true">
        {dots.map((dot, index) => (
          <circle key={index} cx={dot.x} cy={dot.y} r="2.3" fill={dot.color} style={{ animationDelay: `${dot.delay}s` }} />
        ))}
      </svg>
      <span className="chip chip--ok"><Check /> Preuve valide</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* 4. Carte d'identité numérique                                       */
/* ------------------------------------------------------------------ */

export function IdentityVisual() {
  const reduce = useReducedMotion();
  const px = useMotionValue(0.5);
  const py = useMotionValue(0.5);
  const rotateX = useSpring(useTransform(py, [0, 1], [10, -10]), { stiffness: 180, damping: 18 });
  const rotateY = useSpring(useTransform(px, [0, 1], [-12, 12]), { stiffness: 180, damping: 18 });
  const glareX = useTransform(px, [0, 1], ["0%", "100%"]);
  const glareY = useTransform(py, [0, 1], ["0%", "100%"]);

  function move(event: PointerEvent<HTMLDivElement>) {
    if (reduce) return;
    const rect = event.currentTarget.getBoundingClientRect();
    px.set((event.clientX - rect.left) / rect.width);
    py.set((event.clientY - rect.top) / rect.height);
  }

  return (
    <div className="identity-visual" onPointerMove={move} onPointerLeave={() => { px.set(0.5); py.set(0.5); }}>
      <motion.div className="id-card" style={{ rotateX, rotateY }}>
        <div className="id-card__art">
          <span className="id-card__logo"><BrandMark inverted /></span>
          <b>ZK</b>
          <motion.span className="id-card__glare" style={{ "--gx": glareX, "--gy": glareY } as never} />
        </div>
        <div className="id-card__meta">
          <div><strong>manon_m</strong><span>Engagement actif</span></div>
          <em>FaceIN</em>
        </div>
      </motion.div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* 5. Réseau de vérification                                           */
/* ------------------------------------------------------------------ */

type Vec = [number, number, number];

export function NetworkVisual() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const inView = useInView(wrapRef, { amount: 0.2 });
  const reduce = useReducedMotion();
  const speed = useRef(1);
  const [labels, setLabels] = useState<{ id: string; x: number; y: number; front: boolean }[]>([]);

  const points = useMemo<Vec[]>(() => {
    const n = 520;
    const golden = Math.PI * (3 - Math.sqrt(5));
    return Array.from({ length: n }, (_, i) => {
      const y = 1 - (i / (n - 1)) * 2;
      const r = Math.sqrt(1 - y * y);
      return [Math.cos(golden * i) * r, y, Math.sin(golden * i) * r];
    });
  }, []);

  const anchors = useMemo<{ id: string; v: Vec }[]>(() => [
    { id: "A", v: [-0.62, -0.32, 0.71] },
    { id: "B", v: [0.68, -0.18, 0.71] },
    { id: "C", v: [0.05, 0.62, 0.78] },
  ], []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    let raf = 0;
    let angle = -0.25;
    let last = performance.now();
    let lastLabels = 0;

    const draw = (now: number) => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const W = canvas.clientWidth;
      const H = canvas.clientHeight;
      if (canvas.width !== Math.round(W * dpr)) { canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr); }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, W, H);
      const dt = Math.min(64, now - last);
      last = now;
      if (!reduce) angle += dt * 0.00012 * speed.current;
      const R = Math.min(W, H) * 0.44;
      const cx = W / 2;
      const cy = H / 2;
      const cos = Math.cos(angle);
      const sin = Math.sin(angle);
      const tilt = -0.32;
      const ct = Math.cos(tilt);
      const st = Math.sin(tilt);
      const proj = ([x, y, z]: Vec) => {
        const x1 = x * cos + z * sin;
        const z1 = -x * sin + z * cos;
        const y2 = y * ct - z1 * st;
        const z2 = y * st + z1 * ct;
        return { x: cx + x1 * R, y: cy + y2 * R, z: z2 };
      };

      for (const p of points) {
        const q = proj(p);
        const depth = (q.z + 1) / 2;
        ctx.globalAlpha = 0.12 + depth * 0.75;
        ctx.fillStyle = q.x < cx ? "#7a5cff" : "#c06cf0";
        ctx.beginPath();
        ctx.arc(q.x, q.y, 0.7 + depth * 1.3, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;

      // Ancres suivant la rotation (légèrement fixées vers l'avant pour rester lisibles)
      const anchorProj = anchors.map((anchor) => {
        const local: Vec = [anchor.v[0] * Math.cos(angle * 0.35) - anchor.v[2] * Math.sin(angle * 0.35) * 0.2, anchor.v[1], anchor.v[2]];
        const len = Math.hypot(...local);
        const v: Vec = [local[0] / len, local[1] / len, local[2] / len];
        return { id: anchor.id, x: cx + v[0] * R, y: cy + v[1] * R, z: v[2] };
      });

      // Arcs entre les nœuds et impulsion qui circule
      const pairs: [number, number][] = [[0, 1], [1, 2], [2, 0]];
      pairs.forEach(([a, b], index) => {
        const pa = anchorProj[a];
        const pb = anchorProj[b];
        const mx = (pa.x + pb.x) / 2;
        const my = (pa.y + pb.y) / 2 - R * 0.28;
        const failing = b === 2 || a === 2;
        ctx.setLineDash([4, 5]);
        ctx.strokeStyle = failing ? "rgba(255,138,92,.75)" : "rgba(122,92,255,.7)";
        ctx.lineWidth = 1.4;
        ctx.beginPath();
        ctx.moveTo(pa.x, pa.y);
        ctx.quadraticCurveTo(mx, my, pb.x, pb.y);
        ctx.stroke();
        ctx.setLineDash([]);
        if (!reduce) {
          const t = ((now / 1600 + index / 3) % 1);
          const x = (1 - t) ** 2 * pa.x + 2 * (1 - t) * t * mx + t ** 2 * pb.x;
          const y = (1 - t) ** 2 * pa.y + 2 * (1 - t) * t * my + t ** 2 * pb.y;
          ctx.fillStyle = failing ? "#ff8a5c" : "#533afd";
          ctx.shadowColor = ctx.fillStyle;
          ctx.shadowBlur = 8;
          ctx.beginPath();
          ctx.arc(x, y, 2.6, 0, Math.PI * 2);
          ctx.fill();
          ctx.shadowBlur = 0;
        }
      });

      if (now - lastLabels > 90) {
        lastLabels = now;
        setLabels(anchorProj.map((a) => ({ id: a.id, x: (a.x / W) * 100, y: (a.y / H) * 100, front: a.z > 0 })));
      }
      if (inView && !reduce) raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [points, anchors, inView, reduce]);

  return (
    <div
      className="network-visual"
      ref={wrapRef}
      onPointerEnter={() => { speed.current = 3.2; }}
      onPointerLeave={() => { speed.current = 1; }}
    >
      <canvas ref={canvasRef} aria-hidden="true" />
      {labels.map((label) => (
        <span key={label.id} className={`node-badge${label.id === "C" ? " node-badge--late" : ""}`} style={{ left: `${label.x}%`, top: `${label.y}%` }}>
          {label.id}
        </span>
      ))}
      <span className="sr-only">Trois nœuds A, B et C vérifient la preuve ; deux validations suffisent.</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* 6. Tableau de bord partenaire                                       */
/* ------------------------------------------------------------------ */

const services = [
  { name: "Atelier Lune", country: "France", count: 7513, rate: "99,2 %", color: "#ff8a3d" },
  { name: "Studio Kora", country: "Belgique", count: 1352, rate: "98,7 %", color: "#7a5cff" },
  { name: "Biblio+", country: "France", count: 1122, rate: "99,5 %", color: "#15be53" },
  { name: "Vélo Nomade", country: "Suisse", count: 3290, rate: "98,9 %", color: "#ef4fa6" },
  { name: "Maison Sel", country: "France", count: 302, rate: "99,0 %", color: "#3f85ff" },
  { name: "Campus Nord", country: "Canada", count: 2021, rate: "99,4 %", color: "#ff8a3d" },
  { name: "Pixel Café", country: "France", count: 594, rate: "97,8 %", color: "#7a5cff" },
];

export function DashboardVisual({ expanded = false }: { expanded?: boolean }) {
  const { ref, step } = useLoopStep<HTMLDivElement>(3, 900, 5200);
  const [method, setMethod] = useState<"face" | "password">("face");
  const [section, setSection] = useState("Services");
  const showNew = step >= 1;

  return (
    <div className={`dashboard-visual${expanded ? " is-expanded" : ""}`} ref={ref}>
      <div className="mini-login" data-interactive>
        <div className="mini-login__head"><span className="partner-avatar partner-avatar--sm" style={{ background: "linear-gradient(140deg,#7a5cff,#ef4fa6)" }}>AL</span><div><b>Atelier Lune</b><small>Connexion à votre compte</small></div></div>
        <button type="button" className={`mini-choice${method === "face" ? " is-selected" : ""}`} onClick={() => setMethod("face")}>
          <i /> Mon visage <span><BrandMark /> FaceIN</span>
        </button>
        <button type="button" className={`mini-choice${method === "password" ? " is-selected" : ""}`} onClick={() => setMethod("password")}>
          <i /> Mot de passe
        </button>
        <a className="mini-login__submit" href="connexion.html#login">{method === "face" ? "Se connecter avec mon visage" : "Continuer"}</a>
      </div>

      <div className="mini-dashboard">
        <div className="mini-dashboard__bar"><i /><i /><i /><span>dashboard.facein.fr</span></div>
        <div className="mini-dashboard__layout">
          <nav aria-label="Navigation du tableau de bord illustré" data-interactive>
            <b><BrandMark /> FaceIN</b>
            {["Accueil", "Services", "Journal", "Clés"].map((item) => (
              <button key={item} type="button" className={section === item ? "is-active" : ""} onClick={() => setSection(item)}>{item}</button>
            ))}
          </nav>
          <div className="mini-dashboard__main">
            <h4>Connexions par service <span className="tag">Exemple</span></h4>
            <table>
              <thead><tr><th>Service</th><th>Pays</th><th>Connexions</th><th>Réussite</th></tr></thead>
              <tbody>
                <AnimatePresence initial={false}>
                  {showNew && (
                    <motion.tr
                      key="new"
                      className="is-new"
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
                    >
                      <td><i style={{ background: "#533afd" }} />Nouveau : Les Ateliers</td><td>France</td><td>{step >= 2 ? 2 : 1}</td><td>100 %</td>
                    </motion.tr>
                  )}
                </AnimatePresence>
                {services.map((service) => (
                  <tr key={service.name}>
                    <td><i style={{ background: service.color }} />{service.name}</td>
                    <td>{service.country}</td>
                    <td>{service.count.toLocaleString("fr-FR")}</td>
                    <td>{service.rate}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
