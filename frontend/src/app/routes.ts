import type { ComponentType } from "react";
import { CommentCaMarchePage } from "../pages/CommentCaMarchePage";
import { ConnectionUnavailablePage, EspaceUnavailablePage } from "../pages/UnavailableFeaturePage";
import { IntegrationPage } from "../pages/IntegrationPage";
import { HomePage } from "../pages/HomePage";
import { PricingPage } from "../pages/PricingPage";
import { AboutPage, LegalNoticePage, PrivacyPage, TermsPage } from "../pages/FooterPages";
import { pageFiles } from "./navigation";

export type Route = {
  fileName: string;
  title: string;
  component: ComponentType;
  variant?: "default" | "auth";
};

export const routes: readonly Route[] = [
  { fileName: pageFiles.home, title: "FaceIN — Prouver son identité sans exposer sa biométrie", component: HomePage },
  { fileName: pageFiles.connection, title: "Créer un compte ou se connecter — FaceIN", component: ConnectionUnavailablePage, variant: "auth" },
  { fileName: pageFiles.espace, title: "Mon espace — FaceIN", component: EspaceUnavailablePage },
  { fileName: pageFiles.howItWorks, title: "Fonctionnement envisagé — FaceIN", component: CommentCaMarchePage },
  { fileName: pageFiles.integration, title: "Guide d’intégration — FaceIN", component: IntegrationPage },
  { fileName: pageFiles.pricing, title: "Offres envisagées — FaceIN", component: PricingPage },
  { fileName: pageFiles.about, title: "À propos de FaceIN — Projet étudiant SAE 5", component: AboutPage },
  { fileName: pageFiles.privacy, title: "Confidentialité — FaceIN (prototype)", component: PrivacyPage },
  { fileName: pageFiles.terms, title: "Conditions générales — FaceIN", component: TermsPage },
  { fileName: pageFiles.legalNotice, title: "Mentions légales — FaceIN (à compléter)", component: LegalNoticePage },
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
