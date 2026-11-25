import { useEffect, useState } from "react";
import { getCurrentRoute } from "../../app/routes";
import { mainNavigation, pageFiles, pageUrl } from "../../app/navigation";
import { BrandMark } from "../ui/BrandMark";

export function SiteHeader() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const currentPage = getCurrentRoute().fileName;

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

  return (
    <>
      <a className="skip-link" href="#main-content">
        Aller au contenu
      </a>
      <header className={`site-header${scrolled ? " is-scrolled" : ""}`}>
        <div className="site-header__inner">
          <a className="brand" href={pageFiles.home} aria-label="FaceIN — accueil">
            <BrandMark />
            <span>Face<b>IN</b></span>
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
              {mainNavigation.map((item) => (
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
              <a className="button button-outline button-small" href={pageUrl(pageFiles.connection, "login")}>
                Voir la démo
              </a>
              <a className="button button-primary button-small" href={pageUrl(pageFiles.connection, "register")}>
                Tester le parcours <span className="button-arrow" aria-hidden="true" />
              </a>
            </div>
          </nav>
        </div>
      </header>
    </>
  );
}
