# Budget performance — scène 3D du hero (accueil)

- **Date** : 2026-11-17
- **Compétence appliquée** : `.opencode/skills/heavy-3d-animation`
- **État courant** : le modèle de rubans est remplacé par un emblème 3D de preuve d’identité ; aucun SVG n’est montré pendant le chargement ou en fonctionnement normal.
- **Intention de la scène** : un bouclier de vérification FaceIN sculpté en verre/lavande, à surface centrale vide, entouré de trois orbites rapprochées et de quatre nœuds lumineux.
- **Périmètre** : un seul usage dans `HomePage.tsx` (hero). Les autres illustrations SVG du site ne changent pas.
- **Bibliothèques vérifiées** (npm + docs officielles r3f.docs.pmnd.rs) :
  - `three@^0.187.0` — impose WebGL2 (détection + message accessible si indisponible).
  - `@react-three/fiber@^9.8.2` — peers `react/react-dom >=19 <19.4` (projet : 19.3.1 ✓), `three >=0.156` ✓.
  - **Refusés** : `@react-three/drei` (géométries natives suffisantes), `@react-three/postprocessing` (aucun effet post-traité nécessaire), `gsap` (l’horloge R3F pilote tout).

## Budget de la scène

- **Chorégraphie unique** : révélation par mise à l’échelle de l’objet, rotation lente des orbites et parallaxe amortie, tous pilotés par R3F. Pas d’animation Motion/GSAP concurrente dans le hero.
- **Budget** : 60 fps desktop visés, 30 fps mobiles minimum ; ≤ 12 draw calls, < 30 000 triangles, 4 nœuds instanciés, aucune texture applicative, DPR ≤ 2 (≤ 1,5 sur mobile), chunk 3D < 450 kB gzip.
- **Chargement et accessibilité** : import R3F différé ; aucun SVG ou autre illustration de substitution au chargement. En mouvement réduit, rendre une seule image 3D immobile. En cas d’indisponibilité WebGL, afficher un message textuel accessible. Pause hors viewport et onglet caché.
- **Dépendances** : aucune nouvelle dépendance. Utiliser uniquement Three.js et React Three Fiber déjà installés ; ne pas superposer le composant Ribbons de React Bits, qui possède son propre canvas et sa propre boucle RAF.

## Budget chiffré

| Métrique | Budget | Justification |
|---|---|---|
| FPS desktop | 60 | Animation shader légère, scène statique hors déplacement |
| FPS mobile / économie | 30 stables minimum | DPR plafonné à 1,5 sur écrans ≤ 768 px |
| Draw calls visibles | ≤ 12 | Bouclier, trois orbites et quatre nœuds instanciés |
| Triangles visibles | < 30 000 | Géométries procédurales simples, aucune simulation dense |
| Textures applicatives | 0 | Géométries procédurales, matériaux Three.js intégrés |
| Nœuds instanciés | 4 | Un `InstancedMesh` décoratif ; aucune simulation nécessaire |
| `new` dans `useFrame` | 0 | Le modèle existant est animé par transformations de groupes ; géométries/matériaux créés hors de la boucle |
| Poids du chunk 3D (lazy) | < 450 kB gzip | `three` + `@react-three/fiber` uniquement, import dynamique hors chemin critique |
| DPR | ≤ 2 (1,5 mobile) | `dpr={[1, maxDpr]}` calculé dans `perf.ts` |
| Durée de la séquence | Boucle infinie douce | Rotation lente, horloge unique `state.clock`; arrêtée en mode mouvement réduit |
| Interaction attendue | Parallaxe discrète | Décoratif : `pointer-events: none`, `aria-hidden` + libellé accessible |

## Repli et modes

- `prefers-reduced-motion: reduce` : Canvas reste 3D, mais le rendu est figé après son image initiale ; aucune animation de rotation ou de parallaxe.
- WebGL indisponible / erreur du chunk : message textuel accessible, jamais un SVG de substitution au chargement.
- Canvas hors viewport ou onglet caché : `frameloop` passe à `never` (IntersectionObserver + `visibilitychange`).

## Méthode de mesure (rapportées dans `docs/QUALITY_REPORT.md`)

- `renderer.info.render.calls` / `.triangles` via `gl.info` exposé uniquement en dev (`import.meta.env.DEV`).
- FPS mesuré par échantillonnage `requestAnimationFrame` sur ~1 s (desktop, onglet visible).
- Poids : sortie `vite build` (gzip).
- Pause : compteur de frames `info.render.frame` avant/après sortie du viewport.
- WebGL indisponible : vérifié en neutralisant WebGL2 dans le navigateur ; le message accessible s’affiche sans canvas ni SVG.
- Non mesurable dans cet environnement : appareils physiques (mobile milieu de gamme), FPS en onglet réellement visible, heap snapshot après navigation aller-retour.
