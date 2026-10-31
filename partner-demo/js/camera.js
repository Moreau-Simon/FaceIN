/**
 * camera.js - Flux WebRTC : démarrage, erreurs, libération propre des tracks
 */
(() => {
  class CameraManager {
    constructor(video) {
      this.video = video;
      this.stream = null;
      this.token = 0; // invalide les démarrages devenus obsolètes (fermeture pendant l'autorisation)
      this.handlers = { ready: [], error: [] };
    }

    on(event, fn) { this.handlers[event].push(fn); }

    async start() {
      this.stop();
      const token = ++this.token;
      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          throw new Error("L'API WebRTC n'est pas disponible sur ce navigateur.");
        }
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 30 } }
        });
        if (token !== this.token) { stream.getTracks().forEach(t => t.stop()); return; }
        this.stream = stream;
        this.video.srcObject = stream;
        await this.video.play();
        if (token === this.token) this.handlers.ready.forEach(fn => fn());
      } catch (err) {
        if (token === this.token) this.handlers.error.forEach(fn => fn(err));
      }
    }

    stop() {
      this.token++;
      if (this.stream) this.stream.getTracks().forEach(t => t.stop());
      this.stream = null;
      this.video.srcObject = null;
    }
  }

  window.CameraManager = CameraManager;
})();
