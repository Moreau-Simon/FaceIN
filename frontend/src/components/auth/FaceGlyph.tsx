import { motion, useReducedMotion } from "motion/react";
import type { LivenessChallenge } from "../../lib/facein/api";

/**
 * Glyphe « Face ID » animé de la capture : reprise du glyphe 2.5D de `partner-demo/js/liveness-guide.js`.
 */
const MOUTH = { neutral: "M36 66q12 3 24 0", smile: "M31 61q17 20 34 0" };
const EYES = { neutral: ["M34 38v8", "M62 38v8"], wide: ["M34 35v13", "M62 35v13"], closed: ["M30 43h8", "M58 43h8"] };

export type GlyphMode = LivenessChallenge | "idle" | "success";

type FaceGlyphProps = { mode: GlyphMode; className?: string; loop?: boolean };

export function FaceGlyph({ mode, className = "", loop = true }: FaceGlyphProps) {
  const reduce = useReducedMotion();
  const repeat = reduce ? 0 : loop ? Infinity : 0;
  const base = { duration: 1.6, ease: "easeInOut" as const, repeat, repeatDelay: 0.35 };
  const dir = mode === "turn_right" ? 1 : -1;
  const turning = mode === "turn_left" || mode === "turn_right";
  const animateFace = !reduce && mode !== "success";

  return (
    <svg className={`face-glyph ${className}`} viewBox="0 0 96 96" fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {mode === "success" ? (
        <g>
          <motion.circle cx="48" cy="48" r="34" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: reduce ? 0 : 0.5, ease: "easeOut" }} />
          <motion.path d="M32 49l11 11 22-23" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: reduce ? 0 : 0.4, delay: reduce ? 0 : 0.35, ease: "easeOut" }} />
        </g>
      ) : (
        <>
          <path d="M8 28V22a14 14 0 0 1 14-14h6M68 8h6a14 14 0 0 1 14 14v6M88 68v6a14 14 0 0 1-14 14h-6M28 88h-6A14 14 0 0 1 8 74v-6" />
          <motion.g
            style={{ originX: "48px", originY: "48px" }}
            animate={animateFace && turning ? { scaleX: [1, 0.88, 0.88, 1] } : { scaleX: 1 }}
            transition={base}
          >
            <motion.g animate={animateFace && turning ? { x: [0, 5 * dir, 5 * dir, 0] } : { x: 0 }} transition={base}>
              <motion.path
                d={EYES.neutral[0]}
                animate={animateFace && mode === "smile" ? { d: [EYES.neutral[0], EYES.wide[0], EYES.wide[0], EYES.neutral[0]] }
                  : animateFace && mode === "blink" ? { d: [EYES.neutral[0], EYES.closed[0], EYES.neutral[0], EYES.neutral[0]] }
                  : { d: EYES.neutral[0] }}
                transition={base}
              />
              <motion.path
                d={EYES.neutral[1]}
                animate={animateFace && mode === "smile" ? { d: [EYES.neutral[1], EYES.wide[1], EYES.wide[1], EYES.neutral[1]] }
                  : animateFace && mode === "blink" ? { d: [EYES.neutral[1], EYES.closed[1], EYES.neutral[1], EYES.neutral[1]] }
                  : { d: EYES.neutral[1] }}
                transition={base}
              />
            </motion.g>
            <motion.path
              d="M48 36v18h-5"
              style={{ originX: "48px", originY: "36px" }}
              animate={animateFace && turning ? { x: [0, 9 * dir, 9 * dir, 0], rotate: [0, 14 * dir, 14 * dir, 0] } : { x: 0, rotate: 0 }}
              transition={base}
            />
            <motion.path
              d={MOUTH.neutral}
              animate={animateFace && mode === "smile" ? { d: [MOUTH.neutral, MOUTH.smile, MOUTH.smile, MOUTH.neutral] }
                : animateFace && turning ? { x: [0, 4 * dir, 4 * dir, 0] } : { d: MOUTH.neutral, x: 0 }}
              transition={base}
            />
          </motion.g>
          {turning && (
            <motion.path
              d="M92 30q12 18 0 36M84 62l8 4 3-9"
              style={{ originX: "48px", originY: "48px", scaleX: dir === 1 ? 1 : -1 }}
              initial={{ pathLength: 0, opacity: 0 }}
              animate={reduce ? { pathLength: 1, opacity: 1 } : { pathLength: [0, 1, 1, 0], opacity: [0, 1, 1, 0] }}
              transition={base}
            />
          )}
        </>
      )}
    </svg>
  );
}
