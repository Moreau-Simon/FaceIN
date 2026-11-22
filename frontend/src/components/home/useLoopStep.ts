import { useEffect, useRef, useState } from "react";
import { useInView, useReducedMotion } from "motion/react";

/** Fait avancer une séquence pas à pas tant que l'élément est visible, puis la rejoue. */
export function useLoopStep<T extends Element>(steps: number, interval = 520, hold = 3200) {
  const ref = useRef<T>(null);
  const inView = useInView(ref, { amount: 0.35 });
  const reduce = useReducedMotion();
  const [step, setStep] = useState(reduce ? steps : 0);

  useEffect(() => {
    if (reduce) { setStep(steps); return; }
    if (!inView) return;
    const timer = window.setTimeout(() => {
      setStep((value) => (value >= steps ? 0 : value + 1));
    }, step >= steps ? hold : step === 0 ? 500 : interval);
    return () => window.clearTimeout(timer);
  }, [inView, step, steps, interval, hold, reduce]);

  return { ref, step, replay: () => setStep(0) };
}
