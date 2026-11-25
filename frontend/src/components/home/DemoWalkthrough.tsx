import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { FaceGlyph } from "../auth/FaceGlyph";

const steps = [
  { title: "Vous cliquez sur « Se connecter avec FaceIN »", text: "Le site partenaire ouvre FaceIN. Aucun mot de passe à saisir." },
  { title: "Votre navigateur lit votre visage", text: "Deux défis aléatoires, comme cligner des yeux ou tourner la tête, prouvent que vous êtes bien là." },
  { title: "128 valeurs, calculées ici", text: "Votre visage devient un vecteur de 128 valeurs. L’image est effacée aussitôt." },
  { title: "Une preuve, pas une photo", text: "Le navigateur prouve que ce vecteur ressemble à celui de l’inscription, sans le révéler." },
  { title: "Trois serveurs vérifient", text: "Deux validations sur trois suffisent : le site reçoit un jeton de connexion." },
];

const STEP_MS = 3600;

function StepVisual({ index }: { index: number }) {
  if (index === 0) {
    return <div className="walk-visual walk-visual--button"><span className="fake-button"><svg viewBox="56 30 281 317" aria-hidden="true"><path d="M190 37L256 73L125 150V224L192 264L128 301L63 264V109Z" fill="#fff" /><path d="M266 80L330 116V267L203 340L139 303L270 228V152L205 115Z" fill="#7aa2ff" /></svg>Se connecter avec FaceIN</span><span className="walk-cursor" aria-hidden="true" /></div>;
  }
  if (index === 1) {
    return <div className="walk-visual walk-visual--glyph"><FaceGlyph mode="turn_left" /></div>;
  }
  if (index === 2) {
    return (
      <div className="walk-visual walk-visual--vector">
        {Array.from({ length: 32 }, (_, i) => <motion.i key={i} initial={{ scaleY: 0.1 }} animate={{ scaleY: 0.25 + Math.abs(Math.sin(i * 1.7)) * 0.75 }} transition={{ delay: i * 0.025, type: "spring", stiffness: 180, damping: 16 }} />)}
      </div>
    );
  }
  if (index === 3) {
    return <div className="walk-visual walk-visual--proof"><code>π = (a, b, c)</code><span>engagement ✓</span><span>distance ≤ seuil ✓</span></div>;
  }
  return (
    <div className="walk-visual walk-visual--nodes">
      {["A", "B", "C"].map((node, i) => (
        <motion.span key={node} className={i === 2 ? "is-late" : "is-ok"} initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ delay: 0.15 + i * 0.2 }}>
          {node}<small>{i === 2 ? "délai" : "✓"}</small>
        </motion.span>
      ))}
      <motion.b initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.9 }}>Jeton délivré</motion.b>
    </div>
  );
}

/** Démonstration guidée du parcours, ouverte depuis le bandeau « Voyez FaceIN en action ». */
export function DemoWalkthrough() {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const reduce = useReducedMotion();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  useEffect(() => {
    if (!open || paused || reduce) return;
    const timer = window.setTimeout(() => setIndex((value) => (value + 1) % steps.length), STEP_MS);
    return () => window.clearTimeout(timer);
  }, [open, index, paused, reduce]);

  function close() {
    setOpen(false);
    triggerRef.current?.focus();
  }

  return (
    <>
      <button ref={triggerRef} className="button button-light" type="button" onClick={() => { setIndex(0); setOpen(true); }}>
        <span className="play-icon" aria-hidden="true" /> Voir la démonstration
      </button>
      <dialog
        ref={dialogRef}
        className="walk-dialog"
        aria-labelledby="walk-title"
        onCancel={(event) => { event.preventDefault(); close(); }}
        onClick={(event) => { if (event.target === dialogRef.current) close(); }}
      >
        <div className="walk-panel">
          <button className="widget-dialog__close walk-close" type="button" aria-label="Fermer la démonstration" onClick={close}>
            <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>
          </button>
          <h2 id="walk-title">Une connexion FaceIN, étape par étape</h2>
          <div className="walk-layout">
            <ol className="walk-steps">
              {steps.map((step, i) => (
                <li key={step.title}>
                  <button type="button" aria-current={i === index ? "step" : undefined} className={i === index ? "is-active" : i < index ? "is-done" : ""} onClick={() => { setIndex(i); setPaused(true); }}>
                    <span className="walk-steps__num">{i + 1}</span>
                    <span>{step.title}</span>
                    {i === index && !paused && !reduce && <motion.i className="walk-steps__progress" key={`p${index}`} initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ duration: STEP_MS / 1000, ease: "linear" }} />}
                  </button>
                </li>
              ))}
            </ol>
            <div className="walk-stage">
              <AnimatePresence mode="wait">
                <motion.div key={index} className="walk-stage__inner" initial={{ opacity: 0, y: reduce ? 0 : 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: reduce ? 0 : -12 }} transition={{ duration: 0.28 }}>
                  <StepVisual index={index} />
                  <p>{steps[index].text}</p>
                </motion.div>
              </AnimatePresence>
              <div className="walk-controls">
                <button type="button" className="text-button" onClick={() => setPaused((value) => !value)} disabled={reduce ?? false}>{paused ? "Reprendre" : "Pause"}</button>
                <a className="button button-primary button-small" href="connexion.html#register">Essayer avec mon visage <span className="button-arrow" aria-hidden="true" /></a>
              </div>
            </div>
          </div>
        </div>
      </dialog>
    </>
  );
}
