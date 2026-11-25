import type { ReactNode } from "react";
import { SiteFooter } from "./SiteFooter";
import { SiteHeader } from "./SiteHeader";

type SiteShellProps = {
  children: ReactNode;
  variant?: "default" | "auth";
};

export function SiteShell({ children, variant = "default" }: SiteShellProps) {
  return (
    <>
      <SiteHeader />
      <main id="main-content" className={`site-main site-main--${variant}`}>{children}</main>
      {variant === "default" ? <SiteFooter /> : (
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
