# Règles du projet

Ce dépôt utilise l'environnement OpenCode « Frontend Premium » : 1 agent principal (`frontend-lead`), 7 sous-agents, 9 skills (dans `.opencode/`).

## Langue
Réponds et documente en français (code, identifiants et commits en anglais).

## Principes
- Autonomie élevée : décide seul des choix techniques réversibles, consigne-les dans `docs/DECISIONS.md`.
- Demande l'accord de l'utilisateur AVANT : suppression irréversible importante, dépense ou abonnement, publication ou déploiement public, modification majeure du périmètre.
- Un projet n'est terminé qu'après : build OK, audit QA sans problème bloquant, documentation à jour, rapport final.
- Pas de dépendance sans justification. Pas de secret dans le code ni dans la documentation.
- Accessibilité (WCAG AA), responsive, performance et `prefers-reduced-motion` sont des exigences par défaut.
- Évite les designs génériques de template.
- Vérifie versions et API dans la documentation officielle avant d'utiliser une bibliothèque.

## Documents vivants
`docs/PROJECT_BRIEF.md`, `docs/IMPLEMENTATION_PLAN.md`, `docs/DECISIONS.md`, `docs/QUALITY_REPORT.md`, `docs/WORKFLOW.md` : à actualiser pendant le développement.
