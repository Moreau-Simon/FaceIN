# Rapport qualité

- **Date** : 2026-11-17
- **Périmètre** : build de production et cinq pages React
- **Verdict** : prêt avec réserves — l'interface et les démonstrations sont opérationnelles, mais aucune API FaceIN n'est disponible dans ce dépôt.

## Modèle 3D actuel du hero — sceau d’identité (2026-11-17)

| Vérification | Résultat |
|---|---|
| `npm --prefix frontend run build` (TypeScript strict + Vite) | Réussi ; 5 entrées HTML générées |
| Bundle principal | 439,73 kB min / **136,42 kB gzip** |
| Chunk R3F différé | 922,65 kB min / **244,09 kB gzip**, sous le budget 450 kB gzip ; Vite signale le seuil de taille minifiée de 500 kB |
| Rendu visible | 1 canvas, **aucun SVG dans le hero** ; `renderer.info` : **6 draw calls**, **10 904 triangles**, **0 point**, 1 texture signalée par le renderer |
| Responsive | 320, 360, 390, 768, 1024 et 1440 px : un canvas, aucun SVG et `scrollWidth` égal au viewport |
| Mouvement réduit | Le canvas 3D reste présent, aucun SVG ; le compteur de rendu reste stable pendant l’observation |
| Repli WebGL | Testé avec WebGL2 neutralisé : message `role="status"`, aucun canvas ni SVG |
| FPS / pause hors écran | Non mesurés de façon fiable dans cette session : le navigateur de contrôle marquait la page comme masquée et limitait les frames |
| Console | Aucune erreur de rendu après rechargement complet ; avertissement de dépréciation `THREE.Clock` provenant de R3F/Three.js |
| Dépendances | Aucune nouvelle dépendance ; Three.js et React Three Fiber déjà installés |

## Effets premium (upgrade R3F + effets DOM) — état antérieur (2026-11-17)

Analyse des cinq dépôts demandés puis implémentation (détails et licences dans `docs/DECISIONS.md`) ; budget 3D inchangé (`docs/PERF_BUDGET_3D.md`).

| Vérification | Résultat |
|---|---|
| `npm run typecheck` | Réussi, 0 erreur |
| `npm run build` | Réussi ; 5 entrées HTML générées |
| Chunk 3D | `RibbonScene-*.js` 926,71 kB min / **245,82 kB gzip** — sous le budget 450 kB gzip (budget inchangé : apparition + parallaxe + scintillement ne coûtent ni draw call ni triangle) |
| Bundle principal | `main-*.js` 439,43 kB min / 136,31 kB gzip, dont +2,7 kB gzip pour les cinq effets DOM (0 nouvelle dépendance npm) |
| CSS | 65,17 kB (14,94 kB gzip), +0,42 kB pour `shiny-text`, `spotlight-card`, `typed-terminal` |
| Nouveaux composants | `BlurText`, `Magnet`, `ShinyText`, `useSpotlight`, `TypedTerminal` dans `components/ui/` |
| Accessibilité | `aria-label` sur le titre BlurText, résumé `sr-only` du terminal, effets `Magnet`/spotlight sans impact clavier, `prefers-reduced-motion` respecté partout (rendu statique/instantané) |
| Statut prototype | Libellés du terminal alignés (« cible », « simulé », « à venir ») |
| Mesures runtime 3D (draw calls, FPS, pause) | **Exécutées** (fenêtre redevenue visible) : 61 fps, 3 draw calls, 900 triangles, 180 points, 0 texture ; pause hors viewport vérifiée par compteur de frames |

## Premier modèle en rubans du hero — remplacé (2026-11-17)

Intégration R3F cadrée par `docs/PERF_BUDGET_3D.md` ; décision consignée dans `docs/DECISIONS.md`.

