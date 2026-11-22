# Rapport qualité

- **Date** : 2026-11-22
- **Périmètre** : six pages React (accueil, connexion, espace client, comment ça marche, intégrer, tarifs)
- **Verdict** : prêt pour une première version, avec les réserves listées plus bas.

## Résultats

| Vérification | Résultat |
|---|---|
| `npm install` puis `npm run build` | Réussi (TypeScript strict, Vite multipage). Le `package-lock.json` désynchronisé de la branche a été régénéré. |
| Débordement horizontal | Aucun à 360, 768, 1024 et 1440 px sur les six pages |
| Console navigateur | Aucune erreur JavaScript sur les six pages |
| Inscription de bout en bout | Réussie avec l’API de `capture_camera_photo` : caméra, modèles, descripteur 128D, coffre IndexedDB, engagement Poseidon, `POST /api/register` |
| Connexion | `GET /api/nonce` et défis de présence reçus et affichés. Non validée jusqu’au jeton : voir réserves. |
| Erreurs du parcours | Caméra refusée ou indisponible, pseudo inconnu sur l’appareil, API injoignable : messages explicites et bouton « Réessayer » |
| Espace client | Accès refusé sans session (redirection vers la connexion), compte à rebours, « Mettre fin », filtres de l’historique |
| Widgets de l’accueil | Survol, pression, ouverture agrandie animée, fermeture par Échap et clic extérieur, bascule d’offre, survol des barres |
| Démonstration guidée | Défilement automatique, pause, navigation par étape, fermeture clavier |
| Mouvement réduit | Animations désactivées ou figées avec `prefers-reduced-motion` |

## Réserves

- **Connexion complète non vérifiée ici** : le test s’est fait en navigateur automatisé, avec une photo comme caméra. Le calibrage du test de présence a échoué. C’est le comportement attendu face à une photo, mais l’environnement de test était aussi trop lent (environ 18 s par détection). La vérification finale par les nœuds (`POST /api/authenticate`) demande en plus le réseau de nœuds gRPC lancé avec `docker compose`. À tester sur un poste réel, avec une vraie caméra.
- **Historique des connexions** : il est enregistré sur l’appareil en attendant une route API. Les lignes « Exemple » disparaissent dès la première connexion venant d’un site partenaire.
- **Chiffres de l’accueil** : ce sont des exemples, signalés comme tels.
- **Formulaire de contact et SDK** : aucun envoi ni SDK publié, ce qui est signalé dans l’interface.

## Taille du build

- JavaScript : environ 493 kB (157 kB gzip). Les bibliothèques biométriques sont chargées à la demande, uniquement sur la page de connexion.
- CSS : environ 63 kB (14 kB gzip). La police Inter est auto-hébergée.
- Modèles et circuit (`public/facein/`) : environ 25 Mo, téléchargés uniquement au démarrage de la caméra.
