# Decisions

> Journal des décisions techniques et artistiques (plus récent en haut).

## Format
`## [AAAA-MM-JJ] Titre` - Contexte - Options considérées - Décision - Raisons - Conséquences.

## [2026-11-17] Remplacement complet du modèle 3D du hero

- **Contexte** : l’utilisateur a jugé le modèle de rubans 3D initial insuffisant et a demandé son remplacement complet, sans SVG au chargement.
- **Analyse des sources** : [`RaihanAizvan/portfolio`](https://github.com/RaihanAizvan/portfolio) n’a pas de licence déclarée ; ne pas copier son code. [`iammagdy/MagdySaber_Portfolio`](https://github.com/iammagdy/MagdySaber_Portfolio) et [`pmndrs/react-three-examples`](https://github.com/pmndrs/react-three-examples) sont MIT ; les exemples pmndrs consultés sont WebGPU/R3F 10 alpha, donc pas des composants directement compatibles avec le projet. [`react-bits`](https://github.com/DavidHDev/react-bits) utilise MIT + Commons Clause ; son composant [Ribbons](https://reactbits.dev/animations/ribbons) créerait un second canvas et une boucle RAF distincte. [`letshackit/Portfolio`](https://github.com/letshackit/Portfolio) est MIT ; retenir le principe de repli SVG et de chargement différé, sans copier sa scène.
- **Compatibilité** : réutilisation des versions déjà installées (`react@19.3.1`, `motion@14.14.0`, `@react-three/fiber@9.8.2`, `three@0.187.0`) ; aucune dépendance, ressource ou implémentation externe copiée.
- **Décision** : remplacer les rubans par un sceau de vérification procédural (bouclier facetté à surface centrale vide, trois orbites rapprochées et nœuds lumineux instanciés). Le modèle WebGL est la seule illustration du hero au chargement ; aucune image ou SVG de substitution n’est affiché. En mouvement réduit, le même modèle reste en 3D mais figé. WebGL indisponible affiche un message accessible.
- **Raisons** : obtenir une forme-signature lisible sur le thème de la preuve d’identité, distincte du ruban peu abouti, sans simuler un traitement de biométrie réelle, copier d’asset externe ni ajouter de dépendance.
- **Conséquences** : ancien code des rubans supprimé ; budgets et résultats dans `docs/PERF_BUDGET_3D.md` et `docs/QUALITY_REPORT.md`.

## [2026-11-17] Hero d’accueil statique et sans chevauchement

- **Contexte** : le titre et le ruban 3D s’animaient simultanément à l’ouverture ; à certaines largeurs, leur composition se chevauchait. Le style du texte descriptif ciblait aussi la note de bas de page.
- **Décision** : retirer les animations d’entrée et les effets magnétiques/brillants du hero, conserver son illustration sous forme de ruban SVG statique, puis organiser le texte et l’illustration dans une grille qui s’empile sur mobile. Les animations des autres sections restent inchangées.
- **Raisons** : éviter les animations concurrentes et les chargements WebGL inutiles sur le premier écran, tout en gardant son identité visuelle et tous ses contenus.
- **Conséquences** : le hero n’importe plus la scène 3D ; le composant SVG conserve son animation optionnelle pour les autres usages.

## [2026-11-17] Effets premium DOM adaptés de dépôts tiers (analyse des 5 dépôts demandée)

- **Contexte** : l'utilisateur a demandé l'analyse de cinq dépôts GitHub (RaihanAizvan/portfolio, iammagdy/MagdySaber_Portfolio, pmndrs/react-three-examples, DavidHDev/react-bits, letshackit/Portfolio) et l'implémentation des meilleurs éléments, sans remplacer l'architecture.
- **Vérification des licences (mise à jour après vérification des dépôts)** : `react-three-examples` **MIT** ; `react-bits` **MIT + Commons Clause v1.0** (intégration dans ce site autorisée, republication en bibliothèque interdite) ; `letshackit/Portfolio` et `MagdySaber_Portfolio` **MIT** ; `RaihanAizvan/portfolio` **sans licence déclarée** (aucun code ni asset copié).
- **Décision** : cinq effets adaptés, sans aucune nouvelle dépendance :
  - `BlurText` (`components/ui/BlurText.tsx`, d'après react-bits, Motion) — titre du hero, apparition mot par mot flou→net, `aria-label` du texte original, rendu statique sous `prefers-reduced-motion`.
  - `Magnet` (`components/ui/Magnet.tsx`, d'après react-bits, springs Motion) — CTA du hero et « Tester le parcours » du header ; désactivé sans pointeur/reduced-motion.
  - `ShinyText` (`components/ui/ShinyText.tsx` + CSS, d'après react-bits) — reflet CSS pur sur les libellés CTA principaux.
  - Spotlight (`components/ui/useSpotlight.ts` + CSS, d'après SpotlightCard, react-bits) — dégradé radial suivant le curseur sur les trois cartes preuve ; aucune re-render React (variables CSS).
  - `TypedTerminal` (`components/ui/TypedTerminal.tsx`, adapté de `TypedStream`, letshackit/Portfolio, MIT) — terminal à frappe **basée temps** (~34 caractères/s, pauses inter-lignes, pause hors viewport) dans la bannière démo ; rendu instantané sous reduced-motion, résumé sr-only, libellés strictement alignés sur le statut prototype.
- **Côté R3F** (corollaire de l'analyse de react-three-examples, MIT — transcriptions GLSL, pas de TSL/WebGPU, pas de Drei ni GSAP, toujours non justifiés) : apparition « dessinée » des rubans (`uReveal` + attributs `aDelay`, technique `instance-path`), particules en vague + scintillement par graine (technique `tsl-galaxy`), parallaxe curseur amorti (`MathUtils.damp`).
- **Raisons** : effets nuls en poids (main +2,7 kB gzip), compatibles React 19/TS strict, accessibilité et reduced-motion respectés, licences vérifiées et créditées.
- **Conséquences** : budget 3D inchangé (cf. `PERF_BUDGET_3D.md` — chunk 926,71 kB min / 245,82 kB gzip) ; l'ajout d'un nouvel effet doit passer par cette vérification de licence. Mesures runtime 3D restant à refaire avec la fenêtre visible (contrainte environnement, cf. QUALITY_REPORT).

## [2026-11-17] Skill dédié à l'animation 3D lourde

- **Contexte** : une demande portait sur la génération de rendus 3D complexes en React avec optimisation ; les skills existants couvraient l'animation 2D (`advanced-web-animation`) et la 3D légère (`webgl-experience`), sans prendre en charge scènes denses, GPGPU, shaders et profiling GPU.
- **Options** : enrichir `webgl-experience`, créer un skill séparé, ou ne rien ajouter.
- **Décision** : créer `heavy-3d-animation` dans `.opencode/skills/`, cadré sur la génération et l'optimisation de scènes 3D lourdes, avec budget chiffré, mesures, repli et limites explicites vis-à-vis des skills existants.
- **Raisons** : spécialisation claire, chargement à la demande, pas de duplication et continuité avec le workflow en 9 phases.
- **Conséquences** : phase 7 du workflow mise à jour ; ce skill ne remplace pas la décision du 2026-11-16 (« Préférer SVG et Motion à la 3D ») : son activation sur FaceIN nécessite une validation de périmètre et un budget performance dédié.

## [2026-11-17] Ruban 3D WebGL sur le hero de l’accueil — décision historique, modèle ensuite remplacé

- **Contexte** : la décision du 2026-11-16 (« Préférer SVG et Motion à la 3D ») couvre les visuels décoratifs. L’utilisateur a invoqué la commande `heavy-3d-animation` sur le ruban SVG du hero, ce qui vaut validation du changement de périmètre exigé par le skill.
- **Options** : conserver le SVG animé (Motion), ou le remplacer par une scène React Three Fiber à charge différée.
- **Décision initiale** : remplacer uniquement l’usage de `RibbonArtwork` du hero par une scène WebGL2 différée. Cette scène a été remplacée ensuite par le sceau 3D documenté ci-dessus ; `DemoBanner.tsx` et les autres visuels restent en SVG/Motion.
- **Dépendances** : `three@^0.187.0` et `@react-three/fiber@^9.8.2` seulement ; `drei`, `@react-three/postprocessing` et `gsap` vérifiés puis refusés (aucun helper ni effet nécessaire, cf. `docs/PERF_BUDGET_3D.md`).
- **Raisons initiales** : étudier une scène 3D procédurale sur l’illustration d’accueil sans nouvelle dépendance.
- **Conséquences** : budget initial conservé comme historique ; les critères actifs sont dans la décision plus récente et `docs/PERF_BUDGET_3D.md`.

## [2026-11-17] Réécriture éditoriale alignée sur l’état réel du prototype

- **Contexte** : plusieurs pages répétaient des promesses non vérifiées (« 0 image », « 128 valeurs », « 2 sur 3 », « révocation en un clic », tarifs et renouvellement) alors que la vérification biométrique, le vérificateur cryptographique, la base de données et le flux de bout en bout restent à intégrer.
- **Options** : conserver les textes marketing, supprimer les sections concernées, ou réécrire les contenus en distinguant la cible du projet de ce qui est réellement développé.
- **Décision** : centraliser les mentions de statut dans `src/app/content.ts`, remplacer les promesses par le vocabulaire du document de référence, et conserver les structures, classes CSS et interactions existantes.
- **Raisons** : ne pas présenter des fonctions prévues comme opérationnelles, garder une formulation cohérente entre les pages et préserver le design existant.
- **Conséquences** : les sections « architecture », « révocation », « métadonnées » et « offres » ont été reformulées ; les maquettes et tarifs restent explicitement illustratifs ; les titres HTML et `document.title` suivent la nouvelle terminologie.

## [2026-11-17] Restructuration par fonctionnalités et centralisation de la navigation

- **Contexte** : les composants partagés, le layout et les visuels spécifiques étaient mélangés dans `src/components/`; la page d’accueil concentrait 372 lignes et neuf sous-composants locaux; le nom de fichier courant était calculé dans deux modules et les URL `.html` étaient répétées dans tout le code.
- **Options** : conserver la structure plates, adopter un routeur client, ou organiser `src/` en couches (`app/`, `components/`, `features/`) sans changer le modèle multipage.
- **Décision** : garder le build multipage (décision du 2026-11-16), déplacer les composants dans `layout/`, `ui/` et `visuals/`, isoler chaque page dans `features/<nom>/`, extraire les maquettes de l’accueil dans `features/home/components/`, et centraliser URLs (`navigation.ts`) et table des pages (`routes.ts`).
- **Raisons** : séparation claire des responsabilités, imports prévisibles, suppression des valeurs dupliquées, aucune nouvelle dépendance, comportement et design inchangés.
- **Conséquences** : ajout ou renommage d’une page = une seule entrée dans `vite.config.ts`, `navigation.ts` et `routes.ts`; le titre et l’URL d’une page restent aussi déclarés dans son fichier HTML pour le référencement et le rendu sans JavaScript.

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