| Vérification | Résultat |
|---|---|
| `npm run typecheck` | Réussi, 0 erreur (avec `@types/three@^0.187.0` ajouté en devDependency) |
| `npm run build` | Réussi ; le bundle principal passe de 428,95 à 431,86 kB (+2,91 kB : wrapper, détection, repli) |
| Chunk 3D différé | `RibbonScene-*.js` 924,89 kB min / **245,22 kB gzip** — sous le budget de 450 kB gzip, chargé après le premier rendu (fallback SVG pendant le chargement) |
| CSS | 63,72 kB (14,52 kB gzip), +0,21 kB pour `.ribbon-3d*` |
| Montage DOM | Wrapper `.ribbon-3d.home-hero__ribbons` présent, `aria-hidden="true"`, libellé `sr-only`, canvas monté |
| Console | Aucune erreur pendant le chargement et le montage |
| Dépendances | `three@^0.187.0` + `@react-three/fiber@^9.8.2` (peers React 19.3.1 ✓) ; `@types/three` ajouté ; drei/postprocessing/gsap refusés |
| Mesures runtime (draw calls, triangles, FPS, pause hors viewport) | **Exécutées le 2026-11-17, fenêtre visible** : 60–61 fps mesurés sur ~1 s ; `renderer.info` = **3 draw calls** (budget < 12), **900 triangles** (budget < 30 000), **180 points** (budget ≤ 200), **0 texture**, 3 géométries, 3 programmes shader. Pause vérifiée : compteur `info.render.frame` figé hors viewport (2 141 → 2 141 en 1,5 s) puis reprise au retour (2 141 → 2 215). Largeur mobile ~437 px : canvas 451×585 rendu, 3 draw calls |
| Console et responsive | 0 erreur console sur les cinq pages en prévisualisation ; aucun débordement horizontal (437 px) |
| Tests non exécutables dans cet environnement | Appareil mobile réel, WebGL désactivé, heap snapshot après navigation aller-retour |

## Réécriture éditoriale (2026-11-17)

| Vérification | Résultat |
|---|---|
| `npm run typecheck` | Réussi, 0 erreur |
| `npm run build` | Réussi ; 5 entrées HTML générées |
| Mentions de statut | Centralisées dans `src/app/content.ts` ; les pages distinguent la cible du projet et l’état du prototype |
| Pages réécrites | Accueil, fonctionnement, connexion, intégration, offres, en-tête/pied de page et aperçu interactif |
| Promesses retirées | Chiffres de connexions, « 128/256 valeurs », « 2 sur 3 », « 1 clic », renouvellement à 6/12 mois et tarifs présentés comme actifs |
| Navigation | Les cinq URL répondent en prévisualisation ; titres HTML et `document.title` à jour |
| Console navigateur | Aucune erreur pendant le contrôle des cinq pages |
| Responsive après réécriture | 439 px et 1269 px ; aucun débordement horizontal |
| Linter / tests | Toujours non disponibles : aucun linter ni test automatisé n’est configuré |

## Audit et restructuration (2026-11-17)

| Vérification | Résultat |
|---|---|
| `npm run typecheck` (TypeScript strict, `noUnusedLocals`/`noUnusedParameters`) | Réussi, 0 erreur |
| `npm run build` | Réussi ; 5 entrées HTML générées dans `dist/` |
| Graphe d’imports (`src/`) | 0 dépendance circulaire |
| URLs internes | Centralisées dans `src/app/navigation.ts`; plus aucune chaîne `.html` en dur dans les pages |
| Ancres | Cohérentes (les IDs des étapes d’intégration sont générés depuis `step.id`) |
| Routes en prévisualisation | `/index.html`, `/connexion.html`, `/comment-ca-marche.html`, `/integrer.html`, `/tarif.html` → HTTP 200 |
| Linter | Non configurable : aucun linter n’est installé dans ce dépôt (le typecheck strict en fait office) |
| Tests | Aucun test automatisé n’existe dans le frontend ; les contrôles sont manuels |

Architecturalement : `app/` (composition, routes, navigation), `components/{layout,ui,visuals}/`, `features/<page>/`, `styles/site.css`. Code mort supprimé : liste `documentationIndex` inutilisée, classe CSS `.expand-mark`, gestionnaires Échap dupliqués avec l’événement natif `cancel` des dialogues, `useMemo` sans bénéfice sur quatre éléments.

## Résultats

