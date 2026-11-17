/**
 * app.js - Orchestration : ouverture/fermeture de la modale et machine à états
 * États : IDLE -> STARTING -> SCANNING -> SUCCESS -> CLOSING -> IDLE   (ERROR depuis STARTING)
 */
document.addEventListener('DOMContentLoaded', () => {
  const $ = id => document.getElementById(id);
  const btnOpen = $('btn-open-facein'), modal = $('facein-modal');
  const box = modal.querySelector('.fi-modal'), backdrop = modal.querySelector('.fi-backdrop');
  const video = $('webcam-video'), canvas = $('lidar-canvas');
  const skeleton = $('camera-skeleton'), errorEl = $('camera-error'), errorDetail = $('camera-error-detail');
  const status = $('modal-status-text');

  const camera = new CameraManager(video);
  const tracker = new FaceTracker(canvas, video);
  const guide = new LivenessGuide({
    stage: $('fi-stage'), glyph: $('fi-glyph'), pill: $('fi-pill'), pillSlot: $('fi-pill-slot'),
    pillLabel: $('fi-pill-label'), video, canvas, wave: $('fi-wave'),
    ringBase: $('fi-ring-base'), ringLit: $('fi-ring-lit'),
    counterEl: $('liveness-step-counter'), titleEl: $('liveness-instruction-text'),
    onStepReached: () => serverValidation(true)
  });

  let state = 'IDLE';
  const sleep = ms => new Promise(r => setTimeout(r, ms));

  /** Réponse du serveur : `true` valide l'étape courante (bouton de simulation ou détection locale). */
  async function serverValidation(ok) {
    if (state !== 'SCANNING' || ok !== true) return;
    if (!guide.validateStep()) return;

    state = 'SUCCESS';
    status.textContent = 'Consensus 2/3 atteint • Signature ZKP';
    await guide.playSuccess();
    await sleep(600);
    closeModal();
    document.dispatchEvent(new CustomEvent('facein:authenticated', { detail: { user_id: 'demo_partner_user' } }));
  }

  function openModal() {
    if (state !== 'IDLE') return;
    state = 'STARTING';
    modal.classList.add('active');
    modal.setAttribute('aria-hidden', 'false');
    skeleton.classList.remove('hidden');
    errorEl.classList.add('hidden');
    video.classList.remove('active');
    status.textContent = 'Initialisation de la caméra…';

    gsap.fromTo(backdrop, { opacity: 0 }, { opacity: 1, duration: 0.3 });
    gsap.fromTo(box, { scale: 0.92, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.55, ease: 'back.out(1.4)' });

    guide.reset();
    tracker.start();   // le maillage simulé s'affiche dès l'ouverture, sans attendre la caméra
    camera.start();
    $('btn-close-modal').focus();
  }

  function closeModal() {
    if (state === 'IDLE' || state === 'CLOSING') return;
    state = 'CLOSING';
    guide.stop();
    tracker.stop();
    camera.stop();   // libère les tracks vidéo immédiatement
    video.classList.remove('active');

    gsap.to(box, { scale: 0.96, opacity: 0, duration: 0.25, ease: 'power2.in' });
    gsap.to(backdrop, {
      opacity: 0, duration: 0.25,
      onComplete: () => {
        modal.classList.remove('active');
        modal.setAttribute('aria-hidden', 'true');
        state = 'IDLE';
        btnOpen.focus();
      }
    });
  }

  camera.on('ready', () => {
    if (state !== 'STARTING') return;
    state = 'SCANNING';
    skeleton.classList.add('hidden');
    video.classList.add('active');
    status.textContent = 'Capteur actif • Analyse LiDAR en cours';
    guide.start();
  });

  const CAMERA_MESSAGES = {
    InsecureContext: "La webcam exige HTTPS ou http://localhost. Lancez la page via un serveur local (ex. « python -m http.server ») et non en file://.",
    NotAllowedError: "Accès à la caméra bloqué. Cliquez sur l'icône à gauche de la barre d'adresse, autorisez la caméra, puis cliquez sur Réessayer.",
    NotFoundError: "Aucune webcam détectée sur cet appareil.",
    NotReadableError: "La caméra est utilisée par une autre application (Teams, Zoom, OBS…) ou bloquée par le système. Fermez-la puis réessayez.",
    NotSupportedError: "Ce navigateur ne prend pas en charge l'accès à la webcam."
  };

  camera.on('waiting', () => {
    if (state === 'STARTING') status.textContent = "En attente de votre autorisation — cliquez sur « Autoriser » dans la fenêtre du navigateur";
  });

  camera.on('error', err => {
    if (state !== 'STARTING') return;
    state = 'ERROR';
    tracker.stop();
    skeleton.classList.add('hidden');
    errorEl.classList.remove('hidden');
    status.textContent = 'Erreur de périphérique';
    errorDetail.textContent = CAMERA_MESSAGES[err.name] || err.message || "Impossible d'accéder à la webcam.";
  });

  // L'utilisateur vient de débloquer la caméra dans la barre d'adresse : on relance seul
  camera.on('granted', () => { if (state === 'ERROR') retryCamera(); });

  function retryCamera() {
    state = 'STARTING';
    skeleton.classList.remove('hidden');
    errorEl.classList.add('hidden');
    status.textContent = 'Initialisation de la caméra…';
    tracker.start();
    camera.start();
  }

  tracker.onMetrics = m => { if (state === 'SCANNING') guide.processMetrics(m); };

  btnOpen.addEventListener('click', openModal);
  $('btn-close-modal').addEventListener('click', closeModal);
  backdrop.addEventListener('click', closeModal);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
  $('btn-simulate-step').addEventListener('click', () => serverValidation(true));
  $('btn-retry-camera').addEventListener('click', retryCamera);
});
