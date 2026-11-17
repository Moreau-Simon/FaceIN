import { useEffect } from "react";
import { SiteShell } from "./components/SiteShell";
import { CommentCaMarchePage } from "./pages/CommentCaMarchePage";
import { ConnectionPage } from "./pages/ConnectionPage";
import { HomePage } from "./pages/HomePage";
import { IntegrationPage } from "./pages/IntegrationPage";
import { PricingPage } from "./pages/PricingPage";

const pages = {
  "index.html": { title: "FaceIN — Votre visage vous connecte", component: HomePage },
  "connexion.html": { title: "Créer un compte ou se connecter — FaceIN", component: ConnectionPage },
  "comment-ca-marche.html": { title: "Comment ça marche — FaceIN", component: CommentCaMarchePage },
  "integrer.html": { title: "Guide d’intégration — FaceIN", component: IntegrationPage },
  "tarif.html": { title: "Tarifs — FaceIN", component: PricingPage },
} as const;

export function App() {
  const fileName = window.location.pathname.split("/").pop() || "index.html";
  const page = pages[fileName as keyof typeof pages] ?? pages["index.html"];
  const PageComponent = page.component;

  useEffect(() => {
    document.title = page.title;
    const targetId = window.location.hash.slice(1);
    if (!targetId) return;

    const frame = window.requestAnimationFrame(() => {
      document.getElementById(targetId)?.scrollIntoView({ behavior: "instant" });
    });

    return () => window.cancelAnimationFrame(frame);
  }, [page.title]);

  return (
    <SiteShell>
      <PageComponent />
    </SiteShell>
  );
}
