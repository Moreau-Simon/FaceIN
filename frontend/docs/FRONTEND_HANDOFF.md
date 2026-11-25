# Reprise du frontend FaceIN

Ce document explique comment récupérer et lancer le frontend, ce qu’il contient déjà et ce qui reste à faire avant d’en faire un service réel ou de le publier.

## État actuel

Le dossier `frontend/` contient une application multipage construite avec React, TypeScript et Vite. C’est un prototype d’interface : les pages et les démonstrations locales sont présentes, mais le dépôt ne fournit ni API FaceIN ni service de production.

La structure principale est organisée ainsi :

```text
frontend/
├── index.html, connexion.html, comment-ca-marche.html, integrer.html, tarif.html
├── src/
│   ├── app/                 # composition, navigation et table des pages
│   ├── components/          # composants partagés (layout, UI, visuels)
│   ├── features/            # accueil, connexion, fonctionnement, intégration, tarifs
│   └── styles/site.css      # styles et design system
├── docs/                    # décisions, plan, qualité et guides
├── package.json
└── package-lock.json
```

Les cinq entrées HTML conservent leurs URL :

| Page | URL locale | État |
|---|---|---|
| Accueil | `/` | Présentation du projet et démonstrations visuelles |
| Connexion | `/connexion.html` | Parcours de démonstration, sans authentification réelle |
| Fonctionnement | `/comment-ca-marche.html` | Description du fonctionnement envisagé |
| Intégration | `/integrer.html` | Guide et exemples illustratifs, sans SDK ou endpoint disponible |
| Offres | `/tarif.html` | Tarifs et offres indicatifs, sans facturation connectée |

La scène du hero est une illustration 3D procédurale : un bouclier, des orbites et des nœuds lumineux. Elle ne contient pas de visage ni de SVG de remplacement. Son chargement est différé et elle respecte le réglage de mouvement réduit.

## Ce qui reste à faire ou à revoir

Les éléments ci-dessous sont un backlog proposé, pas des fonctionnalités déjà promises par le prototype.

### Priorité 0 — définir et connecter les services réels

1. **Écrire les contrats d’API.** Définir les endpoints, formats de requête/réponse, erreurs, délais, authentification, versionnement et environnements de test. Documenter les responsabilités du frontend et du backend.
2. **Implémenter l’authentification.** Relier les formulaires à un service, gérer les états de chargement, les erreurs, les sessions, la déconnexion et les réponses serveur. Ne pas traiter la validation locale actuelle comme une connexion effective.
3. **Préciser le parcours biométrique et la preuve.** Définir où et comment les données sont traitées, ce qui est transmis, la durée de conservation, la révocation et les consentements. Le prototype caméra n’effectue ni reconnaissance faciale ni vérification cryptographique réelle. Ne revendiquer ces propriétés qu’après implémentation et vérification.
4. **Rendre le formulaire de contact opérationnel.** Connecter une destination de réception, ajouter la validation serveur et une protection contre les abus, puis afficher des états de succès et d’échec fiables. Aujourd’hui, le formulaire ne transmet pas les messages.
5. **Connecter les offres à la facturation.** Confirmer les montants, conditions et règles d’abonnement (notamment les offres de groupe/Enterprise), puis intégrer le prestataire de paiement et ses états d’abonnement. Les prix affichés ne déclenchent aucun paiement.
6. **Fournir le vrai kit d’intégration.** Publier et documenter le SDK, les endpoints et des exemples testés. Les extraits actuels sont illustratifs et ne doivent pas être présentés comme une intégration utilisable.

### Priorité 1 — fiabiliser la qualité du frontend

