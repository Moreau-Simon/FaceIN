import { useEffect, useRef } from "react";
import type { MutableRefObject, Ref } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import type { LivenessChallenge } from "../../lib/facein/api";
import { CHALLENGE_LABELS } from "../../lib/facein/liveness";
import { FaceGlyph } from "./FaceGlyph";
import { drawMesh, type MeshFrame } from "./mesh";

export type ScannerState =
  | { kind: "off" }
  | { kind: "starting" }
  | { kind: "ready" }
  | { kind: "calibrating" }
  | { kind: "challenge"; challenge: LivenessChallenge; index: number; total: number }
  | { kind: "processing"; label: string }
  | { kind: "success"; label: string }
  | { kind: "error"; message: string; camera?: boolean };

export type MeshFrameRef = MutableRefObject<{ frame: MeshFrame; at: number }>;

type FaceScannerProps = {
  videoRef: Ref<HTMLVideoElement>;
  frameRef: MeshFrameRef;
  state: ScannerState;
  progress: number;
  idleTitle: string;
  onRetryCamera?: () => void;
};

const TICKS = 60;
const C = 180;
const R1 = 161;
const R2 = 175;

function mix(a: string, b: string, t: number) {
  const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16));
  const pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
  return `rgb(${pa.map((v, i) => Math.round(v + (pb[i] - v) * t)).join(" ")})`;
}

const ticks = Array.from({ length: TICKS }, (_, i) => {
  const a = (i / TICKS) * Math.PI * 2 - Math.PI / 2;
  return {
    x1: C + R1 * Math.cos(a), y1: C + R1 * Math.sin(a),
    x2: C + R2 * Math.cos(a), y2: C + R2 * Math.sin(a),
    color: mix("#00F0FF", "#3B82F6", i / (TICKS - 1)),
  };
});

function instruction(state: ScannerState, idleTitle: string): { counter: string; title: string } {
  switch (state.kind) {
    case "off": return { counter: "Caméra inactive", title: idleTitle };
    case "starting": return { counter: "Préparation", title: "Autorisez l’accès à la caméra" };
    case "ready": return { counter: "Caméra prête", title: idleTitle };
    case "calibrating": return { counter: "Calibrage", title: "Regardez la caméra, de face" };
    case "challenge": return { counter: `Défi ${state.index + 1} sur ${state.total}`, title: CHALLENGE_LABELS[state.challenge].title };
    case "processing": return { counter: "Vérification", title: state.label };
    case "success": return { counter: "Terminé", title: state.label };
    case "error": return { counter: "Échec", title: state.camera ? "Caméra indisponible" : "Vérification interrompue" };
  }
}

