/**
 * FaceIn — Module de détection de vie (liveness anti-photo)
 *
 * Contre-mesure à l'attaque par présentation (photo/écran devant la caméra) :
 * le serveur impose une liste aléatoire de défis que l'utilisateur doit
 * exécuter devant la webcam. Une photo ne peut ni cligner ni tourner la tête.
 *
 * Ne nécessite aucun modèle supplémentaire : il réutilise les 68 landmarks
 * de face-api.js (faceLandmark68Net), déjà chargés par FaceCapture.
 *
 * Deux couches de défense :
 * 1. Défis actifs aléatoires imposés par le serveur (une photo ne peut pas
 *    cligner des yeux ni tourner la tête) ;
 * 2. Contrôle de continuité temporelle entre frames (empêche l'échange de
 *    plusieurs photos pendant un défi : un visage réel ne "téléporte" pas).
 */
class LivenessModule {
  constructor() {
    // --- Paramètres du test de vie (calibrables) ---
    this.DEBUG = true; // log des mesures dans la console (mettre false après calibrage)
    this.FPS = 10; // frames analysées par seconde
    this.DUREE_REFERENCE_MS = 1500; // calibration initiale (visage de face)
    this.DUREE_MAX_DEFI_MS = 10000; // délai accordé pour exécuter un défi
    this.SEUIL_EAR_CLIGNEMENT = 0.23; // ouverture des yeux en dessous = clignement
    this.SEUIL_ROTATION = 0.1; // écart du rapport nez/yeux vs position de face
    this.GAIN_SOURIRE = 1.08; // la bouche doit s'élargir de 8 %
    // Si le défi "tournez la tête à gauche" se valide quand vous tournez à droite,
    // inversez ce signe (dépend du mirroring de la webcam) :
    this.SENS_ROTATION = +1;

    // --- Continuité temporelle (anti-échange de photos pendant un défi) ---
    // Un visage réel bouge continûment : entre 2 frames espacées de 100 ms, le
    // centre du visage ne peut pas "téléporter" ni changer brusquement de taille.
    this.MAX_SAUT_CENTRE = 0.25; // déplacement max du centre entre 2 frames (× largeur du visage)
    this.MAX_SAUT_ECHELLE = 0.2; // variation max de la largeur du visage entre 2 frames

    // --- Catalogue des défis (les clés correspondent à nonce.py) ---
    this._DEFIS = {
      blink: {
        texte: "clignez des yeux",
        tester: (v, r, s) => s._testerBlink(v, r, s),
      },
      turn_left: {
        texte: "tournez la tête vers votre gauche",
        tester: (v, r, s) => s._testerTurn(v, r, s, -1),
      },
      turn_right: {
        texte: "tournez la tête vers votre droite",
        tester: (v, r, s) => s._testerTurn(v, r, s, +1),
      },
      smile: { texte: "souriez", tester: (v, r, s) => s._testerSmile(v, r, s) },
    };
  }

  /* ============== Mesures sur les 68 landmarks ============== */

  _d(a, b) {
    return Math.hypot(a.x - b.x, a.y - b.y);
  }

  // Rapport d'ouverture d'un œil (6 points). Ouvert ≈ 0.28-0.35, fermé < 0.20.
  _ear(eye) {
    const h = this._d(eye[1], eye[5]) + this._d(eye[2], eye[4]);
    const w = this._d(eye[0], eye[3]);
    return w > 0 ? h / (2 * w) : 0;
  }

  _earMoyen(lm) {
    return (this._ear(lm.getLeftEye()) + this._ear(lm.getRightEye())) / 2;
  }

  // Position latérale du bout du nez entre les coins extérieurs des yeux.
  // Visage de face ≈ 0.5 ; tourner la tête écarte cette valeur de 0.5.
  _ratioRotation(lm) {
    const coinGauche = lm.getLeftEye()[0];
    const coinDroit = lm.getRightEye()[3];
    const nez = lm.getNose()[6]; // bout du nez
    const largeur = coinDroit.x - coinGauche.x;
    return largeur !== 0 ? (nez.x - coinGauche.x) / largeur : 0.5;
  }

  // Largeur de la bouche relative à l'écartement des yeux (augmente en souriant).
  _ratioBouche(lm) {
    const bouche = lm.getMouth();
    const yeux = this._d(lm.getLeftEye()[0], lm.getRightEye()[3]);
    return yeux > 0 ? this._d(bouche[0], bouche[6]) / yeux : 0;
  }

  /* ============== Outils ============== */

