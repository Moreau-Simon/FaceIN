# FaceIN — frontend React

Application multipage en React et TypeScript, construite avec Vite. Les entrées HTML conservent les URLs statiques des cinq maquettes; aucun routeur serveur n’est nécessaire.

## Lancer l’application

Prérequis : Node.js `^20.19.0` ou `>=22.12.0` et npm.

```bash
npm ci
npm run dev
```

Commandes de validation et de livraison :

```bash
npm run typecheck
npm run build
npm run preview
```

Pages servies :

- `/` — accueil
- `/connexion.html` — inscription et connexion par le visage
- `/espace.html` — espace client (connexions en cours et historique), accessible une fois connecté
- `/comment-ca-marche.html` — explication du parcours prévu
- `/integrer.html` — guide et exemples d’intégration
- `/tarif.html` — offres provisoires

La connexion reprend le fonctionnement de la branche `capture_camera_photo` : visage analysé dans le navigateur (face-api.js), vecteur gardé dans IndexedDB, test de présence imposé par le serveur, preuve Groth16 générée localement, puis jeton JWT délivré par l’API Gateway.

Pour tester la connexion, démarrer l’API de la branche `capture_camera_photo` (port 8000). Une autre adresse peut être fournie au build :

```bash
VITE_FACEIN_API_URL=https://api.exemple.fr/api npm run build
```

La caméra exige HTTPS ou `localhost`. Le guide d’intégration présente des exemples illustratifs non reliés à un SDK ou à un endpoint disponible dans ce dépôt. Les chiffres et tableaux d’interface sont également signalés comme illustratifs.

Structure de l’application : `src/` contient les composants React et les pages; `styles/site.css` définit le design responsive; `index.html` et les quatre autres entrées HTML sont compilées dans `dist/`. Les fragments `accueil.js`, `connexion.js`, `comment-ca-marche.js`, `integrer.js` et `tarif.js` restent les références de contenu et ne sont pas des points d’entrée de l’application.

## Environnement OpenCode — Frontend Premium

Équipe d'agents IA pour concevoir des sites web modernes, premium, animés (et en 3D si pertinent) à partir d'une simple idée.

Contenu : **1 agent principal + 7 sous-agents**, **9 skills**, une configuration `opencode.json`, des documents de pilotage dans `docs/`.

## Prérequis
- [OpenCode](https://opencode.ai) installé (`opencode --version`).
- Node.js LTS et un gestionnaire de paquets (npm, pnpm ou yarn) pour les projets générés.
- Un fournisseur de modèle configuré dans OpenCode (`opencode auth login`).

## Installation

### Option A — Dans un projet (recommandé)
Décompresse l'archive à la racine de ton projet (ou d'un dossier vide) :
```bash
unzip opencode-frontend-premium.zip -d mon-site
cd mon-site
opencode
```
`frontend-lead` est l'agent par défaut (`default_agent` dans `opencode.json`).

### Option B — Globalement
Copie les agents et skills dans la configuration globale :
```bash
mkdir -p ~/.config/opencode/agents ~/.config/opencode/skills
cp -r .opencode/agents/* ~/.config/opencode/agents/
cp -r .opencode/skills/* ~/.config/opencode/skills/
```
Puis copie le contenu de `opencode.json` dans `~/.config/opencode/opencode.json` (fusionne si le fichier existe).

## Utilisation
Lance `opencode`, puis décris ton site :
> « Crée un site vitrine pour un studio de céramique : univers organique, animations au scroll, galerie immersive. »

L'agent suit les 9 phases de `docs/WORKFLOW.md`, délègue aux spécialistes, teste et documente. Il te demande ton accord uniquement avant : suppression irréversible importante, dépense/abonnement, publication/déploiement public, changement majeur de périmètre.

## Structure
```
.
├── opencode.json            # config : agent par défaut, instructions, permissions globales
├── AGENTS.md                # règles du projet (chargées automatiquement)
├── docs/
│   ├── PROJECT_BRIEF.md
│   ├── IMPLEMENTATION_PLAN.md
│   ├── DECISIONS.md
│   ├── QUALITY_REPORT.md
│   └── WORKFLOW.md
└── .opencode/
    ├── agents/              # 8 agents (format markdown + frontmatter)
    └── skills/<nom>/SKILL.md  # 9 skills
```

## Agents
| Agent | Mode | Rôle | Écriture |
|---|---|---|---|
| `frontend-lead` | primary | Orchestration, délégation, livraison | oui |
| `frontend-architect` | subagent | Stack et architecture | non |
| `ui-ux-designer` | subagent | Direction artistique, design system | docs seulement |
| `frontend-engineer` | subagent | Implémentation et tests | oui |
| `motion-specialist` | subagent | Animations avancées | oui |
| `webgl-specialist` | subagent | 3D / WebGL | oui |
| `qa-auditor` | subagent | Audit indépendant | `docs/QUALITY_REPORT.md` seulement |
| `frontend-researcher` | subagent | Recherche documentaire | non |

Les agents peuvent aussi être invoqués manuellement avec `@nom-de-l-agent`. Le lead est le seul à pouvoir déléguer (profondeur 1).

## Skills
| Skill | Chargé surtout par |
|---|---|
| `project-orchestrator` | frontend-lead |
| `discovery-and-planning` | frontend-lead |
| `frontend-architecture` | frontend-architect |
| `ui-ux-design-system` | ui-ux-designer |
| `frontend-implementation` | frontend-engineer |
| `advanced-web-animation` | motion-specialist |
| `webgl-experience` | webgl-specialist |
| `frontend-quality-and-performance` | qa-auditor, frontend-lead |
| `frontend-documentation` | frontend-lead |

Le skill « Frontend Architect » est nommé `frontend-architecture` pour ne pas être confondu avec l'agent `frontend-architect`.

## Sécurité et permissions
- Les commandes destructrices ou publiques (`rm -rf`, `git push`, `npm publish`, `vercel`, `netlify`, `wrangler`, `firebase deploy`…) demandent confirmation.
- `qa-auditor`, `frontend-architect` et `frontend-researcher` ne peuvent pas modifier le code.
- Adapte les motifs `bash` dans `.opencode/agents/*.md` à tes outils de déploiement.

## Personnalisation
- Modèle : ajoute `model: fournisseur/modèle` dans le frontmatter d'un agent, ou `"model"` dans `opencode.json`.
- Ajuste `temperature`, permissions et prompts directement dans `.opencode/agents/`.
- Les skills sont du Markdown : modifie-les sans redémarrage de configuration complexe (relance OpenCode si besoin).

## Dépannage
- Skill non trouvé : vérifie que `name` du frontmatter = nom du dossier et que le fichier s'appelle `SKILL.md` en majuscules.
- Agent absent : le fichier doit être dans `.opencode/agents/` et contenir `description`.
- Vérifie la compatibilité avec ta version : consulte https://opencode.ai/docs/agents, /skills, /permissions et /config.
