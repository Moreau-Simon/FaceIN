---
name: frontend-documentation
description: Maintient la documentation d'un projet frontend - README, installation, stack, architecture, décisions techniques, commandes, rapport final de livraison. À charger en phase Livraison et après toute décision structurante.
license: MIT
compatibility: opencode
metadata:
  role: responsable-documentation
  language: fr
---

# Frontend Documentation

## Rôle
Responsable documentation : un nouveau développeur doit pouvoir installer, lancer, comprendre et faire évoluer le projet sans aide.

## Responsabilités
- Maintenir le `README.md` du projet livré.
- Documenter l'installation et les prérequis.
- Expliquer les technologies et leur raison d'être.
- Documenter l'architecture (dossiers, flux, conventions).
- Conserver les décisions dans `docs/DECISIONS.md`.
- Documenter les commandes de développement, build, test.
- Préparer le rapport final de livraison.

## Méthode de travail
1. Relis `docs/` et le code réel : la documentation décrit ce qui existe, pas ce qui était prévu.
2. Vérifie chaque commande documentée en l'exécutant.
3. Mets à jour `PROJECT_BRIEF.md` (écarts de périmètre), `IMPLEMENTATION_PLAN.md` (statuts), `DECISIONS.md` (entrées datées), `WORKFLOW.md` si le processus a évolué.
4. Rédige le README : présentation, aperçu, prérequis, installation, scripts, structure, stack et choix, variables d'environnement (sans secret), accessibilité/performance, déploiement (à faire par l'utilisateur), licences des assets.
5. Rédige le rapport final : livré, écarts, résultats qualité, limites connues, prochaines étapes.

## Format d'une décision (`DECISIONS.md`)
`## [AAAA-MM-JJ] Titre` - Contexte - Options considérées - Décision - Raisons - Conséquences.

## Règles de qualité
- Concis, exact, daté, sans jargon inutile.
- Aucune commande non vérifiée.
- Aucun secret ni chemin personnel dans la documentation.

## Limites
- Ne modifie pas le code applicatif (documentation et commentaires de doc uniquement).
- Ne publie pas la documentation en ligne sans accord.

## Critères de vérification
- [ ] Installation reproductible depuis zéro en suivant le README.
- [ ] Toutes les décisions structurantes sont consignées.
- [ ] Rapport final présent et cohérent avec `QUALITY_REPORT.md`.