  _attendre(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  // Détection avec landmarks (le résultat contient .landmarks ET .detection.box,
  // la boîte étant nécessaire au contrôle de continuité).
  async _detecter(video) {
    const options = new faceapi.SsdMobilenetv1Options({ minConfidence: 0.65 });
    return faceapi.detectSingleFace(video, options).withFaceLandmarks();
  }

  // Échantillonne des frames pendant dureeMs ; s'arrête dès que validateur(lm) renvoie true.
  // Contrôle AUSSI la continuité : un échange de photo devant la caméra produit un
  // "téléport" du visage (position et/ou taille) entre deux frames consécutives.
  async _framesPendant(video, dureeMs, validateur) {
    const pas = 1000 / this.FPS;
    const fin = Date.now() + dureeMs;
    let precedente = null;
    let discontinuites = 0;

    while (Date.now() < fin) {
      const t0 = Date.now();
      const res = await this._detecter(video);

      if (res) {
        if (!this._continuiteOk(res, precedente)) {
          discontinuites++;
          if (discontinuites >= 2) {
            throw new Error(
              "Mouvement du visage discontinu (échange de support devant la caméra ?). " +
                "Test de vie échoué.",
            );
          }
        } else {
          discontinuites = 0;
        }
        precedente = res;

        const valide = validateur(res.landmarks);
        if (this.DEBUG) {
          const lm = res.landmarks;
          console.log(
            "[Liveness] EAR=" +
              this._earMoyen(lm).toFixed(3) +
              " rot=" +
              this._ratioRotation(lm).toFixed(3) +
              " bouche=" +
              this._ratioBouche(lm).toFixed(3) +
              (valide ? " → VALIDÉ ✔" : ""),
          );
        }
        if (valide) return true;
      }
      // Attente adaptative : la détection prend déjà 100-300 ms,
      // on n'ajoute que le temps manquant pour viser un vrai this.FPS.
      // (Sans ça, l'échantillonnage réel tombe à ~3 fps → le clignement
      //  dure ~150 ms et est raté entre deux frames.)
      const ecoule = Date.now() - t0;
      if (ecoule < pas) await this._attendre(pas - ecoule);
    }
    return false;
  }

  // Le centre du visage doit rester dans un rayon de MAX_SAUT_CENTRE largeurs de
  // visage entre 2 frames consécutives, et sa taille ne doit pas varier brutalement.
  _continuiteOk(res, precedente) {
    if (!precedente) return true;
    const b = res.detection.box;
    const p = precedente.detection.box;
    const sautCentre =
      Math.hypot(
        b.x + b.width / 2 - (p.x + p.width / 2),
        b.y + b.height / 2 - (p.y + p.height / 2),
      ) / p.width;
    const sautEchelle = Math.abs(b.width - p.width) / p.width;
    return (
      sautCentre <= this.MAX_SAUT_CENTRE && sautEchelle <= this.MAX_SAUT_ECHELLE
    );
  }

  // Calibration : moyenne des mesures sur ~15 frames, visage de face.
  async _mesurerReference(video) {
    const pas = 1000 / this.FPS;
    const n = Math.max(4, Math.round(this.DUREE_REFERENCE_MS / pas));
    let somme = { ear: 0, rot: 0, bouche: 0 },
      vus = 0;
    for (let i = 0; i < n; i++) {
      const res = await this._detecter(video);
      const lm = res ? res.landmarks : null;
      if (lm) {
        somme.ear += this._earMoyen(lm);
        somme.rot += this._ratioRotation(lm);
        somme.bouche += this._ratioBouche(lm);
        vus++;
      }
      await this._attendre(pas);
    }
    if (vus < Math.ceil(n / 2)) {
      throw new Error(
        "Aucun visage détecté pendant la calibration du test de vie.",
      );
    }
    return {
      ear: somme.ear / vus,
      rot: somme.rot / vus,
      bouche: somme.bouche / vus,
    };
  }

  /* ============== Défis individuels ============== */

  async _testerBlink(video, ref) {
    // Seuil adaptatif : min entre seuil absolu et 70 % de l'ouverture mesurée
    const seuil = Math.min(this.SEUIL_EAR_CLIGNEMENT, ref.ear * 0.7);
    return this._framesPendant(
      video,
      this.DUREE_MAX_DEFI_MS,
      (lm) => this._earMoyen(lm) < seuil,
    );
  }

  async _testerTurn(video, ref, sens) {
    // Cible : le rapport doit franchir ref.rot ± SEUIL_ROTATION dans la bonne direction
    const cible = ref.rot + this.SENS_ROTATION * sens * this.SEUIL_ROTATION;
    return this._framesPendant(video, this.DUREE_MAX_DEFI_MS, (lm) => {
      const r = this._ratioRotation(lm);
      return sens > 0 ? r >= cible : r <= cible;
    });
  }

  async _testerSmile(video, ref) {
    const cible = ref.bouche * this.GAIN_SOURIRE;
    return this._framesPendant(
      video,
      this.DUREE_MAX_DEFI_MS,
      (lm) => this._ratioBouche(lm) >= cible,
    );
  }

  /* ============== Orchestrateur ============== */

  /**
   * Exécute la liste de défis imposée par le serveur.
   * @param {HTMLVideoElement} video
   * @param {string[]} defis - clés tirées par l'API (ex: ["blink", "smile"])
   * @param {Object} callbacks - { onStatus(message), onErreur(message) }
   * @throws {Error} si un défi n'est pas exécuté dans le délai imparti
   */
  async executerDefis(video, defis, callbacks = {}) {
    const onStatus = callbacks.onStatus || (() => {});
    const onErreur = callbacks.onErreur || (() => {});

    if (typeof faceapi === "undefined") {
      throw new Error("face-api.js n'est pas chargé : test de vie impossible.");
    }

    onStatus("Test de vie : placez-vous de face, regardez la caméra...");

    // 1. Calibration des mesures de référence
    const ref = await this._mesurerReference(video);
    if (this.DEBUG) {
      console.log(
        `[Liveness] Référence calibrée : EAR=${ref.ear.toFixed(3)} ` +
          `rot=${ref.rot.toFixed(3)} bouche=${ref.bouche.toFixed(3)}`,
      );
    }

    // 2. Exécution séquentielle des défis imposés par le serveur
    for (const cle of defis) {
      const defi = this._DEFIS[cle];
      if (!defi) continue; // clé inconnue : ignorée (compatibilité future)
      onStatus(`Test de vie : ${defi.texte}`);
      const reussi = await defi.tester(video, ref, this);
      if (!reussi) {
        onErreur(
          `Défi non exécuté dans les ${this.DUREE_MAX_DEFI_MS / 1000} s : « ${defi.texte} »`,
        );
        throw new Error(
          `Test de vie échoué : « ${defi.texte} ». ` +
            "Authentification refusée (protection anti-photo).",
        );
      }
    }

    onStatus("Test de vie réussi ✔");
    return true;
  }
}

// Exposition globale
window.LivenessModule = new LivenessModule();
