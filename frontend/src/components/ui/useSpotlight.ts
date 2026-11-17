import { useEffect, useRef } from "react";
import type { RefObject } from "react";

/**
 * Projecteur « spotlight » sur une carte (inspiré de SpotlightCard, react-bits, licence MIT + Commons Clause) :
 * un dégradé radial suit le curseur via les variables CSS --spot-x / --spot-y.
 * Pur CSS côté rendu (aucune re-render React) ; sans pointeur (tactile), aucune var n'est posée.
 */
export function useSpotlight<T extends HTMLElement>(): RefObject<T | null> {
  const ref = useRef<T>(null);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const onPointerMove = (event: PointerEvent) => {
      const rect = element.getBoundingClientRect();
      element.style.setProperty("--spot-x", `${Math.round(event.clientX - rect.left)}px`);
      element.style.setProperty("--spot-y", `${Math.round(event.clientY - rect.top)}px`);
    };

    element.addEventListener("pointermove", onPointerMove, { passive: true });
    return () => element.removeEventListener("pointermove", onPointerMove);
  }, []);

  return ref;
}
