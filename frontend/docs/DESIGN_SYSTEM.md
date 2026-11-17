# Direction artistique et design system FaceIN

## Concept

**La preuve se voit; la donnée reste privée.** Une composition éditoriale lumineuse et précise rend le chemin local → preuve → consensus compréhensible sans exposer de données biométriques.

## Principes visuels

1. Grande typographie et espaces généreux pour donner confiance et hiérarchie.
2. Motifs abstraits de preuve/réseau inspirés des captures, pas d'assets ou de textes Stripe.
3. Bleu encre et blanc pour la lisibilité; accents cobalt, lilas, corail et ambre réservés aux actions et visualisations.
4. Les panneaux de code et données utilisent une composition dense distincte des sections éditoriales.
5. Métriques et maquettes sont identifiées comme illustratives tant qu'elles ne viennent pas d'une source réelle.

## Tokens de départ

| Token | Valeur | Usage |
|---|---|---|
| `--ink` | `#0A2540` | Titres et texte principal |
| `--muted` | `#596B85` | Texte secondaire courant |
| `--soft-muted` | `#5F6E82` | Annotations secondaires |
| `--primary` | `#533AFD` | Liens et actions |
| `--blue` | `#3F85FF` | Motifs de réseau |
| `--surface` | `#FFFFFF` | Cartes |
| `--canvas` | `#F7F9FC` | Fond général |
| `--line` | `#E5EDF5` | Bordures et séparateurs |
| `--lilac` | `#F4F2FF` | Fonds d'accent |
| `--radius-card` | `18px` | Rayon de carte par défaut |
| `--content` | `1200px` | Largeur maximale éditoriale |
| `--duration-fast` / `--duration-medium` | `180ms` / `320ms` | Transitions courtes |

Typographie : sans-serif de marque avec fallback système pour le contenu; monospace seulement pour les exemples code. Les polices distantes ne sont pas chargées afin d'éviter une requête tierce par défaut.

## Grille et responsive

- Conteneur éditorial centré, largeur maximale approximative de 1200 px.
- Grille desktop 12 colonnes, avec hero asymétrique et visualisation réseau.
- Passage à deux colonnes à tablette, puis une colonne sur mobile; marges latérales fluides.
- Breakpoints d'implémentation : 1080 px (grilles), 820 px (navigation/tablette), 620 px (mobile).
- Pas de largeur fixe ni de positionnement absolu pour le contenu principal.

## Composants

- **Header** : marque, navigation de pages, CTA; menu clavier/tactile sur petit écran.
- **Button/Link** : primaire, secondaire, texte; hover, focus visible, active, disabled; commandes principales d'au moins 44 px.
- **Hero/ProofVisual** : titre éditorial, actions et illustration CSS/SVG accessible.
- **Metric/MockDashboard** : données de maquette étiquetées « exemple ».
- **StepList/Disclosure** : étapes et accordéons natifs clavier.
- **CodeBlock** : exemple non exécutable par défaut, copie avec confirmation/erreur.
- **AuthDemo** : pseudo et consentement validés; aperçu caméra uniquement si l'utilisateur l'active, arrêt explicite et nettoyage des tracks.
- **PricingCard/Table** : contenu conservé et statut tarifaire provisoire clairement signalé.

## Mouvement

- Micro-interactions : 150–250 ms, uniquement `transform` et `opacity`.
- Révélation au scroll : légère, une fois, sans masquer le contenu avant l'observation.
- Héro : dérive lente des rubans et tracé ponctuel du réseau; aucune animation continue indispensable.
- FAQ, onglets et menu : transitions courtes liées à une action.
- `prefers-reduced-motion: reduce` désactive parallaxe, défilement lissé et révélations.
- Pas de 3D à ce stade : un motif SVG/CSS rend le réseau plus léger et lisible.

## Accessibilité

- Contraste visé : WCAG AA, 4.5:1 pour le texte courant, 3:1 pour le grand texte et composants.
- HTML sémantique; labels explicites; états communiqués autrement que par la couleur.
- Focus clavier visible, ordre DOM cohérent, textes alternatifs pertinents.
- Animations non bloquantes, respect du mouvement réduit, aucune cible interactive sous 44 px.

## Contrôle

Les contrastes sont conçus pour viser WCAG AA sur les textes principaux; les annotations des maquettes demandent une vérification dédiée. Les métriques des captures restent illustratives jusqu'à confirmation d'une source backend.
