import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

type AuthTab = "register" | "login";
type StatusMessage = { kind: "info" | "error"; text: string };

export function ConnectionPage() {
  const [activeTab, setActiveTab] = useState<AuthTab>(
    window.location.hash === "#login" ? "login" : "register",
  );
  const [showCamera, setShowCamera] = useState(false);
  const [cameraActive, setCameraActive] = useState(false);
  const [registerUsername, setRegisterUsername] = useState("");
  const [loginUsername, setLoginUsername] = useState("");
  const [consent, setConsent] = useState(false);
  const [status, setStatus] = useState<StatusMessage | null>(null);
  const cameraRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const requestIdRef = useRef(0);

  useEffect(() => {
    return () => {
      requestIdRef.current += 1;
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  function stopCamera(message = "Caméra arrêtée.") {
    requestIdRef.current += 1;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (cameraRef.current) cameraRef.current.srcObject = null;
    setCameraActive(false);
    setStatus({ kind: "info", text: message });
  }

  async function startCamera() {
    if (!navigator.mediaDevices?.getUserMedia) {
      setStatus({
        kind: "error",
        text: "La caméra nécessite un navigateur compatible et une connexion sécurisée (HTTPS ou localhost).",
      });
      return;
    }

    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setStatus({ kind: "info", text: "Demande d’autorisation de la caméra…" });

    let pendingStream: MediaStream | null = null;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: "user" },
      });
      pendingStream = stream;

      if (requestIdRef.current !== requestId) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }

      streamRef.current = stream;
      if (!cameraRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        throw new Error("L’aperçu caméra n’est plus disponible.");
      }

      cameraRef.current.srcObject = stream;
      await cameraRef.current.play();
      if (requestIdRef.current !== requestId) return;
      setCameraActive(true);
      setStatus({
        kind: "info",
        text: "Aperçu actif dans ce navigateur. Aucune reconnaissance ni transmission n’est effectuée.",
      });
    } catch (error) {
      if (requestIdRef.current !== requestId) return;
      pendingStream?.getTracks().forEach((track) => track.stop());
      if (streamRef.current === pendingStream) streamRef.current = null;
      if (cameraRef.current?.srcObject === pendingStream) {
        cameraRef.current.srcObject = null;
      }
      setCameraActive(false);
      const reason =
        error instanceof Error ? error.message : "autorisation refusée ou caméra indisponible";
      setStatus({
        kind: "error",
        text: `Impossible d’activer la caméra : ${reason}. Vérifiez les autorisations du navigateur.`,
      });
    }
  }

  function selectTab(tab: AuthTab) {
    stopCamera("Aperçu caméra désactivé.");
    setActiveTab(tab);
    setShowCamera(false);
    setStatus(null);
  }

  function submitForm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!event.currentTarget.reportValidity()) return;
    setShowCamera(true);
    setStatus({
      kind: "info",
      text: "Étape de démonstration : aucun compte n’est créé et aucune authentification n’est envoyée.",
    });
  }

  return (
    <div className="connection-page">
      <section className="connection-intro">
        <p className="eyebrow">06 Créer un compte - Connexion</p>
        <h1>Votre identité, sous votre contrôle.</h1>
        <p>Pas d’e-mail, pas de mot de passe. Juste un pseudo.</p>
        <div className="connection-proof"><span>Image de visage reçue</span><strong>0</strong><span>Votre image ne quitte pas cet appareil.</span></div>
      </section>

      <section className="connection-card" aria-label="Parcours de connexion FaceIN">
        <div className="auth-tabs" role="group" aria-label="Choisir un parcours">
          <button
            className={`auth-tab${activeTab === "register" ? " is-active" : ""}`}
            type="button"
            id="register"
            aria-pressed={activeTab === "register"}
            onClick={() => selectTab("register")}
          >
            Créer un compte
          </button>
          <button
            className={`auth-tab${activeTab === "login" ? " is-active" : ""}`}
            type="button"
            id="login"
            aria-pressed={activeTab === "login"}
            onClick={() => selectTab("login")}
          >
            Se connecter
          </button>
        </div>

        {activeTab === "register" ? (
          <section id="register-panel" aria-label="Créer un compte">
            <ol className="step-indicator" aria-label="Étapes de création">
              <li className={!showCamera ? "is-current" : "is-complete"}><span>1</span>Pseudo</li>
              <li className={showCamera ? "is-current" : ""}><span>2</span>Visage</li>
              <li><span>3</span>Terminé</li>
            </ol>
            <h2>Créer votre compte</h2>
            <p className="auth-description">Pas d’e-mail, pas de mot de passe. Juste un pseudo.</p>
            {!showCamera && (
              <form className="auth-form" onSubmit={submitForm}>
                <label htmlFor="register-username">Pseudo</label>
                <input
                  id="register-username"
                  name="username"
                  type="text"
                  autoComplete="username"
                  minLength={3}
                  maxLength={24}
                  pattern="[A-Za-z0-9_\-]+"
                  placeholder="ex. manon_m"
                  value={registerUsername}
                  onChange={(event) => setRegisterUsername(event.target.value)}
                  required
                  aria-describedby="username-help"
                />
                <small id="username-help">3 à 24 caractères : lettres, chiffres, tiret ou souligné.</small>
                <label className="consent-label">
                  <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} required />
                  <span>J’accepte les <a href="index.html#legal-notice">CGV</a> et la <a href="comment-ca-marche.html#privacy">politique de confidentialité</a>.</span>
                </label>
                <button className="button button-primary button-full" type="submit">Continuer <span aria-hidden="true">→</span></button>
              </form>
            )}
            {showCamera && (
              <div className="camera-demo">
                <h3>Placez votre visage dans le cadre</h3>
                <p>Bonne lumière, visage dégagé.</p>
                <div className={`camera-frame${cameraActive ? " is-active" : ""}`}>
                  <video ref={cameraRef} autoPlay muted playsInline aria-label="Aperçu local de la caméra" />
                  {!cameraActive && <span className="camera-placeholder">Aperçu caméra désactivé</span>}
                </div>
                <p className="privacy-callout">L’image ne quitte pas votre appareil. Elle est supprimée après le calcul.</p>
                <p className="prototype-note">Dans cette maquette, aucun calcul n’a lieu et aucune image n’est envoyée ou enregistrée.</p>
                <div className="button-row">
                  {!cameraActive ? (
                    <button className="button button-primary" type="button" onClick={startCamera}>Activer l’aperçu caméra</button>
                  ) : (
                    <button className="button button-outline" type="button" onClick={() => stopCamera()}>Arrêter la caméra</button>
                  )}
                  <button
                    className="button button-secondary"
                    type="button"
                    onClick={() => stopCamera("Aucune inscription réelle n’est effectuée dans cette démonstration.")}
                  >
                    Enregistrer mon visage
                  </button>
                </div>
              </div>
            )}
          </section>
        ) : (
          <section id="login-panel" aria-label="Se connecter">
            <h2>Se connecter</h2>
            <p className="auth-description">Saisissez votre pseudo, puis regardez la caméra.</p>
            {!showCamera && (
              <form className="auth-form" onSubmit={submitForm}>
                <label htmlFor="login-username">Pseudo</label>
                <input
                  id="login-username"
                  name="username"
                  type="text"
                  autoComplete="username"
                  minLength={3}
                  maxLength={24}
                  pattern="[A-Za-z0-9_\-]+"
                  placeholder="ex. manon_m"
                  value={loginUsername}
                  onChange={(event) => setLoginUsername(event.target.value)}
                  required
                />
                <button className="button button-primary button-full" type="submit">Continuer <span aria-hidden="true">→</span></button>
              </form>
            )}
            {showCamera && (
              <div className="camera-demo">
                <h3>Se connecter avec mon visage</h3>
                <p>Placez votre visage dans le cadre et regardez la caméra.</p>
                <div className={`camera-frame${cameraActive ? " is-active" : ""}`}>
                  <video ref={cameraRef} autoPlay muted playsInline aria-label="Aperçu local de la caméra" />
                  {!cameraActive && <span className="camera-placeholder">Aperçu caméra désactivé</span>}
                </div>
                <p className="prototype-note">Cette page de démonstration n’effectue pas de reconnaissance biométrique.</p>
                <div className="button-row">
                  {!cameraActive ? (
                    <button className="button button-primary" type="button" onClick={startCamera}>Activer l’aperçu</button>
                  ) : (
                    <button className="button button-outline" type="button" onClick={() => stopCamera()}>Arrêter la caméra</button>
                  )}
                  <button
                    className="button button-secondary"
                    type="button"
                    onClick={() => setStatus({ kind: "info", text: "Aucune connexion réelle n’est effectuée dans cette démonstration." })}
                  >
                    Se connecter avec mon visage
                  </button>
                </div>
                <div className="sample-error">
                  <span className="sample-error__label">Exemple d’état de maquette</span>
                  <strong>Visage non reconnu</strong>
                  <p>Vérifiez l’éclairage et retirez ce qui couvre votre visage, puis réessayez.</p>
                  <button className="text-button" type="button" onClick={() => setStatus({ kind: "info", text: "Aucun contrôle biométrique n’est effectué dans cette maquette." })}>Réessayer</button>
                </div>
              </div>
            )}
            <div className="account-help">
              <button
                className="account-help__action"
                type="button"
                onClick={() => setStatus({ kind: "info", text: "La révocation n’est pas disponible dans cette maquette." })}
              >
                Appareil perdu ? <strong>Révoquer mon identité</strong>
              </button>
              <span>Pas encore de compte ? <button className="text-button" type="button" onClick={() => selectTab("register")}>Créer un compte</button></span>
              <div className="renewal-notice">
                <strong>Votre photo de référence expire dans 12 jours</strong>
                <p>Refaites votre inscription pour continuer à vous connecter.</p>
                <button className="text-button" type="button" onClick={() => selectTab("register")}>Renouveler maintenant</button>
              </div>
            </div>
          </section>
        )}

        {status && <p className={`auth-status auth-status--${status.kind}`} role="status" aria-live="polite">{status.text}</p>}
      </section>
      <p className="connection-footnote">FaceIN <span>© 2026 FaceIN</span></p>
    </div>
  );
}
