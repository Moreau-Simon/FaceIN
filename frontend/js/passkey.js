/**
 * FaceIn - Passkeys WebAuthn (attestation matérielle)
 *
 * - Association d'une passkey au compte : uniquement après une connexion FaceIN
 *   réussie (le JWT obtenu est exigé par l'API).
 * - Dès qu'un compte possède une passkey, l'API l'exige à chaque connexion :
 *   le navigateur signe le challenge dérivé du nonce de session, après
 *   vérification de l'utilisateur par l'appareil (Windows Hello, Face ID…).
 * - Aucune image ni aucun vecteur facial n'est transmis : seule la signature
 *   de l'authentificateur quitte l'appareil.
 */
class PasskeyManager {
  constructor() {
    this.PREFIXE_STOCKAGE = "facein.passkey.";
  }

  /** Le navigateur prend-il en charge WebAuthn ? */
  estDisponible() {
    return (
      typeof window.PublicKeyCredential !== "undefined" &&
      !!navigator.credentials
    );
  }

  /** Une passkey a-t-elle été associée à ce compte depuis cet appareil ? */
  aUnePasskey(userId) {
    try {
      return localStorage.getItem(this.PREFIXE_STOCKAGE + userId) === "1";
    } catch (e) {
      return false;
    }
  }

  _memoriser(userId) {
    try {
      localStorage.setItem(this.PREFIXE_STOCKAGE + userId, "1");
    } catch (e) {
      /* stockage indisponible : la passkey sera demandée après un refus serveur */
    }
  }

  // --- Encodage base64url <-> ArrayBuffer ---
  _versBuffer(b64url) {
    const b64 = b64url.replace(/-/g, "+").replace(/_/g, "/");
    const bin = atob(b64 + "=".repeat((4 - (b64.length % 4)) % 4));
    const octets = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) octets[i] = bin.charCodeAt(i);
    return octets.buffer;
  }

  _versB64url(buffer) {
    const octets = new Uint8Array(buffer);
    let bin = "";
    for (let i = 0; i < octets.length; i++) bin += String.fromCharCode(octets[i]);
    return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  /**
   * Signe le challenge de session (paramètres `webauthn` renvoyés par /api/nonce).
   * @returns {Promise<Object>} Assertion JSON attendue par /api/authenticate
   */
  async obtenirAssertion(parametres) {
    if (!this.estDisponible()) {
      throw new Error("Ce navigateur ne prend pas en charge les passkeys (WebAuthn).");
    }
    const credential = await navigator.credentials.get({
      publicKey: {
        challenge: this._versBuffer(parametres.challenge),
        rpId: parametres.rpId,
        timeout: parametres.timeout,
        userVerification: parametres.userVerification || "required",
        allowCredentials: [], // passkeys découvrables : aucune liste exposée par le serveur
      },
    });
    if (!credential) throw new Error("Vérification par passkey annulée.");
    const r = credential.response;
    return {
      id: credential.id,
      rawId: this._versB64url(credential.rawId),
      type: credential.type,
      response: {
        clientDataJSON: this._versB64url(r.clientDataJSON),
        authenticatorData: this._versB64url(r.authenticatorData),
        signature: this._versB64url(r.signature),
        userHandle: r.userHandle ? this._versB64url(r.userHandle) : null,
      },
      clientExtensionResults: credential.getClientExtensionResults
        ? credential.getClientExtensionResults()
        : {},
    };
  }

  /**
   * Associe une passkey au compte (session FaceIN requise).
   * @param {string} userId
   * @param {string} jeton - JWT obtenu par une authentification FaceIN réussie
   */
  async enregistrer(userId, jeton) {
    if (!this.estDisponible()) {
      throw new Error("Ce navigateur ne prend pas en charge les passkeys (WebAuthn).");
    }
    const entetes = {
      "Content-Type": "application/json",
      Authorization: `Bearer ${jeton}`,
    };
    const base = window.CONFIG.API_BASE_URL;

    const repOptions = await fetch(`${base}/webauthn/register/options`, {
      method: "POST",
      headers: entetes,
      body: JSON.stringify({ user_id: userId }),
    });
    const demande = await repOptions.json();
    if (!repOptions.ok) {
      throw new Error(demande.message || demande.detail || `Erreur HTTP ${repOptions.status}`);
    }

    const o = demande.options;
    const credential = await navigator.credentials.create({
      publicKey: {
        ...o,
        challenge: this._versBuffer(o.challenge),
        user: { ...o.user, id: this._versBuffer(o.user.id) },
        excludeCredentials: (o.excludeCredentials || []).map((c) => ({
          ...c,
          id: this._versBuffer(c.id),
        })),
      },
    });
    if (!credential) throw new Error("Création de la passkey annulée.");

    const r = credential.response;
    const repVerif = await fetch(`${base}/webauthn/register/verify`, {
      method: "POST",
      headers: entetes,
      body: JSON.stringify({
        user_id: userId,
        challenge: demande.challenge,
        expires_at: demande.expires_at,
        jeton: demande.jeton,
        credential: {
          id: credential.id,
          rawId: this._versB64url(credential.rawId),
          type: credential.type,
          response: {
            clientDataJSON: this._versB64url(r.clientDataJSON),
            attestationObject: this._versB64url(r.attestationObject),
            transports: r.getTransports ? r.getTransports() : [],
          },
          clientExtensionResults: credential.getClientExtensionResults
            ? credential.getClientExtensionResults()
            : {},
        },
      }),
    });
    const resultat = await repVerif.json();
    if (!repVerif.ok) {
      throw new Error(resultat.message || resultat.detail || `Erreur HTTP ${repVerif.status}`);
    }
    this._memoriser(userId);
    return resultat;
  }
}

window.PasskeyManager = new PasskeyManager();
