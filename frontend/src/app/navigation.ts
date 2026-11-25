/** Entrées HTML déclarées dans `vite.config.ts`. Toute URL interne part d'ici. */
export const pageFiles = {
  home: "index.html",
  connection: "connexion.html",
  espace: "espace.html",
  howItWorks: "comment-ca-marche.html",
  integration: "integrer.html",
  pricing: "tarif.html",
  about: "a-propos.html",
  privacy: "confidentialite.html",
  terms: "conditions-generales.html",
  legalNotice: "mentions-legales.html",
} as const;

export type PageFile = (typeof pageFiles)[keyof typeof pageFiles];

/** Construit une URL interne, avec ancre optionnelle. */
export function pageUrl(page: PageFile, hash?: string): string {
  return hash ? `${page}#${hash}` : page;
}

export const mainNavigation = [
  { label: "Fonctionnement", href: pageUrl(pageFiles.howItWorks) },
  { label: "Intégrer", href: pageUrl(pageFiles.integration) },
  { label: "Offres", href: pageUrl(pageFiles.pricing) },
  { label: "Contact", href: pageUrl(pageFiles.home, "contact") },
];

export const footerGroups = [
  {
    title: "Produit",
    links: [
      ["Fonctionnement", pageUrl(pageFiles.howItWorks)],
      ["Offres", pageUrl(pageFiles.pricing)],
      ["Ressources d’intégration", pageUrl(pageFiles.integration, "resources")],
      ["Parcours de démonstration", pageUrl(pageFiles.connection, "register")],
    ],
  },
  {
    title: "Développeurs",
    links: [
      ["Guide d’intégration", pageUrl(pageFiles.integration)],
      ["SDK JavaScript (à venir)", pageUrl(pageFiles.integration, "script")],
      ["Module Python (à venir)", pageUrl(pageFiles.integration, "verify-token")],
      ["Site de démonstration", pageUrl(pageFiles.connection)],
    ],
  },
  {
    title: "Projet",
    links: [
      ["À propos", pageUrl(pageFiles.about, "projet")],
      ["L’équipe", pageUrl(pageFiles.about, "equipe")],
      ["Contact", pageUrl(pageFiles.home, "contact")],
    ],
  },
  {
    title: "Légal",
    links: [
      ["Confidentialité", pageUrl(pageFiles.privacy)],
      ["CGV", pageUrl(pageFiles.terms)],
      ["Mentions légales", pageUrl(pageFiles.legalNotice)],
    ],
  },
];