export function FaceScanner({ videoRef, frameRef, state, progress, idleTitle, onRetryCamera }: FaceScannerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const reduce = useReducedMotion();
  const cameraOn = state.kind !== "off" && state.kind !== "starting" && !(state.kind === "error" && state.camera);
  const success = state.kind === "success";
  const busy = state.kind === "processing" || state.kind === "calibrating";
  const blurVideo = success;
  const lit = success ? TICKS : Math.round((TICKS * Math.min(100, Math.max(0, progress))) / 100);
  const { counter, title } = instruction(state, idleTitle);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx || !cameraOn) {
      ctx?.clearRect(0, 0, canvas?.width ?? 0, canvas?.height ?? 0);
      return;
    }
    let raf = 0;
    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(canvas.clientWidth * dpr);
      canvas.height = Math.round(canvas.clientHeight * dpr);
    };
    resize();
    window.addEventListener("resize", resize);
    const loop = (t: number) => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const current = frameRef.current;
      const fresh = current.frame && performance.now() - current.at < 700 ? current.frame : null;
      drawMesh(ctx, canvas.width, canvas.height, dpr, reduce ? 0 : t, fresh, success ? "ok" : "scan");
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, [cameraOn, success, frameRef, reduce]);

  const glyphMode = state.kind === "challenge" ? state.challenge : success ? "success" : null;

  return (
    <div className={`scanner${success ? " is-success" : ""}${busy ? " is-busy" : ""}`}>
      <div className="scanner__stage">
        <svg className="scanner__ring" viewBox="0 0 360 360" aria-hidden="true">
          {ticks.map((tick, i) => (
            <line key={`b${i}`} {...{ x1: tick.x1, y1: tick.y1, x2: tick.x2, y2: tick.y2 }} className="scanner__tick" />
          ))}
        </svg>
        <svg className="scanner__ring scanner__ring--lit" viewBox="0 0 360 360" aria-hidden="true">
          {ticks.map((tick, i) => (
            <line
              key={`l${i}`}
              {...{ x1: tick.x1, y1: tick.y1, x2: tick.x2, y2: tick.y2 }}
              className="scanner__tick scanner__tick--lit"
              style={{ stroke: success ? "#34F5B0" : tick.color, opacity: i < lit ? 1 : 0, transitionDelay: reduce ? "0ms" : `${(i % 20) * 18}ms` }}
            />
          ))}
        </svg>
        {busy && <span className="scanner__sweep" aria-hidden="true" />}

        <div className="scanner__medallion">
          {state.kind === "starting" && <span className="scanner__skeleton" aria-hidden="true" />}
          <video
            ref={videoRef}
            className={cameraOn ? "is-active" : ""}
            style={{ filter: blurVideo ? "blur(12px) brightness(.55)" : undefined }}
            autoPlay
            muted
            playsInline
            aria-label="Aperçu de votre caméra, traité uniquement sur cet appareil"
          />
          <canvas ref={canvasRef} aria-hidden="true" style={{ opacity: success ? 0.25 : 1 }} />
          {state.kind === "off" && (
            <div className="scanner__placeholder" aria-hidden="true">
              <FaceGlyph mode="idle" loop={false} />
            </div>
          )}
          {state.kind === "error" && state.camera && (
            <div className="scanner__error">
              <strong>Accès à la caméra requis</strong>
              <p>{state.message}</p>
              {onRetryCamera && <button className="scanner__retry" type="button" onClick={onRetryCamera}>Réessayer</button>}
            </div>
          )}
          {success && (
            <motion.span
              className="scanner__wave"
              aria-hidden="true"
              initial={{ scale: 0.55, opacity: 0.8 }}
              animate={{ scale: 1.35, opacity: 0 }}
              transition={{ duration: reduce ? 0 : 1.1, ease: "easeOut", delay: 0.3 }}
            />
          )}
        </div>

        <AnimatePresence mode="wait">
          {glyphMode && (
            <motion.div
              key={`${glyphMode}-${state.kind === "challenge" ? state.index : "ok"}`}
              className={`scanner__glyph${success ? " is-success" : ""}`}
              initial={{ opacity: 0, scale: 0.55, y: 0 }}
              animate={success || reduce
                ? { opacity: 1, scale: 1.1, y: 0 }
                : { opacity: [0, 1, 1, 0], scale: [0.55, 1, 1, 0.34], y: ["0%", "0%", "0%", "118%"] }}
              exit={{ opacity: 0, transition: { duration: 0.15 } }}
              transition={success || reduce ? { duration: 0.45, ease: [0.34, 1.56, 0.64, 1] } : { duration: 2.2, times: [0, 0.2, 0.68, 1], ease: "easeInOut" }}
            >
              <FaceGlyph mode={glyphMode} />
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {state.kind === "challenge" && (
            <motion.div
              key={`pill-${state.index}`}
              className="scanner__pill"
              initial={{ opacity: 0, y: 10, scale: 0.85 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 6 }}
              transition={{ delay: reduce ? 0 : 1.9, duration: 0.4, ease: [0.34, 1.56, 0.64, 1] }}
            >
              <FaceGlyph mode={state.challenge} className="scanner__pill-glyph" />
              <span>{CHALLENGE_LABELS[state.challenge].short}</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="scanner__instruction" aria-live="polite">
        <span className="scanner__counter">{counter}</span>
        <AnimatePresence mode="wait">
          <motion.h3
            key={title}
            initial={{ opacity: 0, y: reduce ? 0 : 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: reduce ? 0 : -6 }}
            transition={{ duration: 0.2 }}
          >
            {title}
          </motion.h3>
        </AnimatePresence>
      </div>
    </div>
  );
}
