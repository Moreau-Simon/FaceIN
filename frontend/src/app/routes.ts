import type { ComponentType } from "react";
import { CommentCaMarchePage } from "../features/how-it-works/CommentCaMarchePage";
import { ConnectionPage } from "../features/connection/ConnectionPage";
import { HomePage } from "../features/home/HomePage";
import { IntegrationPage } from "../features/integration/IntegrationPage";
import { EspacePage } from "../pages/EspacePage";
import { PricingPage } from "../features/pricing/PricingPage";
import { pageFiles } from "./navigation";

export type Route = {
  fileName: string;
  title: string;
  component: ComponentType;
  variant?: "default" | "auth";
};

export const routes: readonly Route[] = [
  { fileName: pageFiles.home, title: "FaceIN — Prouver son identité sans exposer sa biométrie", component: HomePage },
  { fileName: pageFiles.connection, title: "Créer un compte ou se connecter — FaceIN", component: ConnectionPage, variant: "auth" },
  { fileName: pageFiles.espace, title: "Mon espace — FaceIN", component: EspacePage },
  { fileName: pageFiles.howItWorks, title: "Fonctionnement envisagé — FaceIN", component: CommentCaMarchePage },
  { fileName: pageFiles.integration, title: "Guide d’intégration — FaceIN", component: IntegrationPage },
  { fileName: pageFiles.pricing, title: "Offres envisagées — FaceIN", component: PricingPage },
];

const fallbackRoute = routes[0];

/** Résout l'entrée HTML courante ; les URL inconnues tombent sur l'accueil. */
export function resolveRoute(pathname: string): Route {
  const fileName = pathname.split("/").pop() || pageFiles.home;
  return routes.find((route) => route.fileName === fileName) ?? fallbackRoute;
}

export function getCurrentRoute(): Route {
  return resolveRoute(window.location.pathname);
}
