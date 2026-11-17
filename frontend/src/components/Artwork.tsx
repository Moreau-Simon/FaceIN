import { useId } from "react";
import { motion, useReducedMotion } from "motion/react";

export function RibbonArtwork({ className = "" }: { className?: string }) {
  const gradientId = useId().replaceAll(":", "");
  const reduceMotion = useReducedMotion();

  return (
    <svg
      className={`ribbon-art ${className}`}
      viewBox="0 0 680 620"
      role="img"
      aria-label="Rubans de couleur illustrant le parcours de vérification FaceIN"
    >
      <defs>
        <linearGradient id={`${gradientId}-blue`} x1="0" y1="0" x2="1" y2="1">
          <stop stopColor="#c9e6ff" />
          <stop offset=".42" stopColor="#a49bff" />
          <stop offset=".77" stopColor="#ed83df" />
          <stop offset="1" stopColor="#ffbfdc" />
        </linearGradient>
        <linearGradient id={`${gradientId}-sunset`} x1="0" y1="0" x2="1" y2="1">
          <stop stopColor="#ffd45c" />
          <stop offset=".48" stopColor="#ff8c43" />
          <stop offset="1" stopColor="#f65d9c" />
        </linearGradient>
        <linearGradient id={`${gradientId}-lilac`} x1="0" y1="0" x2="0" y2="1">
          <stop stopColor="#ff88b0" />
          <stop offset=".5" stopColor="#ffb452" />
          <stop offset="1" stopColor="#8666f5" />
        </linearGradient>
      </defs>
      <motion.path
        d="M0 0h362c72 156 157 290 215 421 36 81 39 145 22 199h-91c12-75 3-139-43-202C375 275 184 132 0 0Z"
        fill={`url(#${gradientId}-blue)`}
        initial={reduceMotion ? false : { opacity: 0.65, x: 16 }}
        animate={reduceMotion ? undefined : { opacity: 1, x: 0 }}
        transition={{ duration: 1.15, ease: [0.22, 1, 0.36, 1] }}
      />
      <motion.path
        d="M228 0h286c60 148 85 282 68 389-10 67-36 115-68 142-31-103-102-239-286-531Z"
        fill={`url(#${gradientId}-sunset)`}
        initial={reduceMotion ? false : { opacity: 0.65, x: 12 }}
        animate={reduceMotion ? undefined : { opacity: 1, x: 0 }}
        transition={{ duration: 1.05, delay: 0.08, ease: [0.22, 1, 0.36, 1] }}
      />
      <motion.path
        d="M470 0h152c59 168 58 349 13 493-22 70-32 113-23 127h-83c-10-66 16-136 38-218 36-135 16-272-97-402Z"
        fill={`url(#${gradientId}-lilac)`}
        initial={reduceMotion ? false : { opacity: 0.65, x: 8 }}
        animate={reduceMotion ? undefined : { opacity: 1, x: 0 }}
        transition={{ duration: 0.95, delay: 0.16, ease: [0.22, 1, 0.36, 1] }}
      />
      <path d="M347 10c109 154 188 298 215 440" fill="none" stroke="white" strokeOpacity=".65" />
      <path d="M438 4c82 145 137 280 156 399" fill="none" stroke="white" strokeOpacity=".55" />
      <path d="M564 12c57 158 70 312 39 438" fill="none" stroke="white" strokeOpacity=".42" />
    </svg>
  );
}

export function ProofRays() {
  const reduceMotion = useReducedMotion();
  const centerX = 400;
  const centerY = 250;
  const rays = Array.from({ length: 48 }, (_, index) => {
    const angle = (-158 + index * 2.5) * (Math.PI / 180);
    const length = 110 + ((index * 37) % 115);
    return {
      x: centerX + Math.cos(angle) * length,
      y: centerY + Math.sin(angle) * length,
      color: ["#8a72ff", "#d27cf1", "#ff8ab4", "#ffbd69"][index % 4],
    };
  });

  return (
    <svg
      className="proof-rays"
      viewBox="0 0 800 280"
      role="img"
      aria-label="Visualisation abstraite d'une preuve vérifiée par plusieurs nœuds"
    >
      <defs>
        <radialGradient id="ray-origin">
          <stop stopColor="#ffba52" />
          <stop offset=".18" stopColor="#f47ebc" stopOpacity=".6" />
          <stop offset="1" stopColor="#f7f5ff" stopOpacity="0" />
        </radialGradient>
      </defs>
      <ellipse cx={centerX} cy={centerY} rx="250" ry="155" fill="url(#ray-origin)" />
      {rays.map((ray, index) => (
        <motion.line
          key={index}
          x1={centerX}
          y1={centerY}
          x2={ray.x}
          y2={ray.y}
          stroke={ray.color}
          strokeOpacity=".42"
          strokeWidth="1.1"
          initial={reduceMotion ? false : { pathLength: 0, opacity: 0 }}
          whileInView={reduceMotion ? undefined : { pathLength: 1, opacity: 1 }}
          viewport={{ once: true, amount: 0.35 }}
          transition={{ duration: 0.55, delay: index * 0.008 }}
        />
      ))}
      <circle cx={centerX} cy={centerY} r="5" fill="#ff9c5e" />
    </svg>
  );
}

export function NetworkSphere() {
  const dots = Array.from({ length: 100 }, (_, index) => {
    const row = Math.floor(index / 10);
    const column = index % 10;
    const offset = row % 2 ? 5 : 0;
    const x = 25 + column * 10 + offset;
    const y = 16 + row * 8;
    const distance = Math.hypot(x - 70, y - 53);
    return { x, y, opacity: Math.max(0.18, 1 - distance / 80) };
  });

  return (
    <svg className="network-sphere" viewBox="0 0 150 110" aria-hidden="true">
      {dots.map((dot, index) => (
        <circle
          key={index}
          cx={dot.x}
          cy={dot.y}
          r="1.35"
          fill={index % 7 === 0 ? "#fd7c9f" : "#7868f6"}
          opacity={dot.opacity}
        />
      ))}
      <path d="m47 45 47 15-26 24-21-39Z" fill="none" stroke="#a79cff" strokeDasharray="2 3" />
      <circle cx="47" cy="45" r="5.5" fill="white" stroke="#6b5bff" strokeWidth="1.5" />
      <circle cx="94" cy="60" r="5.5" fill="white" stroke="#6b5bff" strokeWidth="1.5" />
      <circle cx="68" cy="84" r="5.5" fill="white" stroke="#6b5bff" strokeWidth="1.5" />
      <text x="47" y="47" textAnchor="middle" fontSize="5" fill="#5545df">A</text>
      <text x="94" y="62" textAnchor="middle" fontSize="5" fill="#5545df">B</text>
      <text x="68" y="86" textAnchor="middle" fontSize="5" fill="#5545df">C</text>
    </svg>
  );
}
