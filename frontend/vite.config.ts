import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const root = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  base: "./",
  plugins: [react()],
  build: {
    outDir: "dist",
    rolldownOptions: {
      input: {
        home: resolve(root, "index.html"),
        connection: resolve(root, "connexion.html"),
        howItWorks: resolve(root, "comment-ca-marche.html"),
        integration: resolve(root, "integrer.html"),
        pricing: resolve(root, "tarif.html"),
      },
    },
  },
});
