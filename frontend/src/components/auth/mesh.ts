/**
 * Superposition « LiDAR » du médaillon caméra.
 * Maillage simulé repris de `partner-demo/js/face-tracking.js` ; les 68 repères face-api.js
 * remplacent le maillage dès qu'une détection réelle est disponible.
 */
import type { Point } from "../../lib/facein/vendor";

const ROWS = 15;
const COLS = 13;
type P3 = { x: number; y: number; z: number; v: number };

const halfW = (v: number) => 0.8 * Math.sqrt(1 - v * v) * (v > 0 ? 1 - 0.3 * v : 1);
const depth = (u: number, v: number) =>
  Math.sqrt(Math.max(0, 1 - u * u)) * (0.4 - 0.18 * Math.abs(v)) + 0.3 * Math.exp(-(u * u * 9 + (v - 0.12) ** 2 * 12));
const point = (u: number, v: number): P3 => ({ x: u * halfW(v), y: v * 0.95, z: depth(u, v), v });

const GRID: P3[] = [];
const EDGES: [number, number][] = [];
for (let r = 0; r < ROWS; r += 1) {
  for (let c = 0; c < COLS; c += 1) GRID.push(point(-1 + (2 * c) / (COLS - 1), -0.97 + (1.94 * r) / (ROWS - 1)));
}
for (let r = 0; r < ROWS; r += 1) {
  for (let c = 0; c < COLS; c += 1) {
    const i = r * COLS + c;
    if (c < COLS - 1) EDGES.push([i, i + 1]);
    if (r < ROWS - 1) {
      EDGES.push([i, i + COLS]);
      if (c < COLS - 1) EDGES.push([i, i + COLS + 1]);
    }
  }
}
const SYN_NODES: P3[] = [
  [0.5, -0.28], [0.36, -0.33], [0.36, -0.23], [0.22, -0.28], [0, -0.3], [0, -0.1], [0, 0.08], [0, 0.2], [0.15, 0.22],
  [0.62, -0.02], [0.3, 0.5], [0, 0.46], [0, 0.58], [0.55, 0.7], [0.3, 0.88], [0, 0.95],
].flatMap(([u, v]) => (u ? [[u, v], [-u, v]] : [[0, v]])).map(([u, v]) => point(u, v));

function project(p: P3, W: number, H: number, t: number) {
  const yaw = 0.32 * Math.sin(t / 1100);
  const cy = Math.cos(yaw);
  const sy = Math.sin(yaw);
  const xr = p.x * cy + p.z * sy;
  const zr = -p.x * sy + p.z * cy;
  const k = 1 / (1 - zr * 0.35);
  return { x: W / 2 + xr * W * 0.4 * k, y: H / 2 + p.y * H * 0.38 * k, v: p.v };
}

/** Groupes de repères face-api.js (0-16 mâchoire, 17-26 sourcils, 27-35 nez, 36-47 yeux, 48-67 bouche). */
const LANDMARK_PATHS: [number, number, boolean][] = [
  [0, 16, false], [17, 21, false], [22, 26, false], [27, 30, false], [31, 35, false],
  [36, 41, true], [42, 47, true], [48, 59, true], [60, 67, true],
];

export type MeshFrame = { points: Point[]; videoWidth: number; videoHeight: number } | null;

export function drawMesh(ctx: CanvasRenderingContext2D, W: number, H: number, dpr: number, t: number, frame: MeshFrame, tone: "scan" | "ok") {
  ctx.clearRect(0, 0, W, H);
  const lineColor = tone === "ok" ? "rgba(52, 245, 176, 0.3)" : "rgba(56, 189, 248, 0.2)";
  const nodeColor = tone === "ok" ? "#34F5B0" : "#38BDF8";
  let nodes: { x: number; y: number; v: number }[];

  ctx.lineWidth = 0.7 * dpr;
  ctx.strokeStyle = lineColor;
  ctx.beginPath();

  if (frame) {
    const s = Math.max(W / frame.videoWidth, H / frame.videoHeight);
    const ox = (W - frame.videoWidth * s) / 2;
    const oy = (H - frame.videoHeight * s) / 2;
    const pts = frame.points.map((p) => ({ x: p.x * s + ox, y: p.y * s + oy, v: (p.y * s + oy) / H * 2 - 1 }));
    for (const [from, to, closed] of LANDMARK_PATHS) {
      ctx.moveTo(pts[from].x, pts[from].y);
      for (let i = from + 1; i <= to; i += 1) ctx.lineTo(pts[i].x, pts[i].y);
      if (closed) ctx.lineTo(pts[from].x, pts[from].y);
    }
    nodes = pts;
  } else {
    const pts = GRID.map((p) => project(p, W, H, t));
    for (const [a, b] of EDGES) {
      ctx.moveTo(pts[a].x, pts[a].y);
      ctx.lineTo(pts[b].x, pts[b].y);
    }
    nodes = SYN_NODES.map((p) => project(p, W, H, t));
  }
  ctx.stroke();

  ctx.fillStyle = nodeColor;
  ctx.shadowColor = nodeColor;
  ctx.shadowBlur = 6 * dpr;
  for (const n of nodes) {
    const pulse = 0.5 + 0.5 * Math.sin(t / 380 + n.v * 5);
    ctx.globalAlpha = 0.55 + 0.45 * pulse;
    ctx.beginPath();
    ctx.arc(n.x, n.y, (1 + 0.8 * pulse) * dpr, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.globalAlpha = 1;
  ctx.shadowBlur = 0;
}