| Vérification | Résultat |
|---|---|
| `npm install` | Réussi; 0 vulnérabilité signalée par npm |
| `npm run build` | Réussi; TypeScript strict puis Vite 8 multipage |
| Pages dans le serveur de prévisualisation | Les cinq URL renvoient HTTP 200 |
| Responsive | Contrôle après réécriture à 439 px et 1269 px ; aucun débordement horizontal sur les cinq pages |
| Navigation et ancres | Contact atteint le formulaire depuis la page Tarifs; aucune ancre locale manquante ni ID dupliqué |
| Console navigateur | Aucune erreur JavaScript ou console pendant le contrôle des pages |
| Widget d’aperçu | Dialogue supérieur, verrouillage du défilement, focus/restauration, Échap, clic sur l’overlay, sélection d’offre, mouvement réduit et rendu mobile vérifiés |
| Navigation de l’en-tête | « Télécharger » et « À propos » retirés; Contact mène au formulaire |
| Tarifs | Formules présentées comme indicatives ; aucun abonnement ni paiement opérationnel |
| Formulaire de contact | Validation et avertissement vérifiés; aucun message n’est envoyé sans service configuré |
| Parcours d'inscription | Validation invalide bloquée; formulaire valide ouvre l'étape de démonstration et son avertissement |
| Autres interactions | Onglets, menu mobile, recherche « Python »/aucun résultat, FAQ, copie de code, lien de contact et message de révocation vérifiés |
| Clavier et mouvement réduit | Lien d'évitement visible au focus; préférence `prefers-reduced-motion` vérifiée |

## Taille du build

- JavaScript : 439,43 kB (136,31 kB gzip) après l’upgrade R3F et les cinq effets DOM ; chunk différé `RibbonScene` 926,71 kB (245,82 kB gzip), chargé à la demande.
- CSS : 65,17 kB (14,94 kB gzip) après ajout des styles `.ribbon-3d`, `.shiny-text`, `.spotlight-card`, `.typed-terminal`.
- Les métriques LCP/INP/CLS n'ont pas été mesurées.

## Contraste et accessibilité

Contrastes calculés pour les principaux tokens sur fond blanc : `--ink` 15,54:1, `--muted` 5,43:1, `--primary` 6,19:1 et `--soft-muted` 5,20:1. Le focus clavier est visible, les champs ont des labels, les FAQ utilisent les éléments natifs `details/summary`, et les graphiques décoratifs ont un nom accessible.

Ce contrôle n'est pas un audit WCAG automatisé complet; certains textes minuscules dans les maquettes illustratives restent à revoir lors d'une validation d'accessibilité formelle.

## Corrections réalisées

- Identifiants des dégradés SVG rendus uniques entre illustrations.
- Débordement horizontal du code sur petit écran corrigé; toutes les pages passent désormais les quatre largeurs testées.
- Ancres du guide d'intégration et chemins des cinq entrées vérifiés.
- Exports JSX bruts inutilisés retirés après migration de leurs rendus vers les composants React.
- Les widgets principaux de l’accueil peuvent être agrandis en premier plan dans un dialogue accessible.
- Un aperçu produit interactif reprend les codes de composition Stripe avec une illustration locale et des indicateurs explicitement fictifs.
- Le bouton de contact de la section finale a été retiré à la demande; les autres contenus de cette section sont conservés.
- Le formulaire de contact et les tarifs demandés sont intégrés; l’absence de service de soumission et de facturation est signalée clairement.
- Révocation, téléchargement et authentification ne prétendent pas appeler un service absent; les limites sont annoncées dans l'interface.
- Les textes répétitifs ont été remplacés par une formulation cohérente avec l’état du prototype : cible, limites, métadonnées et fonctions encore à implémenter.
- Les animations SVG et au scroll respectent `prefers-reduced-motion`.
- Le flux caméra est arrêté/nettoyé lors de l'arrêt, du changement d'étape et du démontage du composant.

## Réserves restantes

- Aucun backend HTTP, SDK téléchargeable, compte, reconnaissance faciale, révocation ou jeton réel n'est fourni par ce projet; ces éléments ne sont pas simulés comme fonctionnels.
- Le formulaire de contact est une maquette validable mais ne transmet pas les messages tant qu’un canal de réception n’est pas configuré.
- Les offres et prix sont affichés, mais aucun abonnement ni paiement n’est encore connecté à un service de facturation.
- L'aperçu caméra réel n'a pas été activé pendant le contrôle; il dépend d'une permission explicite et d'un appareil compatible.
- Les tarifs, mentions légales et affirmations produit doivent être confirmés avant publication.
- Un audit d'accessibilité formel et des mesures de performance réelles restent à effectuer.
- Aucun linter ni test automatisé n'est configuré dans le frontend : l'ajout d'ESLint et de Vitest reste recommandé avant une montée en charge de l'équipe.
