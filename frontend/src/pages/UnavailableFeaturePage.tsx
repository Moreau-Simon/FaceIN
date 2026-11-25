import { useEffect, useState } from "react";
import { pageFiles } from "../app/navigation";

type UnavailablePageProps = {
  title: string;
  description: string;
};

function UnavailableFeaturePage({ title, description }: UnavailablePageProps) {
  return (
    <section className="page-hero grid-lines">
      <div className="container page-hero__inner">
        <div>
          <p className="lead-label">Prototype FaceIN</p>
          <h1>{title}</h1>
          <p className="note">{description}</p>
          <p className="callout callout--warn" role="status">
            Cette action n’a pas été effectuée. Aucun compte ni aucune authentification n’a été créé.
          </p>
          <div className="button-row">
            <a className="button button-primary" href={pageFiles.home}>Retour à l’accueil <span className="button-arrow" aria-hidden="true" /></a>
            <a className="button button-outline" href={pageFiles.howItWorks}>Voir le fonctionnement <span className="button-arrow" aria-hidden="true" /></a>
          </div>
        </div>
        <div className="page-hero__network-art" aria-hidden="true"><span>A</span><i /><span>B</span><i /><span>C</span></div>
      </div>
    </section>
  );
}

export function ConnectionUnavailablePage() {
  const [hash, setHash] = useState(() => window.location.hash);

  useEffect(() => {
    const onHashChange = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const isLogin = hash === "#login";

  return (
    <UnavailableFeaturePage
      title={isLogin ? "La connexion FaceIN est indisponible." : "La création de compte FaceIN est indisponible."}
      description="Les modules nécessaires à l’inscription, à la caméra et à la vérification ne sont pas présents dans cette version du dépôt."
    />
  );
}

export function EspaceUnavailablePage() {
  return (
    <UnavailableFeaturePage
      title="L’espace FaceIN est indisponible."
      description="Les modules nécessaires aux connexions et à l’historique de l’espace client ne sont pas présents dans cette version du dépôt."
    />
  );
}
