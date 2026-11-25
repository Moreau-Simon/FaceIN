import { footerGroups, pageFiles } from "../../app/navigation";
import { BrandMark } from "../ui/BrandMark";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="site-footer__main container">
        <div className="site-footer__brand">
          <a className="brand" href={pageFiles.home}>
            <BrandMark />
            <span>Face<b>IN</b></span>
          </a>
          <p>Prouver son identité sans exposer sa biométrie.</p>
          <span className="language-link">France (français)</span>
        </div>
        {footerGroups.map((group) => (
          <nav className="footer-group" key={group.title} aria-label={group.title}>
            <h2>{group.title}</h2>
            {group.links.map(([label, href]) => (
              <a key={label} href={href}>
                {label}
              </a>
            ))}
          </nav>
        ))}
      </div>
      <div className="site-footer__bottom container">
        <small>© 2026 FaceIN, projet SAE 5</small>
        <p>
          Les tarifs et informations légales présentés restent à confirmer.
        </p>
        <span>FaceIN</span>
      </div>
    </footer>
  );
}
