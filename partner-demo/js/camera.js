/**
 * camera.js - Flux WebRTC : autorisation, erreurs explicites, libération propre des tracks
 */
(() => {
  const fail = (name, message) => Object.assign(new Error(message), { name });

  class CameraManager {
    constructor(video) {
      this.video = video;
      this.stream = null;
      this.token = 0; // invalide les démarrages devenus obsolètes (fermeture pendant l'autorisation)
      this.permStatus = null;
      this.handlers = { ready: [], error: [], waiting: [], granted: [] };
    }

    on(event, fn) { this.handlers[event].push(fn); }
    emit(event, data) { this.handlers[event].forEach(fn => fn(data)); }

    /** 'granted' | 'denied' | 'prompt' | 'unknown' (Safari/Firefox n'exposent pas toujours l'API) */
    async permissionState() {
      try {
        const status = await navigator.permissions.query({ name: 'camera' });
        if (this.permStatus !== status) {
          this.permStatus = status;
          // Si l'utilisateur débloque la caméra dans la barre d'adresse, on le signale
          status.onchange = () => { if (status.state === 'granted') this.emit('granted'); };
        }
        return status.state;
      } catch (_) {
        return 'unknown';
      }
    }

    async start() {
      this.stop();
      const token = ++this.token;
      let waitTimer = null;
      try {
        if (!window.isSecureContext) {
          throw fail('InsecureContext', 'Contexte non sécurisé : la webcam exige HTTPS ou http://localhost.');
        }
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          throw fail('NotSupportedError', "L'API WebRTC n'est pas disponible sur ce navigateur.");
        }

        // Si l'accès est déjà bloqué, le navigateur n'affichera PLUS la fenêtre d'autorisation :
        // inutile d'attendre, on explique comment le débloquer.
        const perm = await this.permissionState();
        if (token !== this.token) return;
        if (perm === 'denied') throw fail('NotAllowedError', 'blocked');

        // La fenêtre d'autorisation peut rester ignorée : on prévient l'utilisateur après 3,5 s.
        waitTimer = setTimeout(() => { if (token === this.token) this.emit('waiting'); }, 3500);

        let stream;
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            audio: false,
            video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 30 } }
          });
        } catch (err) {
          // Contraintes refusées par la caméra : nouvel essai sans contraintes
          if (err.name === 'OverconstrainedError' || err.name === 'NotFoundError') {
            stream = await navigator.mediaDevices.getUserMedia({ audio: false, video: true });
          } else {
            throw err;
          }
        }

        clearTimeout(waitTimer);
        if (token !== this.token) { stream.getTracks().forEach(t => t.stop()); return; }
        this.stream = stream;
        this.video.srcObject = stream;
        await this.video.play();
        if (token === this.token) this.emit('ready');
      } catch (err) {
        clearTimeout(waitTimer);
        if (token === this.token) this.emit('error', err);
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
