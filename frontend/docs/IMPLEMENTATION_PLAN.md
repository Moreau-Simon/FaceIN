# Plan d'implémentation

- **Statut** : terminé
- **Dernière mise à jour** : 2026-11-16

## Jalons

| Jalon | Contenu | Statut |
|---|---|---|
| 1. Audit et contenu | Inventaire des fragments, interactions, API et captures | Terminé |
| 2. Architecture et design | Choix React/build, structure et tokens documentés | Terminé |
| 3. Fondations React | Entrées multi-pages, composants communs et styles globaux | Terminé |
| 4. Pages et contenu | Migrer les cinq pages et conserver les textes de la source | Terminé |
| 5. Interactions | Navigation, formulaires de démo, aperçu caméra, copie, FAQ | Terminé |
| 6. Animations | Micro-interactions et apparitions au scroll, mouvement réduit | Terminé |
| 7. Qualité et livraison | Build, responsive, accessibilité, rapport et README | Terminé |
| 8. Remplacement du modèle 3D | Créer un sceau d’identité 3D procédural, sans SVG au chargement ; respecter le mouvement réduit et le repli WebGL | Terminé |

## Tâches

| ID | Tâche | Responsable | Dépendances | Critères d'acceptation | Statut |
|---|---|---|---|---|---|
| audit | Comprendre les maquettes, les contrats API et les contraintes de service | Lead | — | Pages et fonctions réelles/inexistantes identifiées | Terminé |
| architecture | Choisir React, build statique, TypeScript, navigation et dépendances | Architecte / Lead | audit | Choix comparés et documentés, versions officielles vérifiées | Terminé |
| design | Définir tokens, hiérarchie, composants, breakpoints et mouvement | Designer / Lead | audit | Guide de design utilisable et contraste vérifiable | Terminé |
| foundation | Installer le socle React et le build multi-page | Ingénieur frontend | architecture, design | Chaque URL HTML produit son shell React; build déterministe | Terminé |
| pages | Implémenter les cinq pages et réintégrer tous les textes source | Ingénieur frontend | foundation, design | Contenu comparé à chaque fragment d'origine | Terminé |
| interactions | Ajouter navigation, copies, FAQ et démonstration caméra explicitement locale | Ingénieur frontend | pages | Pas de fonction affichée sans action ou mention d'illustration | Terminé |
| motion | Implémenter les animations retenues et leur repli réduit | Spécialiste animation / Lead | pages, design | Nettoyage des effets; mouvement réduit testé | Terminé |
| qa | Tester build, routes, formulaires, responsive, clavier, contraste, console | QA / Lead | pages, interactions, motion | Aucun bloquant; rapport avec preuves et limites | Terminé |
| delivery | Documenter installation, scripts, architecture et risques | Documentation / Lead | qa | Installation reproductible et docs synchronisées | Terminé |
| hero-3d | Remplacer le ruban par un sceau 3D procédural, sans SVG au chargement ; garder le chargement différé, le mode immobile, le message WebGL et la pause hors écran | Lead | research, motion | 12 draw calls max, moins de 30 000 triangles, sans débordement, build et métriques consignés | Terminé |

## Découpage technique proposé

```text
frontend/
├── index.html, connexion.html, comment-ca-marche.html, integrer.html, tarif.html
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── components/
│   ├── pages/
│   ├── features/auth-demo/
│   └── lib/
├── styles/
├── public/
├── docs/
├── package.json, package-lock.json
└── vite.config.ts
```

Les URLs multi-pages préservent les entrées HTML, le chargement direct et un déploiement statique sans réécriture serveur. Stack retenue : React 19, TypeScript 7, Vite 8 et Motion for React; le réseau et les exemples du projet ne justifient pas de dépendance 3D. Vite 8 et son plugin React requièrent Node `^20.19.0 || >=22.12.0`.
