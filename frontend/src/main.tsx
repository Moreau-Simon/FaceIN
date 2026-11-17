import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "../styles/site.css";

const mountNode = document.getElementById("root");

if (!mountNode) {
  throw new Error("Élément racine React introuvable.");
}

createRoot(mountNode).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
