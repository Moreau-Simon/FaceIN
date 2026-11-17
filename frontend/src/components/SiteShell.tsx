import { useState } from "react";
import type { ReactNode } from "react";
import { BrandMark } from "./BrandMark";

const navigation = [
  { label: "Comment ça marche", href: "comment-ca-marche.html" },
  { label: "Intégrer", href: "integrer.html" },
  { label: "Tarifs", href: "tarif.html" },
  { label: "Contact", href: "index.html#contact" },
];

export function SiteHeader() {
  const [menuOpen, setMenuOpen] = useState(false);
  const currentPage = window.location.pathname.split("/").pop() || "index.html";

  return (
    <>
      <a className="skip-link" href="#main-content">
        Aller au contenu
      </a>
      <header className="site-header">
        <div className="site-header__inner">
          <a className="brand" href="index.html" aria-label="FaceIN — accueil">
            <BrandMark />
            <span>FaceIN</span>
          </a>
          <button
            className="menu-toggle"
            type="button"
            aria-expanded={menuOpen}
            aria-controls="primary-navigation"
            onClick={() => setMenuOpen((open) => !open)}
          >
            <span className="sr-only">{menuOpen ? "Fermer le menu" : "Ouvrir le menu"}</span>
            <span className="menu-toggle__icon" aria-hidden="true">
              <span />
              <span />
            </span>
          </button>
          <nav
            className={`site-nav${menuOpen ? " is-open" : ""}`}
            id="primary-navigation"
            aria-label="Navigation principale"
          >
            <div className="site-nav__links">
              {navigation.map((item) => (
                <a
                  key={item.label}
                  href={item.href}
                  aria-current={item.href === currentPage ? "page" : undefined}
                  onClick={() => setMenuOpen(false)}
                >
                  {item.label}
                </a>
              ))}
            </div>
            <div className="site-nav__actions">
              <a className="button button-outline button-small" href="connexion.html#login">
                Se connecter
              </a>
              <a className="button button-primary button-small" href="connexion.html#register">
                Créer un compte <span aria-hidden="true">↗</span>
              </a>
            </div>
          </nav>
        </div>
      </header>
    </>
  );
}

const footerGroups = [
  {
    title: "Produit",
    links: [
      ["Comment ça marche", "comment-ca-marche.html"],
      ["Tarifs", "tarif.html"],
      ["Télécharger", "integrer.html#resources"],
      ["Créer un compte", "connexion.html#register"],
    ],
  },
  {
    title: "Développeurs",
    links: [
      ["Guide d’intégration", "integrer.html"],
      ["SDK JavaScript", "integrer.html#script"],
      ["Module Python", "integrer.html#verify-token"],
      ["Site de démonstration", "connexion.html"],
    ],
  },
  {
    title: "Projet",
    links: [
      ["À propos", "index.html#team"],
      ["L’équipe", "index.html#team"],
      ["Contact", "index.html#contact"],
    ],
  },
  {
    title: "Légal",
    links: [
      ["Confidentialité", "comment-ca-marche.html#privacy"],
      ["CGV", "index.html#legal-notice"],
      ["Mentions légales", "index.html#legal-notice"],
    ],
  },
];

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="site-footer__main">
        <div className="site-footer__brand">
          <a className="brand" href="index.html">
            <BrandMark />
            <span>FaceIN</span>
          </a>
          <p>Une identité numérique qui n’appartient qu’à vous.</p>
          <span className="language-link">France (français)</span>
        </div>
        {footerGroups.map((group) => (
          <nav
            className="footer-group"
            key={group.title}
            aria-label={group.title}
          >
            <h2>{group.title}</h2>
            {group.links.map(([label, href]) => (
              <a key={label} href={href}>
                {label}
              </a>
            ))}
          </nav>
        ))}
      </div>
      <div className="site-footer__bottom">
        <small>© 2026 FaceIN, projet SAE 5</small>
        <p id="legal-notice">
          Les tarifs et informations légales présentés restent à confirmer.
        </p>
        <span>FaceIN</span>
      </div>
    </footer>
  );
}

type SiteShellProps = {
  children: ReactNode;
};

export function SiteShell({ children }: SiteShellProps) {
  return (
    <>
      <SiteHeader />
      <main id="main-content">{children}</main>
      <SiteFooter />
    </>
  );
}