1. **Ajouter des tests automatisés.** Aucun runner de test ou linter n’est actuellement configuré. Commencer par les routes, les formulaires et les interactions critiques ; ajouter des parcours navigateur pour l’inscription, le contact, le menu mobile et les pages multipages.
2. **Compléter l’audit d’accessibilité.** Vérifier au clavier et avec un lecteur d’écran les formulaires, dialogues, états d’erreur, contrastes et ordre du focus. Faire un contrôle WCAG complet avant publication ; le rapport qualité existant ne constitue pas un audit formel.
3. **Tester les navigateurs et appareils réels.** Refaire les parcours sur Safari, Firefox et Chromium, puis sur téléphone et tablette. Vérifier WebGL désactivé, mouvement réduit, redimensionnement, chargement direct de chaque URL et absence de débordement.
4. **Mesurer les performances.** Collecter LCP, INP et CLS, ainsi que le FPS et la consommation de la scène 3D sur un appareil mobile représentatif. Le build signale un chunk 3D supérieur à 500 kB minifié, bien que son poids gzip reste sous le budget défini : mesurer avant de décider s’il faut davantage le découper.
5. **Valider tous les textes et prix.** Faire confirmer les promesses produit, tarifs, mentions légales et conditions par les responsables du projet. Maintenir les avertissements « prototype », « cible » et « à venir » tant que les services correspondants ne sont pas opérationnels.

### Priorité 2 — préparer la livraison

- Choisir l’hébergement statique et vérifier qu’il sert correctement les cinq fichiers HTML.
- Ajouter une intégration continue qui exécute le contrôle TypeScript et le build sur chaque changement.
- Préparer les variables d’environnement et les secrets côté serveur ; ne jamais placer de secret dans le bundle frontend.
- Documenter les procédures de mise en production, de retour arrière et de signalement d’incidents.
- Mettre à jour `QUALITY_REPORT.md` après les vérifications, en distinguant clairement les tests automatisés, les contrôles manuels et les points non mesurés.

## Récupérer le projet

### Depuis GitHub avec Git

Prérequis : accès au dépôt, Git, Node.js `^20.19.0` ou `>=22.12.0` et npm.

```bash
git clone https://github.com/Moreau-Simon/FaceIN.git
cd FaceIN/frontend
npm ci
npm run dev
```

Vite affiche l’adresse locale dans le terminal, généralement `http://localhost:5173/`. Ouvre cette adresse dans un navigateur. Si le port est déjà utilisé, Vite en choisira un autre et affichera l’adresse correspondante. Pour arrêter le serveur, reviens au terminal et fais `Ctrl+C`.

Si le dépôt est privé, connecte-toi à GitHub ou utilise la méthode d’accès autorisée par le propriétaire du dépôt. Ne mets jamais de jeton ou de mot de passe dans une commande qui pourrait être partagée.

### Depuis une archive

Télécharge l’archive du dépôt depuis GitHub, décompresse-la, puis ouvre un terminal dans le dossier `frontend/` et exécute :

```bash
npm ci
npm run dev
```

### Vérifier ou préparer une version de production

Depuis `frontend/` :

```bash
npm run typecheck
npm run build
npm run preview
```

Le build est généré dans `frontend/dist/`. `npm run preview` sert ce build localement pour le vérifier avant déploiement. Ne modifie pas directement `dist/` : les fichiers y sont régénérés par le build.

Pour récupérer les changements ultérieurs après un clone, utilise `git pull --ff-only` depuis le dépôt, puis relance `npm ci` uniquement si `package-lock.json` a changé.

## Commandes disponibles

| Commande | Utilité |
|---|---|
| `npm run dev` | Démarre Vite en mode développement avec rechargement à chaud |
| `npm run typecheck` | Vérifie les types TypeScript (`tsc --noEmit`) |
| `npm run build` | Lance le contrôle TypeScript puis produit le build Vite |
| `npm run preview` | Sert localement le contenu de `dist/` |

Aucune commande de test automatisé ni de lint n’est disponible pour l’instant.

## Documents utiles

- `README.md` — installation rapide, architecture et scripts.
- `docs/IMPLEMENTATION_PLAN.md` — jalons déjà réalisés.
- `docs/QUALITY_REPORT.md` — résultats des builds et contrôles manuels, avec leurs réserves.
- `docs/PERF_BUDGET_3D.md` — contraintes de performance de la scène 3D.
- `docs/DECISIONS.md` — décisions techniques et éléments de contexte.
