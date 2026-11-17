import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from "motion/react";
import { useRef, type PointerEvent as ReactPointerEvent, type PropsWithChildren } from "react";

type MagnetProps = PropsWithChildren<{
  className?: string;
  /** Portion du déplacement curseur restituée par l'élément (0–1). */
  strength?: number;
}>;

/**
 * Effet magnétique curseur (inspiré de Magnet, react-bits, licence MIT + Commons Clause).
 * Spring amorti dépendant du delta pour rester insensible au framerate.
 * prefers-reduced-motion : désactivé (wrapper passif).
 */
export function Magnet({ children, className, strength = 0.32 }: MagnetProps) {
  const reduceMotion = useReducedMotion();
  const ref = useRef<HTMLSpanElement>(null);

  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const springX = useSpring(x, { stiffness: 180, damping: 18, mass: 0.5 });
  const springY = useSpring(y, { stiffness: 180, damping: 18, mass: 0.5 });
  const transform = useTransform(
    [springX, springY],
    ([latestX, latestY]: number[]) => `translate3d(${latestX}px, ${latestY}px, 0)`,
  );

  const handleMove = (event: ReactPointerEvent<HTMLSpanElement>) => {
    if (reduceMotion) return;
    const rect = ref.current?.getBoundingClientRect();
    if (!rect) return;
    x.set((event.clientX - (rect.left + rect.width / 2)) * strength);
    y.set((event.clientY - (rect.top + rect.height / 2)) * strength);
  };

  const reset = () => {
    x.set(0);
    y.set(0);
  };

  return (
    <motion.span
      ref={ref}
      className={className}
      style={{ display: "inline-flex", transform, willChange: "transform" }}
      onPointerMove={reduceMotion ? undefined : handleMove}
      onPointerLeave={reduceMotion ? undefined : reset}
    >
      {children}
    </motion.span>
  );
}
