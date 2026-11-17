# Rapport qualité

- **Date** : 2026-11-17
- **Périmètre** : build de production et cinq pages React
- **Verdict** : prêt avec réserves — l'interface et les démonstrations sont opérationnelles, mais aucune API FaceIN n'est disponible dans ce dépôt.

## Résultats

| Vérification | Résultat |
|---|---|
| `npm install` | Réussi; 0 vulnérabilité signalée par npm |
| `npm run build` | Réussi; TypeScript strict puis Vite 8 multipage |
| Pages dans le serveur de prévisualisation | Les cinq URL renvoient HTTP 200 |
| Responsive | 360, 768, 1024 et 1440 px; aucun débordement horizontal sur les cinq pages |
| Navigation et ancres | Contact atteint le formulaire depuis la page Tarifs; aucune ancre locale manquante ni ID dupliqué |
| Console navigateur | Aucune erreur JavaScript ou console pendant le contrôle des pages |
| Widget d’aperçu | Dialogue supérieur, verrouillage du défilement, focus/restauration, Échap, clic sur l’overlay, sélection d’offre, mouvement réduit et rendu mobile vérifiés |
| Navigation de l’en-tête | « Télécharger » et « À propos » retirés; Contact mène au formulaire |
| Tarifs | Standard gratuit, Renforcée à 2,99 €/mois et Enterprise par groupe vérifiés |
| Formulaire de contact | Validation et avertissement vérifiés; aucun message n’est envoyé sans service configuré |
| Parcours d'inscription | Validation invalide bloquée; formulaire valide ouvre l'étape de démonstration et son avertissement |
| Autres interactions | Onglets, menu mobile, recherche « Python »/aucun résultat, FAQ, copie de code, lien de contact et message de révocation vérifiés |
| Clavier et mouvement réduit | Lien d'évitement visible au focus; préférence `prefers-reduced-motion` vérifiée |

## Taille du build

- JavaScript : 426,34 kB (131,57 kB gzip).
- CSS : 63,67 kB (14,51 kB gzip).
- Les métriques LCP/INP/CLS n'ont pas été mesurées.

## Contraste et accessibilité

Contrastes calculés pour les principaux tokens sur fond blanc : `--ink` 15,54:1, `--muted` 5,43:1, `--primary` 6,19:1 et `--soft-muted` 5,20:1. Le focus clavier est visible, les champs ont des labels, les FAQ utilisent les éléments natifs `details/summary`, et les graphiques décoratifs ont un nom accessible.

Ce contrôle n'est pas un audit WCAG automatisé complet; certains textes minuscules dans les maquettes illustratives restent à revoir lors d'une validation d'accessibilité formelle.

## Corrections réalisées

- Identifiants des dégradés SVG rendus uniques entre illustrations.
- Débordement horizontal du code sur petit écran corrigé; toutes les pages passent désormais les quatre largeurs testées.
- Ancres du guide d'intégration et chemins des cinq entrées vérifiés.
- Exports JSX bruts inutilisés retirés après migration de leurs rendus vers les composants React.
- Les widgets principaux de l’accueil peuvent être agrandis en premier plan dans un dialogue accessible.
- Un aperçu produit interactif reprend les codes de composition Stripe avec une illustration locale et des indicateurs explicitement fictifs.
- Le bouton de contact de la section finale a été retiré à la demande; les autres contenus de cette section sont conservés.
- Le formulaire de contact et les tarifs demandés sont intégrés; l’absence de service de soumission et de facturation est signalée clairement.
- Révocation, téléchargement et authentification ne prétendent pas appeler un service absent; les limites sont annoncées dans l'interface.
- Les animations SVG et au scroll respectent `prefers-reduced-motion`.
- Le flux caméra est arrêté/nettoyé lors de l'arrêt, du changement d'étape et du démontage du composant.

## Réserves restantes

- Aucun backend HTTP, SDK téléchargeable, compte, reconnaissance faciale, révocation ou jeton réel n'est fourni par ce projet; ces éléments ne sont pas simulés comme fonctionnels.
- Le formulaire de contact est une maquette validable mais ne transmet pas les messages tant qu’un canal de réception n’est pas configuré.
- Les offres et prix sont affichés, mais aucun abonnement ni paiement n’est encore connecté à un service de facturation.
- L'aperçu caméra réel n'a pas été activé pendant le contrôle; il dépend d'une permission explicite et d'un appareil compatible.
- Les tarifs, mentions légales et affirmations produit doivent être confirmés avant publication.
- Un audit d'accessibilité formel et des mesures de performance réelles restent à effectuer.
