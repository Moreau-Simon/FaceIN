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
    this.DEBUG = true; // log console + mesures affichées à l'écran (false après calibrage)
    this.FPS = 10; // frames analysées par seconde
    this.DUREE_REFERENCE_MS = 1500; // durée visée pour la calibration (visage de face)
    this.DUREE_CALIBRATION_MAX_MS = 4000; // délai max pour obtenir assez de frames valides
    this.FRAMES_REFERENCE_MIN = 8; // nombre minimal de frames valides pour calibrer
    this.DUREE_MAX_DEFI_MS = 10000; // délai accordé pour exécuter un défi
    // Confiance minimale du détecteur. 0.65 perdait le visage dès que la tête
    // tournait ou que les yeux se fermaient ; 0.5 reste fiable pour un visage réel.
    this.CONFIANCE_MIN = 0.5;

    // Clignement
    this.SEUIL_EAR_CLIGNEMENT = 0.26; // ouverture des yeux en dessous = clignement
    this.RATIO_EAR_FERME = 0.85; // œil "fermé" si EAR < 85 % de la référence
    this.RATIO_EAR_OUVERT = 0.92; // œil "rouvert" si EAR remonte à 92 % de la référence
    // Fermer les yeux déplace légèrement les coins d'yeux détectés, ce qui fait
    // bouger les ratios rotation/bouche : les tolérances doivent être réalistes.
    this.STABILITE_ROT_BLINK = 0.15;
    this.STABILITE_BOUCHE_BLINK = 0.25; // 25 % de la valeur de référence

    // Rotation
    this.SEUIL_ROTATION = 0.06; // écart du rapport nez/yeux vs position de face
    this.FRAMES_ROTATION = 2; // frames consécutives au-delà du seuil (anti-bruit)

    // Sourire
    this.GAIN_SOURIRE = 1.08; // la bouche doit s'élargir de 8 %

    // Les frames brutes de la webcam ne sont PAS miroirées : quand l'utilisateur
    // tourne la tête vers SA gauche, le rapport nez/yeux AUGMENTE dans l'image.
    // (-1 correspond à cette réalité, validée par les mesures réelles ;
    //  remettez +1 si votre flux vidéo est miroité.)
    this.SENS_ROTATION = -1;

    // --- Continuité temporelle (anti-échange de photos pendant un défi) ---
    // Un visage réel bouge continûment. Les sauts sont mesurés relativement à la
    // HAUTEUR du visage (la largeur de la boîte rétrécit naturellement quand on
    // tourne la tête) et la tolérance augmente si l'écart entre 2 frames valides
    // est long (le détecteur peut perdre le visage quelques frames).
    this.MAX_SAUT_CENTRE = 0.35; // déplacement max du centre entre 2 frames (× hauteur du visage)
    this.MAX_SAUT_ECHELLE = 0.3; // variation max de la hauteur du visage entre 2 frames
    this.DISCONTINUITES_MAX = 3; // nombre de sauts consécutifs tolérés avant d'échouer
    this.PAS_REFERENCE_MS = 150; // écart "normal" entre 2 frames valides

    // Callback d'affichage (renseigné par executerDefis)
    this._onStatus = null;
    this._texteCourant = "";

    // --- Catalogue des défis (les clés correspondent à nonce.py) ---
    this._DEFIS = {
      blink: {
        texte: "clignez lentement des yeux",
        tester: (v, r, s) => s._testerBlink(v, r),
      },
      turn_left: {
        texte: "tournez la tête vers votre gauche",
        tester: (v, r, s) => s._testerTurn(v, r, -1),
      },
      turn_right: {
        texte: "tournez la tête vers votre droite",
        tester: (v, r, s) => s._testerTurn(v, r, +1),
      },
      smile: {
        texte: "souriez franchement",
        tester: (v, r, s) => s._testerSmile(v, r),
      },
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

  // Affichage des mesures en direct à l'écran (uniquement en mode DEBUG).
  _afficherMesures(lm) {
    if (!this.DEBUG || !this._onStatus) return;
    const suffixe = lm
      ? ` [EAR=${this._earMoyen(lm).toFixed(2)} rot=${this._ratioRotation(lm).toFixed(2)} bouche=${this._ratioBouche(lm).toFixed(2)}]`
      : " [visage non détecté]";
    this._onStatus(`Test de vie : ${this._texteCourant}${suffixe}`);
  }

  // Détection avec landmarks (le résultat contient .landmarks ET .detection.box,
  // la boîte étant nécessaire au contrôle de continuité).
  async _detecter(video) {
    const options = new faceapi.SsdMobilenetv1Options({
      minConfidence: this.CONFIANCE_MIN,
    });
    return faceapi.detectSingleFace(video, options).withFaceLandmarks();
  }

  // Échantillonne des frames pendant dureeMs ; s'arrête dès que validateur(lm) renvoie true.
  // Contrôle AUSSI la continuité : un échange de photo devant la caméra produit un
  // "téléport" du visage (position et/ou taille) entre deux frames consécutives.
  async _framesPendant(video, dureeMs, validateur) {
    const pas = 1000 / this.FPS;
    const fin = Date.now() + dureeMs;
    let precedente = null;
    let tPrecedente = 0;
    let discontinuites = 0;

    while (Date.now() < fin) {
      const t0 = Date.now();
      const res = await this._detecter(video);

      // Filtre des détections aberrantes : quand la tête est très tournée, le
      // détecteur peut se fixer sur le bord du visage ou l'arrière-plan et
      // produire des mesures impossibles (ex. EAR = 45). Ces frames sont
      // ignorées comme s'il n'y avait pas de visage.
      if (res && this._plausible(res.landmarks)) {
        const dt = precedente ? t0 - tPrecedente : this.PAS_REFERENCE_MS;
        if (!this._continuiteOk(res, precedente, dt)) {
          discontinuites++;
          if (discontinuites >= this.DISCONTINUITES_MAX) {
            throw new Error(
              "Mouvement du visage discontinu (échange de support devant la caméra ?). " +
                "Test de vie échoué.",
            );
          }
        } else {
          discontinuites = 0;
        }
        precedente = res;
        tPrecedente = t0;

        const valide = validateur(res.landmarks, res);
        this._afficherMesures(res.landmarks);
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
      } else {
        this._afficherMesures(null);
        if (this.DEBUG) {
          console.log(
            res
              ? "[Liveness] frame ignorée (mesures non plausibles)"
              : "[Liveness] aucun visage détecté sur cette frame",
          );
        }
      }
      // Attente adaptative : la détection prend déjà 100-300 ms,
      // on n'ajoute que le temps manquant pour viser un vrai this.FPS.
      const ecoule = Date.now() - t0;
      if (ecoule < pas) await this._attendre(pas - ecoule);
    }
    return false;
  }

  // Le centre du visage doit rester dans un rayon de MAX_SAUT_CENTRE hauteurs de
  // visage entre 2 frames, et sa taille ne doit pas varier brutalement.
  // La tolérance est proportionnelle à l'écart de temps réel entre les 2 frames.
  _continuiteOk(res, precedente, dtMs) {
    if (!precedente) return true;
    const b = res.detection.box;
    const p = precedente.detection.box;
    const sautCentre =
      Math.hypot(
        b.x + b.width / 2 - (p.x + p.width / 2),
        b.y + b.height / 2 - (p.y + p.height / 2),
      ) / p.height;
    const sautEchelle = Math.abs(b.height - p.height) / p.height;
    const tolerance = Math.max(1, dtMs / this.PAS_REFERENCE_MS);
    return (
      sautCentre <= this.MAX_SAUT_CENTRE * tolerance &&
      sautEchelle <= this.MAX_SAUT_ECHELLE * tolerance
    );
  }

  // Mesures plausibles pour un vrai visage : rejette les détections aberrantes
  // (l'EAR réel reste < 0.55 ; le bout du nez reste ~entre les coins d'yeux).
  _plausible(lm) {
    const ear = this._earMoyen(lm);
    const rot = this._ratioRotation(lm);
    const bouche = this._ratioBouche(lm);
    return (
      ear >= 0.05 &&
      ear <= 0.55 &&
      rot >= -0.1 &&
      rot <= 0.9 &&
      bouche >= 0.15 &&
      bouche <= 1.5
    );
  }

  // Calibration : moyenne des mesures sur des frames valides, visage de face.
  // On continue d'échantillonner (jusqu'à DUREE_CALIBRATION_MAX_MS) tant qu'on
  // n'a pas assez de frames : l'utilisateur a besoin d'un instant pour se placer.
  async _mesurerReference(video) {
    const pas = 1000 / this.FPS;
    const nCible = Math.max(
      this.FRAMES_REFERENCE_MIN,
      Math.round(this.DUREE_REFERENCE_MS / pas),
    );
    const fin = Date.now() + this.DUREE_CALIBRATION_MAX_MS;
    let somme = { ear: 0, rot: 0, bouche: 0 };
    let vus = 0;

    while (vus < nCible && Date.now() < fin) {
      const t0 = Date.now();
      const res = await this._detecter(video);
      const lm = res ? res.landmarks : null;
      if (lm && this._plausible(lm)) {
        somme.ear += this._earMoyen(lm);
        somme.rot += this._ratioRotation(lm);
        somme.bouche += this._ratioBouche(lm);
        vus++;
      }
      const ecoule = Date.now() - t0;
      if (ecoule < pas) await this._attendre(pas - ecoule);
    }
    if (vus < this.FRAMES_REFERENCE_MIN) {
      throw new Error(
        "Aucun visage détecté pendant la calibration du test de vie. " +
          "Placez-vous de face, avec un bon éclairage.",
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
    // Seuil adaptatif : chute relative de l'ouverture des yeux par rapport à la référence.
    const seuilFerme = Math.min(
      this.SEUIL_EAR_CLIGNEMENT,
      ref.ear * this.RATIO_EAR_FERME,
    );
    const seuilOuvert = ref.ear * this.RATIO_EAR_OUVERT;
    let ferme = false;

    // Un vrai clignement = yeux fermés PUIS rouverts, sans que la tête ne bouge
    // franchement (anti-photo pivotée). Exiger la réouverture évite aussi qu'un
    // simple bruit de landmarks valide le défi.
    return this._framesPendant(video, this.DUREE_MAX_DEFI_MS, (lm) => {
      const ear = this._earMoyen(lm);
      const stable =
        Math.abs(this._ratioRotation(lm) - ref.rot) <=
          this.STABILITE_ROT_BLINK &&
        Math.abs(this._ratioBouche(lm) - ref.bouche) <=
          ref.bouche * this.STABILITE_BOUCHE_BLINK;
      if (!stable) {
        ferme = false; // la tête a bougé : on repart de zéro
        return false;
      }
      if (ear < seuilFerme) ferme = true; // yeux fermés détectés
      return ferme && ear >= seuilOuvert; // puis rouverts => clignement validé
    });
  }

  async _testerTurn(video, ref, sens) {
    // Cible : le rapport doit franchir ref.rot ± SEUIL_ROTATION dans la
    // direction attendue. delta donne ET la cible ET le sens de comparaison
    // (comparer avec `sens` seul inverserait le défi).
    const delta = this.SENS_ROTATION * sens;
    const cible = ref.rot + delta * this.SEUIL_ROTATION;
    let consecutives = 0;
    return this._framesPendant(video, this.DUREE_MAX_DEFI_MS, (lm) => {
      const r = this._ratioRotation(lm);
      const atteint = delta > 0 ? r >= cible : r <= cible;
      consecutives = atteint ? consecutives + 1 : 0;
      return consecutives >= this.FRAMES_ROTATION;
    });
  }

  async _testerSmile(video, ref) {
    const cible = ref.bouche * this.GAIN_SOURIRE;
    // DURCISSEMENT anti-support-plat : un VRAI sourire rétrécit légèrement
    // les yeux (les joues montent — visible dans nos mesures réelles :
    // EAR 0.316 → 0.276 en souriant). Déplacer une photo change le rapport
    // de bouche mais laisse l'EAR constant → rejet.
    return this._framesPendant(
      video,
      this.DUREE_MAX_DEFI_MS,
      (lm) =>
        this._ratioBouche(lm) >= cible && this._earMoyen(lm) <= ref.ear * 0.95,
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
    this._onStatus = onStatus;

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
      this._texteCourant = defi.texte;
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

    // Petite pause : l'utilisateur vient d'exécuter les défis (tête tournée,
    // visage rapproché...) et doit se replacer de face avant l'extraction du
    // descripteur — sinon la capture échoue ("Aucun visage détecté").
    onStatus(
      "Test de vie réussi ✔ — replacez-vous de face devant la caméra...",
    );
    await this._attendre(2000);
    onStatus("Test de vie réussi ✔");
    this._onStatus = null;
    return true;
  }
}

// Exposition globale
window.LivenessModule = new LivenessModule();
