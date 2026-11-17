import { useEffect, useMemo, useRef, useState } from "react";
import { useReducedMotion } from "motion/react";

export type TypedLine = {
  /** Contenu de la ligne affichée après le prompt. */
  text: string;
  /** Décalage initial (s) avant la première frappe. */
  delay?: number;
};

type TypedTerminalProps = {
  lines: readonly TypedLine[];
  /** Invite affichée devant chaque ligne (sans animation). */
  prompt?: string;
  className?: string;
};

const CHARS_PER_SECOND = 34;
/** Pause entre deux lignes (s), calquée sur TypedStream (letshackit/Portfolio, MIT). */
const LINE_PAUSE = 0.9;

/**
 * Machine à écrire pilotée par le TEMPS et non par les frames : à chaque tick, on calcule
 * le nombre de caractères attendus depuis l'horodatage de départ — le throttling d'onglet
 * ou les chutes de framerate ne « perdent » jamais de texte.
 * prefers-reduced-motion : rendu instantané. Résumé lisible en sr-only.
 */
export function TypedTerminal({ lines, prompt = "$", className }: TypedTerminalProps) {
  const reduceMotion = useReducedMotion();
  const hostRef = useRef<HTMLDivElement>(null);
  const [progress, setProgress] = useState(() => ({
    lineIndex: 0,
    chars: 0,
    done: false,
  }));

  const totalLines = lines.length;
  const plainText = useMemo(
    () => lines.map((line) => line.text).join("\n"),
    [lines],
  );

  useEffect(() => {
    if (reduceMotion) {
      setProgress({ lineIndex: totalLines - 1, chars: Number.POSITIVE_INFINITY, done: true });
      return;
    }

    const host = hostRef.current;
    if (!host) return;

    let inView = true;
    const observer = new IntersectionObserver(
      (entries) => {
        inView = entries.some((entry) => entry.isIntersecting);
      },
      { threshold: 0.05 },
    );
    observer.observe(host);

    // Cumul des délais de démarrage + pauses inter-lignes, exprimé en ms de « frappe effective ».
    const typingPlan = lines.map((line, index) => ({
      typingMs: (line.text.length / CHARS_PER_SECOND) * 1000,
      offsetMs:
        (line.delay ?? 0) * 1000 +
        lines.slice(0, index).reduce((sum, previous) => sum + (previous.text.length / CHARS_PER_SECOND) * 1000 + LINE_PAUSE * 1000, 0),
    }));
    const totalMs = typingPlan[typingPlan.length - 1].offsetMs + typingPlan[typingPlan.length - 1].typingMs;

    let elapsedBeforePause = 0;
    let resumeStart = performance.now();

    const tick = () => {
      if (!document.hidden && inView) {
        elapsedBeforePause += performance.now() - resumeStart;
        resumeStart = performance.now();

        const elapsed = Math.min(elapsedBeforePause, totalMs);
        let lineIndex = 0;
        while (lineIndex < totalLines - 1 && elapsed >= typingPlan[lineIndex].offsetMs + typingPlan[lineIndex].typingMs) {
          lineIndex += 1;
        }
        const current = typingPlan[lineIndex];
        const chars = elapsed >= totalMs ? Number.POSITIVE_INFINITY : Math.floor((elapsed - current.offsetMs) / 1000 * CHARS_PER_SECOND);
        setProgress({ lineIndex, chars, done: elapsed >= totalMs });
      } else {
        resumeStart = performance.now();
      }
    };

    const interval = window.setInterval(tick, 120);
    return () => {
      window.clearInterval(interval);
      observer.disconnect();
    };
  }, [lines, reduceMotion, totalLines]);

  return (
    <div ref={hostRef} className={`typed-terminal${className ? ` ${className}` : ""}`} role="img" aria-label={plainText}>
      <p className="sr-only">{plainText}</p>
      <div className="typed-terminal__screen" aria-hidden="true">
        {lines.slice(0, progress.lineIndex + 1).map((line, index) => {
          const isCurrent = index === progress.lineIndex;
          const visibleChars = isCurrent ? line.text.slice(0, progress.chars) : line.text;
          return (
            <p key={line.text} className="typed-terminal__line">
              <span className="typed-terminal__prompt">{prompt}</span>
              <span>{visibleChars}</span>
              {isCurrent && !progress.done && <span className="typed-terminal__caret" />}
            </p>
          );
        })}
      </div>
    </div>
  );
}
