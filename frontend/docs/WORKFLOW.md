# Workflow du projet

Processus obligatoire suivi par `frontend-lead`. Ne jamais sauter de phase ; ne jamais conclure parce que « le code est écrit ».

| # | Phase | Agent(s) | Skill(s) | Livrable | Sortie de phase |
|---|---|---|---|---|---|
| 1 | Découverte | lead | discovery-and-planning | `PROJECT_BRIEF.md` (v1) | Besoin, cibles, objectifs, hypothèses clairs |
| 2 | Analyse | lead, researcher | discovery-and-planning | Contraintes dans le brief | Dépôt existant analysé, contraintes listées |
| 3 | Planification | lead | discovery-and-planning, project-orchestrator | `IMPLEMENTATION_PLAN.md`, liste de tâches | Tâches ordonnées + critères d'acceptation |
| 4 | Architecture | architect, researcher | frontend-architecture | Entrée dans `DECISIONS.md` | Stack et structure décidées |
| 5 | Direction artistique | ui-ux-designer | ui-ux-design-system | `DESIGN_SYSTEM.md` | Tokens et composants définis |
| 6 | Développement | engineer | frontend-implementation | Code fonctionnel | Build/lint/tests OK, critères validés |
| 7 | Animations | motion-specialist, webgl-specialist (si justifié) | advanced-web-animation, webgl-experience | Animations/3D intégrées | Perf mesurée, mouvement réduit OK |
| 8 | Contrôle qualité | qa-auditor, engineer (corrections) | frontend-quality-and-performance | `QUALITY_REPORT.md` | Aucun bloquant ouvert |
| 9 | Livraison | lead | frontend-documentation | README, rapport final | Docs à jour, installation reproductible |

## Boucle qualité (phase 8)
audit -> rapport -> corrections par `frontend-engineer`/`motion-specialist` -> ré-audit, jusqu'au verdict « Prêt » ou « Prêt avec réserves » (réserves acceptées par l'utilisateur).

## Points d'accord utilisateur
Suppression irréversible importante - dépense/abonnement - publication/déploiement public - changement majeur de périmètre.

## Délégation
Profondeur 1 : le lead délègue, les sous-agents ne délèguent pas.
