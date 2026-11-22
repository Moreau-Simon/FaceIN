import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { RibbonArtwork } from "../components/Artwork";
import { FaceScanner, type MeshFrameRef, type ScannerState } from "../components/auth/FaceScanner";
import { closeCamera, describeCameraError, loadFaceModels, openCamera } from "../lib/facein/camera";
import { FACEIN_SPACE, getPartnerContext, recordConnection } from "../lib/facein/connections";
import { authenticateFlow, registerFlow, validateUserId, type FlowStep } from "../lib/facein/flows";
import { createSession } from "../lib/facein/session";
import { warmUpZkp } from "../lib/facein/zkp";

type Mode = "register" | "login";
type Stage = "form" | "scan" | "done";
type LogEntry = { id: number; time: string; message: string; level: "info" | "success" | "warn" | "error" };

const STEP_LABELS: Record<FlowStep, string> = {
  capture: "Lecture de votre visage…",
  "vault-save": "Enregistrement dans le coffre de cet appareil…",
  commitment: "Calcul de votre empreinte cryptographique…",
  register: "Création de votre identité FaceIN…",
  "vault-read": "Ouverture du coffre de cet appareil…",
  nonce: "Réception du défi de sécurité…",
  liveness: "Préparation du test de présence…",
  proof: "Génération de la preuve, quelques secondes…",
  verify: "Vérification par le réseau FaceIN…",
};

const STEP_PROGRESS: Record<Mode, Partial<Record<FlowStep, number>>> = {
  register: { capture: 20, "vault-save": 45, commitment: 70, register: 90 },
  login: { "vault-read": 5, nonce: 12, liveness: 18, capture: 70, proof: 82, verify: 92 },
};

const VERIFICATION_STEPS: FlowStep[] = ["liveness", "capture", "proof", "verify"];

function initialMode(): Mode {
  const mode = new URLSearchParams(window.location.search).get("mode");
  if (mode === "login" || mode === "auth" || window.location.hash === "#login") return "login";
  return "register";
}

