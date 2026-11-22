import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { endAllConnections } from "../lib/facein/connections";
import { clearSession, getSession } from "../lib/facein/session";
import { BrandMark } from "./BrandMark";

const navigation = [
  { label: "Comment ça marche", href: "comment-ca-marche.html" },
  { label: "Intégrer", href: "integrer.html" },
  { label: "Tarifs", href: "tarif.html" },
  { label: "Contact", href: "index.html#contact" },
];

export function Brand({ inverted = false }: { inverted?: boolean }) {
  return (
    <a className={`brand${inverted ? " brand--inverted" : ""}`} href="index.html" aria-label="FaceIN, retour à l’accueil">
      <BrandMark inverted={inverted} />
      <span>Face<b>IN</b></span>
    </a>
  );
}

export function SiteHeader() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const session = getSession();
  const currentPage = window.location.pathname.split("/").pop() || "index.html";

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    document.body.classList.toggle("menu-open", menuOpen);
    return () => document.body.classList.remove("menu-open");
  }, [menuOpen]);

  function logout() {
    if (session) endAllConnections(session.userId);
    clearSession();
    window.location.assign("index.html");
  }

  return (
    <>
      <a className="skip-link" href="#main-content">Aller au contenu</a>
      <header className={`site-header${scrolled ? " is-scrolled" : ""}`}>
        <div className="site-header__inner">
          <Brand />
          <button
            className="menu-toggle"
            type="button"
            aria-expanded={menuOpen}
            aria-controls="primary-navigation"
            onClick={() => setMenuOpen((open) => !open)}
          >
            <span className="sr-only">{menuOpen ? "Fermer le menu" : "Ouvrir le menu"}</span>
            <span className="menu-toggle__icon" aria-hidden="true"><span /><span /></span>
          </button>
          <nav className={`site-nav${menuOpen ? " is-open" : ""}`} id="primary-navigation" aria-label="Navigation principale">
            <div className="site-nav__links">
              {navigation.map((item) => (
                <a key={item.label} href={item.href} aria-current={item.href === currentPage ? "page" : undefined} onClick={() => setMenuOpen(false)}>
                  {item.label}
                </a>
              ))}
            </div>
            <div className="site-nav__actions">
              {session ? (
                <>
                  <button className="nav-text-button" type="button" onClick={logout}>Se déconnecter</button>
                  <a className="button button-primary button-small" href="espace.html" aria-current={currentPage === "espace.html" ? "page" : undefined}>
                    Mon espace <span className="button-arrow" aria-hidden="true" />
                  </a>
                </>
              ) : (
                <>
                  <a className="nav-text-button" href="connexion.html#login">Se connecter</a>
                  <a className="button button-primary button-small" href="connexion.html#register">
                    Créer un compte <span className="button-arrow" aria-hidden="true" />
                  </a>
                </>
              )}
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
      ["Créer un compte", "connexion.html#register"],
      ["Se connecter", "connexion.html#login"],
    ],
  },
  {
    title: "Développeurs",
    links: [
      ["Guide d’intégration", "integrer.html"],
      ["Ajouter le bouton", "integrer.html#button"],
      ["Vérifier le jeton", "integrer.html#verify-token"],
    ],
  },
  {
    title: "Projet",
    links: [
      ["Pourquoi FaceIN", "index.html#security"],
      ["Contact", "index.html#contact"],
    ],
  },
  {
    title: "Légal",
    links: [
      ["Confidentialité", "comment-ca-marche.html#privacy"],
      ["Mentions légales", "index.html#legal-notice"],
    ],
  },
];

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="site-footer__main container">
        <div className="site-footer__brand">
          <Brand />
          <p>Une identité numérique qui n’appartient qu’à vous.</p>
        </div>
        {footerGroups.map((group) => (
          <nav className="footer-group" key={group.title} aria-label={group.title}>
            <h2>{group.title}</h2>
            {group.links.map(([label, href]) => <a key={label} href={href}>{label}</a>)}
          </nav>
        ))}
      </div>
      <div className="site-footer__bottom container">
        <small>© 2026 FaceIN · Projet SAÉ 5</small>
        <p id="legal-notice">Tarifs et conditions en cours de validation.</p>
      </div>
    </footer>
  );
}

type SiteShellProps = { children: ReactNode; variant?: "default" | "auth" };

export function SiteShell({ children, variant = "default" }: SiteShellProps) {
  return (
    <>
      <SiteHeader />
      <main id="main-content" className={`site-main site-main--${variant}`}>{children}</main>
      {variant === "default" && <SiteFooter />}
      {variant === "auth" && (
        <footer className="auth-footer container">
          <small>© 2026 FaceIN</small>
          <a href="index.html#contact">Contact</a>
          <a href="comment-ca-marche.html#privacy">Confidentialité</a>
          <a href="index.html#legal-notice">Mentions légales</a>
        </footer>
      )}
    </>
  );
}
