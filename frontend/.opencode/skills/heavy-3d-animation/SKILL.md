---
name: heavy-3d-animation
description: Génère et optimise des animations 3D lourdes en React (React Three Fiber / Three.js) - scènes denses, particules GPGPU, shaders GLSL, post-processing, physique, cinématiques synchronisées - avec budget GPU/CPU, profiling et repli. À charger quand la 3D dépasse une scène simple ou qu'un rendu 3D complexe est demandé.
license: MIT
compatibility: opencode
metadata:
  role: specialiste-animation-3d-lourde
  language: fr
---

# Heavy 3D Animation

## Rôle
Ingénieur d'animation 3D temps réel. Transforme un besoin en scène React Three Fiber / Three.js dense et fluide, puis dimensionne le rendu pour qu'il tienne un budget mesuré. Une scène lourde n'est jamais justifiée par « ça fait fancy » : elle sert une intention et reste sous budget sur le plateau cible.

## Périmètre et frontières
- **Prise en charge** : plus de quelques dizaines d'objets, particules massives, shaders GLSL sur mesure, post-processing, simulation physique, cinématiques synchronisées, streaming de ressources, profiling GPU/CPU, mode économie.
- **`advanced-web-animation`** : animations DOM/CSS/Motion/GSAP en 2D. Les garder pour l'UI autour du canvas.
- **`webgl-experience`** : décision d'usage de la 3D, scène simple, pipeline d'assets de base, repli. Ce skill prend le relais quand la complexité augmente.
- **`frontend-quality-and-performance`** : audit final indépendant ; fournir-lui les mesures, ne pas les deviner.
- **FaceIN** : la décision du 2026-11-16 (« Préférer SVG et Motion à la 3D ») reste la référence pour les visuels décoratifs. Activer ce skill sur le projet = changement de périmètre à faire valider avant intégration.

## Responsabilités
- Cadrer l'intention, le plateau cible et le budget avant d'écrire du code.
- Concevoir la scène (géométries, matériaux, lumières, caméra, animation) et choisir les techniques de mise à l'échelle.
- Écrire des composants R3F isolés, typés et nettoyés.
- Mesurer, optimiser, re-mesurer ; documenter les gains.
- Fournir un repli (image/vidéo/CSS, scène statique, mode économie) et le respect de `prefers-reduced-motion`.

## Processus de génération (ordre obligatoire)

### 1. Cadrer et chiffrer
Avant tout code, produire un mini-budget écrit (section dans `docs/DECISIONS.md` ou `docs/PERF_BUDGET_3D.md`) :
intention de la scène, plateformes, fps cible, nombre max de draw calls / triangles visibles / textures, poids initial, interaction attendue, durée de la séquence, condition de repli. Sans chiffres, pas d'optimisation possible.

### 2. Vérifier les bibliothèques
Vérifier versions et API officielles via `frontend-researcher` avant d'installer : `three`, `@react-three/fiber`, `@react-three/drei`, `@react-three/postprocessing`, `@react-three/rapier`, `motion`/`gsap`. Ne pas inventer de props ni de noms d'exports. Justifier chaque dépendance ; refuser une bibliothèque de post-processing si un shader de 20 lignes suffit.

### 3. Choisir le mode de rendu
| Contexte | Choix |
|---|---|
| Scène R3F standard, interaction DOM | `<Canvas>` + `frameloop="demand"` si la scène est majoritairement statique |
| Simulation lourde sans événements DOM | Three.js seul + `OffscreenCanvas` dans un Web Worker (transferables), poster DOM à l'attente |
| Très grand nombre d'objets identiques | `InstancedMesh` / `<Instances>` de drei, jamais un mesh par objet |
| Rendu haute fidélité ponctuel | Pré-rendu vidéo/WebP ou image sequence, pas un rendu temps réel |

Vérifier les exigences WebGL/WebGPU de la version de three retenue (les versions récentes imposent WebGL2) ; prévoir la détection et le repli.

### 4. Construire la scène à l'échelle
- **Géométries** : fusionner les statiques (`mergeGeometries`), instancier les répétitions, LOD (`<Detailed distances>` ou `LOD`), impostors/billboards pour le lointain, occlusion via `frustumCulled` et culling manuel si nécessaire. Pipeline GLB : Draco ou Meshopt, KTX2/Basis pour les textures, `useGLTF.preload()` hors du chemin critique.
- **Matériaux / shaders** : privilégier `shaderMaterial` de drei ou `RawShaderMaterial` ; passer les données par attributs d'instance plutôt que par uniforms multiples ; éviter les branches dynamiques et la haute précision inutile sur mobile ; garder les shaders dans `src/features/<feature>/three/shaders/` (`.glsl` importés en string) avec commentaires sur l'intention.
- **Particules** : CPU seulement pour quelques centaines ; au-delà, GPGPU (`GPUComputationRenderer` ou ping-pong `WebGLRenderTarget` float) avec positions/vitesses dans des textures, rendu final via `InstancedBufferGeometry` ou `Points`. Toujours borner le nombre de particules au budget.
- **Animation** : `useFrame((state, delta) => ...)` avec `delta` (jamais de nombre de frames) ; `MathUtils.damp` / `lerp` avec facteur dépendant de `delta` ; horloge unique (`state.clock`) pour synchroniser shaders, particules et caméra ; timelines GSAP/Motion uniquement pour piloter des uniforms/props, une seule source de vérité.
- **Physique** : pas de `useFrame` custom pour la collision ; moteur dédié dans un worker si possible, pas de pas de temps variable, corps endormis, colliders simples.
- **Post-processing** : ordre réfléchi (AO → ombres/contact → bloom → DOF → tone mapping → AA) ; activer uniquement les effets visibles ; proposer un preset « économie » qui désactive bloom/DOF/SSAO ; vérifier les licences des effets propriétaires.
- **Lumières / ombres** : une lumière directionnelle avec ombre uniquement si elle se voit ; `shadow-mapSize` calibré, `shadow-camera-*` serré sur la zone utile, ombres cuites ou contact shadows pour le reste ; IBL/environment map compressée plutôt que plusieurs lights dynamiques.

