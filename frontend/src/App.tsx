import { useEffect } from "react";
import { SiteShell } from "./components/SiteShell";
import { CommentCaMarchePage } from "./pages/CommentCaMarchePage";
import { ConnectionPage } from "./pages/ConnectionPage";
import { EspacePage } from "./pages/EspacePage";
import { HomePage } from "./pages/HomePage";
import { IntegrationPage } from "./pages/IntegrationPage";
import { PricingPage } from "./pages/PricingPage";

const pages = {
  "index.html": { title: "FaceIN — Connectez-vous avec votre visage, sans le partager", component: HomePage, variant: "default" },
  "connexion.html": { title: "Créer un compte ou se connecter — FaceIN", component: ConnectionPage, variant: "auth" },
  "espace.html": { title: "Mon espace — FaceIN", component: EspacePage, variant: "default" },
  "comment-ca-marche.html": { title: "Comment ça marche — FaceIN", component: CommentCaMarchePage, variant: "default" },
  "integrer.html": { title: "Guide d’intégration — FaceIN", component: IntegrationPage, variant: "default" },
  "tarif.html": { title: "Tarifs — FaceIN", component: PricingPage, variant: "default" },
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
    <SiteShell variant={page.variant}>
      <PageComponent />
    </SiteShell>
  );
}
