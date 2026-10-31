/**
 * face-tracking.js - Overlay LiDAR : tessellation fine + points nodaux pulsants.
 * MediaPipe Face Mesh si disponible, sinon maillage 3D simulé (CDN bloqué, caméra lente...).
 */
(() => {
  // Repères anatomiques (indices MediaPipe) : yeux, arête du nez, ailes, pommettes, lèvres, mâchoire
  const NODES = [
    33, 160, 158, 133, 153, 144, 362, 385, 387, 263, 373, 380,
    168, 6, 197, 195, 5, 4, 98, 327,
    50, 280, 205, 425,
    61, 291, 0, 17,
    58, 172, 136, 150, 176, 152, 400, 379, 365, 397, 288
  ];
  const TESS = () => window.FACEMESH_TESSELATION; // (sic) nom exporté par MediaPipe

  // ---- Maillage simulé : grille en forme de visage, projetée en perspective et pivotant lentement
  const ROWS = 15, COLS = 13;
  const halfW = v => 0.8 * Math.sqrt(1 - v * v) * (v > 0 ? 1 - 0.3 * v : 1);
  const depth = (u, v) => Math.sqrt(Math.max(0, 1 - u * u)) * (0.4 - 0.18 * Math.abs(v)) +
                          0.3 * Math.exp(-(u * u * 9 + (v - 0.12) ** 2 * 12));
  const point = (u, v) => ({ x: u * halfW(v), y: v * 0.95, z: depth(u, v), v });

  const GRID = [], EDGES = [];
  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS; c++) GRID.push(point(-1 + 2 * c / (COLS - 1), -0.97 + 1.94 * r / (ROWS - 1)));
  }
  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS; c++) {
      const i = r * COLS + c;
      if (c < COLS - 1) EDGES.push([i, i + 1]);
      if (r < ROWS - 1) {
        EDGES.push([i, i + COLS]);
        if (c < COLS - 1) EDGES.push([i, i + COLS + 1]);
      }
    }
  }
  const SYN_NODES = [
    [.5, -.28], [.36, -.33], [.36, -.23], [.22, -.28], [0, -.3], [0, -.1], [0, .08], [0, .2], [.15, .22],
    [.62, -.02], [.3, .5], [0, .46], [0, .58], [.55, .7], [.3, .88], [0, .95]
  ].flatMap(([u, v]) => (u ? [[u, v], [-u, v]] : [[0, v]])).map(([u, v]) => point(u, v));

  function project(p, W, H, t) {
    const yaw = 0.32 * Math.sin(t / 1100), cy = Math.cos(yaw), sy = Math.sin(yaw);
    const xr = p.x * cy + p.z * sy, zr = -p.x * sy + p.z * cy, k = 1 / (1 - zr * 0.35);
    return { x: W / 2 + xr * W * 0.40 * k, y: H / 2 + p.y * H * 0.38 * k, v: p.v };
  }

  class FaceTracker {
    constructor(canvas, video) {
      this.canvas = canvas;
      this.ctx = canvas.getContext('2d');
      this.video = video;
      this.running = false;
      this.landmarks = null;
      this.busy = false;
      this.last = 0;
      this.dpr = 1;
      this.onMetrics = null;
      this.loop = this.loop.bind(this);
      this.resize = this.resize.bind(this);
      this.fm = null;

      if (window.FaceMesh) {
        try {
          this.fm = new window.FaceMesh({
            locateFile: f => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh@0.4.1633559619/${f}`
          });
          this.fm.setOptions({ maxNumFaces: 1, refineLandmarks: true, minDetectionConfidence: 0.5, minTrackingConfidence: 0.5 });
          this.fm.onResults(r => this.onResults(r));
        } catch (e) {
          console.warn('[FaceTracker] MediaPipe indisponible, maillage simulé actif.', e);
          this.fm = null;
        }
      }
    }

    onResults(res) {
      this.landmarks = (res.multiFaceLandmarks && res.multiFaceLandmarks[0]) || null;
      if (this.landmarks) this.computeMetrics(this.landmarks);
    }

    /** yaw > 0 : l'utilisateur tourne la tête vers SA droite (vue miroir). */
    computeMetrics(p) {
      const nose = p[1], l = p[234], r = p[454];
      const dl = Math.abs(nose.x - l.x), dr = Math.abs(r.x - nose.x), total = dl + dr || 1;
      const yaw = ((dr - dl) / total) * 2.5;
      const mouth = Math.hypot(p[291].x - p[61].x, p[291].y - p[61].y);
      const smile = mouth / total;
      if (this.onMetrics) this.onMetrics({ yaw, smile });
    }

    start() {
      if (this.running) return;
      this.running = true;
      this.landmarks = null;
      this.resize();
      window.addEventListener('resize', this.resize);
      this.raf = requestAnimationFrame(this.loop);
    }

    stop() {
      this.running = false;
      cancelAnimationFrame(this.raf);
      window.removeEventListener('resize', this.resize);
      this.landmarks = null;
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }

    resize() {
      const w = this.canvas.clientWidth, h = this.canvas.clientHeight;
      if (!w || !h) return;
      this.dpr = Math.min(window.devicePixelRatio || 1, 2);
      this.canvas.width = Math.round(w * this.dpr);
      this.canvas.height = Math.round(h * this.dpr);
    }

    loop(ts) {
      if (!this.running) return;
      this.raf = requestAnimationFrame(this.loop);
      if (this.fm && !this.busy && this.video.readyState >= 2 && ts - this.last > 33) {
        this.busy = true;
        this.last = ts;
        this.fm.send({ image: this.video }).catch(() => {}).finally(() => { this.busy = false; });
      }
      this.draw(ts);
    }

    draw(t) {
      const { ctx, canvas, dpr } = this, W = canvas.width, H = canvas.height;
      ctx.clearRect(0, 0, W, H);

      let pts, edges, nodes;
      const tess = TESS();
      if (this.landmarks && tess) {
        // Mapping identique à object-fit: cover (le canvas est miroité en CSS comme la vidéo)
        const vw = this.video.videoWidth || 640, vh = this.video.videoHeight || 480;
        const s = Math.max(W / vw, H / vh), ox = (W - vw * s) / 2, oy = (H - vh * s) / 2;
        pts = this.landmarks.map(p => ({ x: p.x * vw * s + ox, y: p.y * vh * s + oy }));
        edges = tess;
        nodes = NODES.map(i => pts[i]).filter(Boolean).map(p => ({ x: p.x, y: p.y, v: p.y / H * 2 - 1 }));
      } else {
        pts = GRID.map(p => project(p, W, H, t));
        edges = EDGES;
        nodes = SYN_NODES.map(p => project(p, W, H, t));
      }

      ctx.strokeStyle = 'rgba(56, 189, 248, 0.18)';
      ctx.lineWidth = 0.6 * dpr;
      ctx.beginPath();
      for (const [a, b] of edges) {
        const p = pts[a], q = pts[b];
        if (!p || !q) continue;
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(q.x, q.y);
      }
      ctx.stroke();

      ctx.fillStyle = '#38BDF8';
      ctx.shadowColor = 'rgba(56, 189, 248, 0.9)';
      ctx.shadowBlur = 6 * dpr;
      for (const n of nodes) {
        const pulse = 0.5 + 0.5 * Math.sin(t / 380 + n.v * 5); // vague de pulsation qui balaie le visage
        ctx.globalAlpha = 0.55 + 0.45 * pulse;
        ctx.beginPath();
        ctx.arc(n.x, n.y, (1.1 + 0.9 * pulse) * dpr, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
      ctx.shadowBlur = 0;
    }
  }

  window.FaceTracker = FaceTracker;
})();