### 5. Optimiser le runtime
1. `dpr` plafonné (1,5 sur mobile, 2 sur desktop) et adaptatif (`PerformanceMonitor` / `setDpr`) avec dégradation progressive.
2. `frameloop="demand"` + `invalidate()` dès qu'une valeur change ; sinon pause quand le canvas sort du viewport (`IntersectionObserver`) ou que l'onglet est caché (`visibilitychange`).
3. Mettre à jour les matrices d'instances en lot, un seul `needsUpdate` par frame ; réutiliser un `Object3D` temporaire, jamais `new` dans `useFrame`.
4. Ne pas recréer de géométrie/material/texture dans le render : `useMemo` / `useCallback`, props stables.
5. Libérer à la navigation : `dispose()` des ressources créées impérativement (RenderTarget, textures, geometries, matériaux), `cancelAnimationFrame`, `removeEventListener`, arrêt du worker. R3F dispose automatiquement les objets déclaratifs, pas les objets créés à la main.
6. Limiter la mémoire GPU : textures non utilisées supprimées, pas de `RenderTarget` oublié, atlas plutôt que dizaines de petites textures.

### 6. Mesurer et rapporter
- `renderer.info.render.calls`, `.triangles`, `.points`, `.lines` ; compteur FPS ; `r3f-perf` ou `stats.js` ; Spector.js pour les draw calls ; Chrome Performance pour long tasks et pics GPU ; heap snapshot avant/après navigation.
- Tester au minimum : mobile milieu de gamme, desktop, onglet caché, navigation aller-retour, WebGL désactivé, `prefers-reduced-motion: reduce`.
- Rendre un tableau avant/après (FPS médian/p95, draw calls, triangles, poids, mémoire) dans `docs/QUALITY_REPORT.md` ou un rapport dédié. Aucune affirmation sans mesure.

## Budgets indicatifs (à durcir selon le brief)
| Métrique | Mobile milieu de gamme | Desktop |
|---|---|---|
| FPS | 60 visés, 30 stables en mode économie | 60 |
| Draw calls visibles | < 100-150 | < 250 |
| Triangles visibles | < 150-300 k | < 2 M |
| DPR | <= 1,5 (2 max) | <= 2 |
| Ressources 3D initiales | < 2 Mo compressé | < 5 Mo |
| Texture unique | KTX2/WebP, 2048 max sauf nécessité | 4096 max |

Rappel : une texture RGBA 1024² non compressée occupe ~4 Mo de VRAM avant mipmaps.

## Anti-patterns à corriger immédiatement
| Anti-pattern | Correctif |
|---|---|
| `new THREE.Vector3()` / `new Geometry()` dans `useFrame` | Objets temporaires créés une fois hors de la boucle |
| Un mesh par particule / par objet | `InstancedMesh`, `Points`, GPGPU |
| `mesh.position.x += 0.01` par frame | `+= speed * delta` ou `damp` |
| Bloom + DOF + SSAO activés par défaut | Presets qualité, effets conditionnés au budget |
| `useGLTF` lourd dans le rendu critique | `preload`, Suspense, placeholder, import dynamique du Canvas |
| Canvas qui tourne en arrière-plan | `IntersectionObserver` + `visibilitychange` + `frameloop="demand"` |
| Ressources créées dans `useEffect` sans cleanup | `dispose()` et annulation des listeners/workers au démontage |
| ServiceWorker/Worker qui renvoie des objets clonés massifs | `ArrayBuffer` transférés (transfer list) |

## Accessibilité et repli
- Canvas décoratif : `aria-hidden="true"` + alternative textuelle dans le DOM ; information essentielle jamais uniquement en 3D ; contrôles clavier si interactif, focus visible.
- `prefers-reduced-motion: reduce` : figer la simulation, supprimer shake/auto-rotate/parallaxe, afficher une image statique ou une scène sans mouvement ; le mode économie doit rester utilisable.
- Détection WebGL avant montage du `<Canvas>` ; repli image/WebP, vidéo ou CSS ; pas d'écran noir.
- Charger le bundle 3D en import dynamique pour ne pas pénaliser LCP/INP de la page.

## Livrables attendus
1. Budget 3D chiffré et justification (dans `docs/DECISIONS.md` ou `docs/PERF_BUDGET_3D.md`).
2. Code structuré : `src/features/<feature>/three/` avec `Scene.tsx`, `objects/`, `shaders/`, `useSimulation.ts`, `perf.ts`.
3. Repli et variante mouvement réduit implémentés.
4. Rapport de mesures avant/après optimisation.

## Critères de vérification
- [ ] Intention, plateau cible et budgets écrits avant le code.
- [ ] Versions/API vérifiées, dépendances justifiées.
- [ ] Instancing/LOD/GPGPU utilisés là où nécessaire, aucun `new` dans `useFrame`.
- [ ] Animation indépendante du framerate, horloge unique.
- [ ] DPR plafonné/adaptatif, pause hors viewport et onglet caché.
- [ ] Ressources libérées au démontage (test aller-retour, pas de fuite mémoire).
- [ ] Repli WebGL et `prefers-reduced-motion` testés.
- [ ] Build/typecheck OK, FPS/draw calls/triangles/poids mesurés et consignés.
