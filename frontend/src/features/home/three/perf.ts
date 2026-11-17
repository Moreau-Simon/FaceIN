/** Utilitaires d'environnement pour décider du rendu 3D. Reste léger : aucun import `three`. */

import { useSyncExternalStore } from "react";

const reducedMotionQuery = "(prefers-reduced-motion: reduce)";
const compactViewportQuery = "(max-width: 768px)";

function subscribeToMotionPreference(onChange: () => void) {
  if (typeof window === "undefined") return () => {};
  const mediaQuery = window.matchMedia(reducedMotionQuery);
  mediaQuery.addEventListener("change", onChange);
  return () => mediaQuery.removeEventListener("change", onChange);
}

function getMotionPreference() {
  return typeof window === "undefined" || window.matchMedia(reducedMotionQuery).matches;
}

function subscribeToViewportSize(onChange: () => void) {
  if (typeof window === "undefined") return () => {};
  const mediaQuery = window.matchMedia(compactViewportQuery);
  mediaQuery.addEventListener("change", onChange);
  return () => mediaQuery.removeEventListener("change", onChange);
}

function getMaxDeviceDpr() {
  if (typeof window === "undefined") return 1;
  return window.matchMedia(compactViewportQuery).matches ? 1.5 : 2;
}

/** Réagit aussi aux changements de préférence pendant la session. */
export function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(subscribeToMotionPreference, getMotionPreference, () => true);
}

/** Met à jour le plafond DPR lorsque le viewport change de catégorie. */
export function useMaxDeviceDpr(): number {
  return useSyncExternalStore(subscribeToViewportSize, getMaxDeviceDpr, () => 1);
}

/** `three` r187 exige WebGL2 : détecter avant de monter le Canvas. */
export function hasWebGL2(): boolean {
  if (typeof document === "undefined") return false;
  try {
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("webgl2");
    if (!context) return false;
    context.getExtension("WEBGL_lose_context")?.loseContext();
    return true;
  } catch {
    return false;
  }
}

