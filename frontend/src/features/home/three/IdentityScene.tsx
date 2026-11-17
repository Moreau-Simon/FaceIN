import { Canvas } from "@react-three/fiber";
import { useEffect, useRef, useState } from "react";
import type { RefObject } from "react";
import * as THREE from "three";
import { IdentityModel } from "./IdentityModel";

declare global {
  interface Window {
    __faceinIdentityInfo?: THREE.WebGLRenderer["info"];
  }
}

/** Suspend le canvas hors écran ou lorsque l'onglet n'est pas visible. */
function usePausedWhenHidden(hostRef: RefObject<HTMLDivElement | null>): boolean {
  const [paused, setPaused] = useState(() => typeof document !== "undefined" && document.hidden);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;

    let inView = false;
    let tabVisible = !document.hidden;
    const sync = () => setPaused(!inView || !tabVisible);
    const observer = new IntersectionObserver(
      (entries) => {
        inView = entries.some((entry) => entry.isIntersecting);
        sync();
      },
      { threshold: 0.02 },
    );
    const onVisibilityChange = () => {
      tabVisible = !document.hidden;
      sync();
    };

    observer.observe(host);
    document.addEventListener("visibilitychange", onVisibilityChange);
    sync();

    return () => {
      observer.disconnect();
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [hostRef]);

  return paused;
}

export default function IdentityScene({
  maxDpr,
  reducedMotion,
}: {
  maxDpr: number;
  reducedMotion: boolean;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const paused = usePausedWhenHidden(hostRef);

  return (
    <div ref={hostRef} className="identity-3d__canvas">
      <Canvas
        aria-hidden="true"
        frameloop={paused ? "never" : reducedMotion ? "demand" : "always"}
        dpr={[1, maxDpr]}
        flat
        camera={{ fov: 38, near: 0.1, far: 40, position: [0, 0, 5.8] }}
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
        onCreated={({ gl }) => {
          if (import.meta.env.DEV) window.__faceinIdentityInfo = gl.info;
        }}
      >
        <ambientLight intensity={1.05} />
        <directionalLight position={[3.5, 4.5, 5]} intensity={2.2} color="#fff9ff" />
        <pointLight position={[-3, -1.5, 2.5]} intensity={18} distance={8} color="#9b7bff" />
        <pointLight position={[2.5, 2, -1]} intensity={12} distance={7} color="#ffad75" />
        <IdentityModel reducedMotion={reducedMotion} />
      </Canvas>
    </div>
  );
}
