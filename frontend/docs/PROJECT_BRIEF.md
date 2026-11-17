# Brief projet FaceIN

- **Statut** : validé pour implémentation frontend
- **Dernière mise à jour** : 2026-11-16

## Contexte

FaceIN présente un parcours d'authentification biométrique qui affirme garder l'image et le vecteur facial sur l'appareil, et ne transmettre qu'une preuve cryptographique. Le frontend fourni est composé de cinq exports de maquettes JSX bruts, non exécutables sans build ni structure React.

## Objectifs

- Transformer toutes les pages en une application React maintenable.
- Préserver les textes et exemples présents dans les cinq maquettes.
- Reproduire les captures d'accueil avec une direction visuelle premium inspirée des principes éditoriaux de Stripe, sans reprendre ses textes ou ses ressources.
- Distinguer clairement les démonstrations visuelles des fonctions réellement connectées à un service.

## Cibles

- Utilisateurs qui découvrent FaceIN, ses garanties et ses offres.
- Développeurs et sites partenaires qui consultent le guide d'intégration.
- Utilisateurs qui parcourent le prototype d'inscription et de connexion.

## Fonctionnalités (MoSCoW)

### Must
- Pages Accueil, Connexion/Inscription, Comment ça marche, Intégrer et Tarifs.
- Contenu de la maquette conservé, y compris les exemples, FAQ et libellés provisoires.
- Navigation réelle, responsive et utilisable au clavier.
- Parcours de démonstration explicitement identifié comme non connecté à une authentification.
- Build statique reproductible et instructions de lancement.

### Should
- Copie des extraits de code avec retour de succès/erreur.
- Validation native des formulaires et aperçu caméra local avec arrêt/nettoyage du flux.
- FAQ accessible et états d'interaction cohérents.
- Animations sobres et compatibles avec `prefers-reduced-motion`.

### Could
- Intégration de l'API d'authentification si un contrat HTTP supporté est fourni.
- Enrichissement des illustrations de preuve avec des données réellement validées.

### Won't (dans ce périmètre)
- Affirmer qu'une identité est créée, qu'un visage est reconnu ou qu'un jeton est délivré sans API vérifiable.
- Publier ou déployer l'application.
- Modifier la configuration du backend ou du dépôt en dehors de `frontend/`.

## Parcours principaux

1. Découvrir la proposition et les principes de confidentialité, puis ouvrir le parcours de démonstration.
2. Comprendre les étapes d'une vérification et les données qui restent locales ou transitent.
3. Suivre le guide d'intégration, copier les exemples et consulter les tarifs provisoires.

## Pages et contenus

- **Accueil** : navigation, métriques illustratives, hero, compatibilité, maquettes de connexion/tableau de bord, bénéfices, vidéo/démonstration, statistiques, FAQ/accordéons, intégration et footer.
- **Connexion** : étapes pseudo/visage/terminé, inscription, connexion, renouvellement, révocation, erreurs et liens légaux.
- **Comment ça marche** : cinq étapes, données locales/envoyées, renouvellement et questions fréquentes.
- **Intégrer** : prérequis, déclaration du service, script, bouton, vérification JWT, exemples HTML/Python et ressources.
- **Tarifs** : offres Standard, Renforcée et Sur mesure, tableau comparatif et FAQ; prix et avantages restent explicitement provisoires.

## Contraintes

- React est obligatoire. Le projet doit rester statique et simple à servir; aucune API HTTP frontend n'est confirmée dans le dépôt.
- Le système doit distinguer les affirmations produit vérifiées des textes et statistiques de la maquette.
- Responsive, navigation clavier, contrastes WCAG AA et réduction des animations sont requis.
- Les fichiers et modifications restent dans `frontend/`.

## Ton et références visuelles

Confiant, précis et transparent. Utiliser les captures fournies comme référence de composition; s'inspirer de l'espace, de la typographie, des dégradés contrôlés et du raffinement d'interaction de Stripe sans copier sa marque, ses textes ni ses assets.

## Critères d'acceptation globaux

- Les cinq pages se construisent et se chargent directement en statique.
- Tous les textes de la source sont conservés ou repérables dans la page correspondante.
- Chaque contrôle visible effectue une action réelle ou est explicitement présenté comme illustration.
- Aucun débordement horizontal aux largeurs 360, 768, 1024 et 1440 px.
- Les états focus, erreur et succès sont perceptibles; la préférence de mouvement réduit est respectée.
- Aucun appel à une API non disponible et aucune fausse confirmation d'authentification.

## Hypothèses

- Les nombres de connexion, tableaux et éléments d'interface des captures sont des exemples de présentation, pas des données temps réel.
- L'aperçu caméra n'effectue ni extraction de caractéristiques, ni persistance, ni envoi.
- Les textes tarifaires et certaines garanties nécessitent une validation produit/légale.