export function ConnectionPage() {
  const reduce = useReducedMotion();
  const [mode, setMode] = useState<Mode>(initialMode);
  const [stage, setStage] = useState<Stage>("form");
  const [userId, setUserId] = useState("");
  const [consent, setConsent] = useState(false);
  const [formError, setFormError] = useState("");
  const [scanner, setScanner] = useState<ScannerState>({ kind: "off" });
  const [progress, setProgress] = useState(0);
  const [flowError, setFlowError] = useState("");
  const [notice, setNotice] = useState("");
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [running, setRunning] = useState(false);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [videoEl, setVideoEl] = useState<HTMLVideoElement | null>(null);
  const attachVideo = useCallback((element: HTMLVideoElement | null) => {
    videoRef.current = element;
    setVideoEl(element);
  }, []);
  const streamRef = useRef<MediaStream | null>(null);
  const frameRef: MeshFrameRef = useRef({ frame: null, at: 0 });
  const abortRef = useRef<AbortController | null>(null);
  const cameraRequest = useRef(0);
  const partner = useRef(getPartnerContext()).current;
  const fromPartner = partner !== FACEIN_SPACE;

  function log(message: string, level: LogEntry["level"] = "info") {
    setLogs((entries) => [
      ...entries.slice(-80),
      { id: Date.now() + Math.random(), time: new Date().toLocaleTimeString("fr-FR"), message, level },
    ]);
  }

  function stopCamera() {
    cameraRequest.current += 1;
    abortRef.current?.abort();
    abortRef.current = null;
    closeCamera(streamRef.current, videoRef.current);
    streamRef.current = null;
    frameRef.current = { frame: null, at: 0 };
  }

  useEffect(() => () => stopCamera(), []);

  // La caméra démarre dès que l'élément vidéo de l'étape « Visage » est monté.
  useEffect(() => {
    if (stage === "scan" && videoEl && scanner.kind === "off") void startCamera();
  }, [stage, videoEl, scanner.kind]);

  useEffect(() => {
    const onHash = () => {
      if (window.location.hash === "#login" || window.location.hash === "#register") {
        switchMode(window.location.hash === "#login" ? "login" : "register");
      }
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  });

  async function startCamera() {
    const request = ++cameraRequest.current;
    setScanner({ kind: "starting" });
    setFlowError("");
    try {
      const video = videoRef.current;
      if (!video) throw new Error("L’aperçu caméra n’est pas prêt.");
      const stream = await openCamera(video);
      if (request !== cameraRequest.current) {
        closeCamera(stream, null);
        return;
      }
      streamRef.current = stream;
      log("Caméra active. L’image reste dans ce navigateur.", "success");
      setScanner({ kind: "processing", label: "Chargement des modèles de reconnaissance…" });
      await Promise.all([loadFaceModels(), warmUpZkp()]);
      if (request !== cameraRequest.current) return;
      log("Modèles de reconnaissance et moteur cryptographique prêts.", "success");
      setScanner({ kind: "ready" });
    } catch (error) {
      if (request !== cameraRequest.current) return;
      const isCamera = !streamRef.current;
      const message = isCamera ? describeCameraError(error) : error instanceof Error ? error.message : "Initialisation impossible.";
      log(message, "error");
      setScanner({ kind: "error", message, camera: isCamera });
      if (!isCamera) setFlowError(message);
    }
  }

  function switchMode(next: Mode) {
    if (running) return;
    stopCamera();
    setMode(next);
    setStage("form");
    setScanner({ kind: "off" });
    setProgress(0);
    setFormError("");
    setFlowError("");
    setNotice("");
    history.replaceState(null, "", `${window.location.pathname}${window.location.search}#${next}`);
  }

  function submitForm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const problem = validateUserId(userId);
    if (problem) {
      setFormError(problem);
      return;
    }
    if (mode === "register" && !consent) {
      setFormError("Acceptez les conditions pour continuer.");
      return;
    }
    setFormError("");
    setScanner({ kind: "off" });
    setProgress(0);
    setStage("scan");
  }

  function goBack() {
    if (running) return;
    stopCamera();
    setStage("form");
    setScanner({ kind: "off" });
    setFlowError("");
  }

  async function run() {
    const video = videoRef.current;
    if (!video || running) return;
    const controller = new AbortController();
    abortRef.current = controller;
    setRunning(true);
    setFlowError("");
    setProgress(0);
    let lastStep: FlowStep | null = null;
    const id = userId.trim();

    const handlers = {
      signal: controller.signal,
      onLog: log,
      onStep: (step: FlowStep) => {
        lastStep = step;
        const value = STEP_PROGRESS[mode][step];
        if (value !== undefined) setProgress(value);
        if (step !== "liveness") setScanner({ kind: "processing", label: STEP_LABELS[step] });
      },
      onCalibrating: () => setScanner({ kind: "calibrating" }),
      onChallenge: (challenge: Parameters<NonNullable<Parameters<typeof authenticateFlow>[2]["onChallenge"]>>[0], index: number, total: number) => {
        setScanner({ kind: "challenge", challenge, index, total });
        setProgress(20 + (index / total) * 45);
      },
      onChallengeDone: (_challenge: unknown, index: number, total: number) => setProgress(20 + ((index + 1) / total) * 45),
      onFrame: (detection: Parameters<NonNullable<Parameters<typeof authenticateFlow>[2]["onFrame"]>>[0]) => {
        if (!detection) return;
        frameRef.current = {
          frame: { points: detection.landmarks.positions, videoWidth: video.videoWidth || 640, videoHeight: video.videoHeight || 480 },
          at: performance.now(),
        };
      },
    };

    try {
      if (mode === "register") {
        await registerFlow(id, video, handlers);
        setProgress(100);
        setScanner({ kind: "success", label: "Votre visage est enregistré" });
        window.setTimeout(() => {
          stopCamera();
          setStage("done");
        }, reduce ? 300 : 1500);
        return;
      }

      const token = await authenticateFlow(id, video, handlers);
      const session = createSession(id, token);
      recordConnection({
        userId: id,
        partnerName: partner.name,
        partnerOrigin: partner.origin,
        startedAt: Date.now(),
        expiresAt: session.expiresAt,
      });
      setProgress(100);
      setScanner({ kind: "success", label: "Identité vérifiée" });

      if (window.opener && !window.opener.closed && fromPartner) {
        window.opener.postMessage({ type: "FACEIN_AUTH_SUCCESS", token, user_id: id }, partner.origin.startsWith("http") ? partner.origin : "*");
        setNotice(`Connexion transmise à ${partner.name}. Cette fenêtre va se fermer.`);
        window.setTimeout(() => window.close(), 1500);
      } else {
        window.setTimeout(() => window.location.assign("espace.html"), reduce ? 300 : 1600);
      }
    } catch (error) {
      if (controller.signal.aborted) return;
      const message = error instanceof Error ? error.message : "Une erreur inattendue est survenue.";
      log(message, "error");
      setFlowError(message);
      setScanner({ kind: "ready" });
      setProgress(0);
      if (mode === "login" && lastStep && VERIFICATION_STEPS.includes(lastStep)) {
        recordConnection({
          userId: id,
          partnerName: partner.name,
          partnerOrigin: partner.origin,
          startedAt: Date.now(),
          expiresAt: Date.now(),
          refused: true,
          reason: message,
        });
      }
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
      setRunning(false);
    }
  }

  const canRun = scanner.kind === "ready" && !running;
  const steps = mode === "register" ? ["Pseudo", "Visage", "Terminé"] : ["Pseudo", "Vérification"];
  const currentStep = stage === "form" ? 0 : stage === "scan" ? 1 : 2;

  return (
    <div className="auth-page">
      <RibbonArtwork className="auth-page__ribbons" />
      <div className="auth-page__inner">
        <section className="auth-intro">
          {fromPartner ? (
            <p className="auth-intro__partner">
              <span className="status-dot" aria-hidden="true" /> {partner.name} vous demande de vous identifier
            </p>
          ) : (
            <p className="lead-label">Espace client</p>
          )}
          <h1>{mode === "register" ? "Créez votre identité en une minute." : "Connectez‑vous d’un regard."}</h1>
          <p className="auth-intro__lead">
            {mode === "register"
              ? "Un pseudo et votre visage suffisent. Pas d’e-mail, pas de mot de passe."
              : "Votre visage est comparé sur cet appareil. Seule une preuve mathématique est envoyée."}
          </p>
          <ul className="auth-assurances">
            <li><b>0</b><span>image envoyée : la caméra est traitée dans votre navigateur</span></li>
            <li><b>128</b><span>valeurs décrivent votre visage, gardées dans le coffre de cet appareil</span></li>
            <li><b>2 sur 3</b><span>serveurs indépendants doivent valider la preuve</span></li>
          </ul>
        </section>

        <section className="auth-card" aria-label={mode === "register" ? "Créer un compte" : "Se connecter"}>
          <div className="segmented" role="tablist" aria-label="Choisir un parcours">
            {(["register", "login"] as Mode[]).map((value) => (
              <button
                key={value}
                id={value}
                role="tab"
                type="button"
                aria-selected={mode === value}
                className={mode === value ? "is-active" : ""}
                disabled={running}
                onClick={() => switchMode(value)}
              >
                {mode === value && <motion.span layoutId="segmented-pill" className="segmented__pill" transition={{ type: "spring", stiffness: 420, damping: 34 }} />}
                <span>{value === "register" ? "Créer un compte" : "Se connecter"}</span>
              </button>
            ))}
          </div>

          <ol className="stepper" aria-label="Étapes">
            {steps.map((label, index) => (
              <li key={label} className={index < currentStep ? "is-done" : index === currentStep ? "is-current" : ""} aria-current={index === currentStep ? "step" : undefined}>
                <span>{index < currentStep ? "✓" : index + 1}</span>{label}
              </li>
            ))}
          </ol>

          <AnimatePresence mode="wait" initial={false}>
            {stage === "form" && (
              <motion.form
                key={`form-${mode}`}
                className="auth-form"
                onSubmit={submitForm}
                noValidate
                initial={{ opacity: 0, x: reduce ? 0 : 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: reduce ? 0 : -16 }}
                transition={{ duration: 0.22 }}
              >
                <h2>{mode === "register" ? "Choisissez votre pseudo" : "Quel est votre pseudo ?"}</h2>
                <p className="auth-form__hint">
                  {mode === "register"
                    ? "Il vous identifie auprès des sites partenaires. Vous ne pourrez pas le modifier."
                    : "Celui que vous avez choisi en créant votre compte sur cet appareil."}
                </p>
                <label className="field">
                  <span>Pseudo</span>
                  <input
                    name="username"
                    type="text"
                    autoComplete="username"
                    autoCapitalize="none"
                    spellCheck={false}
                    placeholder="ex. manon_m"
                    value={userId}
                    aria-invalid={Boolean(formError) && !validateUserId(userId) === false}
                    aria-describedby="username-help"
                    onChange={(event) => setUserId(event.target.value)}
                  />
                  <small id="username-help">3 à 24 caractères : lettres, chiffres, tiret ou tiret bas.</small>
                </label>
                {mode === "register" && (
                  <label className="checkbox">
                    <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} />
                    <span>J’accepte les <a href="index.html#legal-notice">conditions générales</a> et la <a href="comment-ca-marche.html#privacy">politique de confidentialité</a>.</span>
                  </label>
                )}
                {formError && <p className="form-error" role="alert">{formError}</p>}
                <button className="button button-primary button-full" type="submit">
                  Continuer <span className="button-arrow" aria-hidden="true" />
                </button>
                {mode === "login" && (
                  <p className="auth-form__switch">
                    Pas encore de compte ? <button type="button" className="text-button" onClick={() => switchMode("register")}>Créer un compte</button>
                  </p>
                )}
              </motion.form>
            )}

            {stage === "scan" && (
              <motion.div
                key={`scan-${mode}`}
                className="auth-scan"
                initial={{ opacity: 0, x: reduce ? 0 : 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: reduce ? 0 : -16 }}
                transition={{ duration: 0.22 }}
              >
                <div className="auth-scan__head">
                  <button type="button" className="text-button" onClick={goBack} disabled={running}>‹ Modifier le pseudo</button>
                  <span className="auth-scan__user">{userId.trim()}</span>
                </div>
                <FaceScanner
                  videoRef={attachVideo}
                  frameRef={frameRef}
                  state={scanner}
                  progress={progress}
                  idleTitle={mode === "register" ? "Placez votre visage dans le cercle" : "Prêt pour la vérification"}
                  onRetryCamera={() => void startCamera()}
                />
                <p className="auth-scan__privacy">
                  {mode === "register"
                    ? "Bonne lumière, visage dégagé. L’image ne quitte pas cet appareil et n’est jamais enregistrée."
                    : "Suivez les consignes à l’écran. Elles prouvent qu’une personne réelle est devant la caméra."}
                </p>
                {flowError && (
                  <div className="callout callout--error" role="alert">
                    <strong>{mode === "register" ? "Inscription interrompue" : "Connexion refusée"}</strong>
                    <p>{flowError}</p>
                  </div>
                )}
                {notice && <p className="callout callout--info" role="status">{notice}</p>}
                {scanner.kind !== "success" && (
                  <button className="button button-primary button-full" type="button" disabled={!canRun} onClick={() => void run()}>
                    {running
                      ? "Vérification en cours…"
                      : flowError
                        ? "Réessayer"
                        : mode === "register" ? "Enregistrer mon visage" : "Me connecter avec mon visage"}
                  </button>
                )}
                {mode === "login" && (
                  <p className="auth-form__switch">
                    Appareil perdu ? <button type="button" className="text-button" onClick={() => setNotice("La révocation à distance n’est pas encore disponible. Contactez l’équipe FaceIN pour désactiver votre identité.")}>Révoquer mon identité</button>
                  </p>
                )}
                <details className="tech-log">
                  <summary>Journal technique <span>{logs.length}</span></summary>
                  <ol>
                    {logs.length === 0 && <li className="is-empty">Aucun évènement pour l’instant.</li>}
                    {logs.map((entry) => (
                      <li key={entry.id} className={`is-${entry.level}`}><time>{entry.time}</time>{entry.message}</li>
                    ))}
                  </ol>
                </details>
              </motion.div>
            )}

            {stage === "done" && (
              <motion.div
                key="done"
                className="auth-done"
                initial={{ opacity: 0, scale: reduce ? 1 : 0.97 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.3 }}
              >
                <span className="auth-done__badge" aria-hidden="true">✓</span>
                <h2>Votre identité est prête.</h2>
                <p>Votre visage est enregistré sur cet appareil sous le pseudo <b>{userId.trim()}</b>. Vous pouvez maintenant vous connecter à votre espace et aux sites partenaires.</p>
                <button className="button button-primary button-full" type="button" onClick={() => switchMode("login")}>
                  Se connecter maintenant <span className="button-arrow" aria-hidden="true" />
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </section>
      </div>
    </div>
  );
}
