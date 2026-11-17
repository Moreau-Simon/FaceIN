import { useReducedMotion } from "motion/react";
import { motion } from "motion/react";
import type { ElementType } from "react";

type BlurTextProps = {
  text: string;
  as?: ElementType;
  className?: string;
  /** Décalage initial (s) avant la première apparition. */
  delay?: number;
  /** Écart entre deux mots (s). */
  stagger?: number;
};

/**
 * Titre animé « blur → net » mot par mot (inspiré de BlurText, react-bits, licence MIT + Commons Clause).
 * Accessibilité : le texte original est exposé via aria-label, les mots animés sont masqués.
 * prefers-reduced-motion : rendu statique sans animation.
 */
export function BlurText({ text, as: Tag = "p", className, delay = 0, stagger = 0.045 }: BlurTextProps) {
  const reduceMotion = useReducedMotion();
  const words = text.split(" ");

  if (reduceMotion) {
    return <Tag className={className}>{text}</Tag>;
  }

  return (
    <Tag className={className} aria-label={text}>
      {words.map((word, index) => (
        <motion.span
          key={`${word}-${index}`}
          aria-hidden="true"
          style={{ display: "inline-block", willChange: "transform, filter" }}
          initial={{ opacity: 0, y: 12, filter: "blur(9px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ duration: 0.55, delay: delay + index * stagger, ease: [0.22, 1, 0.36, 1] }}
        >
          {word}
          {index < words.length - 1 ? "\u00A0" : ""}
        </motion.span>
      ))}
    </Tag>
  );
}
