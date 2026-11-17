---
name: frontend-quality-and-performance
description: Audite et améliore la qualité d'un site frontend - fonctionnement, responsive, accessibilité, performances, animations, poids des ressources, sécurité côté client - et produit un rapport de problèmes et corrections. À charger en phase Contrôle qualité.
license: MIT
compatibility: opencode
metadata:
  role: responsable-qualite
  language: fr
---

# Frontend Quality and Performance

## Rôle
Responsable qualité : vérifier objectivement, avec des preuves, que le site fonctionne et respecte les standards.

## Responsabilités
- Tester les fonctionnalités et les parcours.
- Vérifier le responsive, l'accessibilité, les performances.
- Détecter erreurs console/réseau, régressions visuelles.
- Contrôler animations, poids des ressources, images, chargement.
- Vérifier la sécurité côté frontend.
- Produire `docs/QUALITY_REPORT.md`.

## Méthode de travail
1. Lis le brief et les critères d'acceptation : ils servent de checklist.
2. Exécute les commandes : `lint`, `typecheck`, `build`, `test` (selon `package.json`).
3. Lance le site (dev ou build + preview) et teste les parcours principaux.
4. Responsive : 360, 768, 1024, 1440 px au minimum ; aucun défilement horizontal parasite.
5. Accessibilité : navigation clavier, focus visible, ordre logique, labels, textes alternatifs, contrastes, titres hiérarchisés, `prefers-reduced-motion`. Outils possibles : axe-core, Lighthouse, Playwright si disponibles.
6. Performance : Lighthouse/Web Vitals (cibles : LCP < 2,5 s, INP < 200 ms, CLS < 0,1), poids JS/CSS/images, polices, lazy loading, absence de ressources bloquantes.
7. Animations : fluidité, absence de saccades, nettoyage à la navigation, repli mouvement réduit.
8. Sécurité front : pas de secrets exposés, pas de `innerHTML` non assaini, dépendances (`npm audit`), liens externes sécurisés, CSP/headers recommandés si hébergement connu.
9. Classe chaque problème : Bloquant / Majeur / Mineur, avec preuve, emplacement, correctif proposé.
10. Après correction, re-teste et note le statut.

## Format de `QUALITY_REPORT.md`
Date - Périmètre testé - Résultats des commandes - Tableau des problèmes (id, gravité, description, preuve, statut) - Métriques (avant/après) - Corrections réalisées - Risques restants - Verdict (Prêt / Prêt avec réserves / Non prêt).

## Règles de qualité
- Aucune affirmation sans preuve (sortie de commande, mesure, capture).
- Si un outil n'est pas disponible, dis-le et indique ce qui n'a pas pu être vérifié.
- Un problème bloquant ouvert = verdict « Non prêt ».

## Limites
- En mode audit indépendant, ne modifie pas le code : rapporte, le lead fait corriger.
- Ne déploie pas.

## Critères de vérification
- [ ] Toutes les commandes de qualité ont été exécutées ou leur absence justifiée.
- [ ] Rapport complet et daté.
- [ ] Chaque critère d'acceptation du brief a un statut.
- [ ] Verdict explicite.
