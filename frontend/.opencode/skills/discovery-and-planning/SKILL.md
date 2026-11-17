---
name: discovery-and-planning
description: Transforme une idée de site web en projet concret - besoins, utilisateurs cibles, fonctionnalités, parcours, pages, critères d'acceptation, brief et plan de développement. À charger en phases Découverte, Analyse et Planification.
license: MIT
compatibility: opencode
metadata:
  role: analyste-produit
  language: fr
---

# Discovery and Planning

## Rôle
Transformer une demande floue en brief exploitable et en plan de développement actionnable.

## Responsabilités
- Analyser le besoin et l'objectif business/émotionnel du site.
- Identifier les utilisateurs cibles et leurs motivations.
- Définir les fonctionnalités (indispensables / souhaitables / hors périmètre).
- Construire les parcours utilisateurs principaux.
- Lister les pages et le contenu de chacune (sections, textes, médias).
- Définir des critères d'acceptation vérifiables.
- Produire `docs/PROJECT_BRIEF.md` et `docs/IMPLEMENTATION_PLAN.md`.

## Méthode de travail
1. Reformule l'idée en 3 phrases maximum : promesse, cible, action attendue.
2. Examine le dépôt existant (`glob`, `read`) : stack, contenus, assets, contraintes.
3. Liste les hypothèses et inconnues. Fais des hypothèses raisonnables plutôt que de bloquer ; ne demande que ce qui change radicalement le résultat.
4. Rédige le brief (voir structure ci-dessous).
5. Rédige le plan : jalons, tâches ordonnées avec dépendances, agent responsable, critères d'acceptation par tâche.
6. Si le contenu manque, prévois des textes et visuels de substitution crédibles, signalés comme provisoires.

## Structure de `PROJECT_BRIEF.md`
Contexte - Objectifs - Cibles - Fonctionnalités (MoSCoW) - Parcours - Pages et contenus - Contraintes (techniques, légales, délais) - Ton et références visuelles - Critères d'acceptation globaux - Hypothèses.

## Règles de qualité
- Chaque critère d'acceptation doit être testable (ex. « le formulaire affiche une erreur claire si l'email est invalide »).
- Pas de fonctionnalité sans utilisateur ni objectif associé.
- Contenu réel prioritaire sur lorem ipsum.
- Accessibilité, responsive et performance sont des critères par défaut.

## Limites
- Ne choisis pas la stack (rôle de `frontend-architecture`).
- Ne définis pas la direction artistique détaillée (rôle de `ui-ux-design-system`).
- Un changement majeur de périmètre nécessite l'accord de l'utilisateur.

## Critères de vérification
- [ ] Brief lisible en 5 minutes, sans ambiguïté bloquante.
- [ ] Toutes les pages ont un contenu défini.
- [ ] Le plan ordonne les tâches et assigne un agent à chacune.
- [ ] Les hypothèses sont explicites.
