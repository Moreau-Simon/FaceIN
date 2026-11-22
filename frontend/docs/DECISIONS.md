# Decisions

> Journal des décisions techniques et artistiques (plus récent en haut).

## Format
`## [AAAA-MM-JJ] Titre` - Contexte - Options considérées - Décision - Raisons - Conséquences.

## [2026-11-22] Connexion biométrique reprise de `capture_camera_photo`

- **Contexte** : le site devait proposer une vraie connexion, avec le fonctionnement et l’interface de capture de la branche `capture_camera_photo`.
- **Options** : réimplémenter la biométrie, ou porter en TypeScript les modules existants (`fronted_api/js/*`) et l’interface de `partner-demo`.
- **Décision** : portage fidèle dans `src/lib/facein/` (mêmes seuils, mêmes routes `/register`, `/nonce`, `/authenticate`). face-api.js 0.22.2, snarkjs 0.7.4 et circomlibjs 0.1.7 sont chargés à la demande depuis jsDelivr, aux mêmes versions que la branche d’origine ; modèles et circuit copiés dans `public/facein/`. L’interface de capture (couronne, médaillon, maillage, glyphe, pastille) est animée avec Motion au lieu de GSAP.
- **Raisons** : aucun écart de comportement avec le prototype validé, pas de nouvelle dépendance npm lourde, bibliothèques chargées uniquement sur la page de connexion.
- **Conséquences** : l’API Gateway doit tourner (`VITE_FACEIN_API_URL`, par défaut `http://localhost:8000/api`). Le premier chargement télécharge environ 25 Mo (modèles + circuit).

## [2026-11-22] Espace client alimenté par un journal local

- **Contexte** : l’espace client doit lister les connexions en cours et établies avec les sites partenaires, mais l’API n’expose pas cet historique.
- **Décision** : `src/lib/facein/connections.ts` enregistre chaque connexion (réussie ou refusée) sur l’appareil. Tant qu’aucune connexion partenaire n’existe, des lignes « Exemple » sont affichées.
- **Conséquences** : à remplacer par une route API dédiée ; l’interface de l’espace ne changera pas.

## [2026-11-22] Refonte visuelle alignée sur la maquette v3

- **Décision** : police Inter auto-hébergée (`@fontsource-variable/inter`, aucune requête tierce), grille verticale et boutons à flèche animée inspirés de stripe.com, widgets d’accueil interactifs (halo au survol, pression au clic, ouverture agrandie animée depuis la carte).
- **Conséquences** : `ExperienceWidget` (aperçu de paiement sans rapport avec le produit) et `ZoomableWidget` sont remplacés par `DemoWalkthrough` et `WidgetCard`.

## [2026-11-17] Aperçu produit dans un dialogue natif

- **Contexte** : présenter un widget interactif façon produit Stripe sans faire croire à un paiement ou à une authentification opérationnels.
- **Options** : dépendance de modal supplémentaire, couche maison, ou élément natif `<dialog>`.
- **Décision** : utiliser `<dialog>` pour la couche supérieure, le focus et l’inertie de l’arrière-plan; CSS pour les transitions, Motion déjà installé pour respecter la réduction des mouvements.
- **Raisons** : comportement clavier et modal natifs, pas de nouvelle dépendance, animation légère et contrôlable.
- **Conséquences** : la simulation de paiement est clairement étiquetée comme illustrative; les formules ne déclenchent aucune transaction.

## [2026-11-16] Garder cinq entrées HTML statiques

- **Contexte** : les maquettes correspondent à cinq URL et le dépôt ne fournit pas de réécriture SPA côté serveur.
- **Options** : routeur client avec fallback serveur ou build multipage.
- **Décision** : React/TypeScript avec Vite multipage et une entrée HTML par URL.
- **Raisons** : accès direct à chaque page, navigation statique, déploiement sans configuration serveur spécifique.
- **Conséquences** : la sélection de page est déterminée par le nom de fichier; les liens gardent les URL `.html`.

## [2026-11-16] Ne pas simuler de backend FaceIN

- **Contexte** : aucun endpoint HTTP frontend opérationnel n'a été confirmé dans le dépôt.
- **Décision** : les formulaires indiquent explicitement qu'aucun compte ou jeton n'est créé; la caméra n'est qu'un aperçu local et les exemples du guide sont marqués comme illustratifs.
- **Conséquences** : l'intégration réelle requiert un contrat d'API et un SDK validés.

## [2026-11-16] Préférer SVG et Motion à la 3D

- **Contexte** : les formes de ruban et de réseau sont décoratives et ne requièrent pas une scène interactive.
- **Options** : SVG/CSS léger ou WebGL/React Three Fiber.
- **Décision** : SVG/CSS avec Motion, révélations ponctuelles et prise en compte de `prefers-reduced-motion`.
- **Raisons** : cohérence avec les maquettes, poids et complexité moindres, amélioration progressive.

## [2026-11-16] Éviter les polices et assets distants

- **Contexte** : les maquettes reposent sur une typographie sans-serif et des motifs abstraits.
- **Décision** : pile système locale et illustrations SVG/CSS réalisées dans l'application.
- **Raisons** : rendu rapide sans requête tierce par défaut et identité visuelle propre à FaceIN.
