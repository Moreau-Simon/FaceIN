import { pageFiles, pageUrl } from "../../../app/navigation";
import { CodeBlock } from "../../../components/ui/CodeBlock";

const snippet = `<script src="facein-sdk.js"></script>\n\n<button\n  data-facein-login\n  data-service-id="VOTRE_ID"\n>\n  Se connecter avec FaceIN\n</button>`;

export function DeveloperSection() {
  return (
    <section className="developer-section" id="developers">
      <div className="container">
        <div className="developer-heading">
          <div>
            <p className="eyebrow">Intégration envisagée.</p>
            <h2>Un parcours d’intégration à définir.</h2>
            <p>Aucun SDK opérationnel n’est fourni dans ce dépôt.</p>
          </div>
          <div className="developer-stats">
            <div><strong>Cible</strong><span>un bouton à intégrer</span></div>
            <div><strong>1</strong><span>résultat à transmettre, format à définir</span></div>
            <div><strong>0</strong><span>donnée biométrique brute à recevoir (objectif)</span></div>
          </div>
        </div>
        <div className="developer-demo">
          <div className="developer-code">
            <CodeBlock label="index.html · server.py" code={snippet} />
          </div>
          <div className="developer-preview">
            <span>Résultat</span>
            <div className="developer-preview__canvas"><a href={pageUrl(pageFiles.connection, "login")}><span className="mini-brand">F</span> Se connecter avec FaceIN</a></div>
          </div>
        </div>
        <div className="developer-resources">
          <article><h3>Exemple de bouton.</h3><p>Le code illustre l’intégration visée, pas un composant prêt à l’emploi.</p><a href={pageUrl(pageFiles.integration, "button")}>Voir l’exemple <span>›</span></a></article>
          <article><h3>SDK JavaScript (à venir).</h3><p>L’apparence et le parcours restent à définir avec le futur SDK.</p><a href={pageUrl(pageFiles.integration, "script")}>Voir la cible <span>›</span></a></article>
          <article><h3>Module Python (à venir).</h3><p>La vérification des résultats côté serveur reste à concevoir.</p><a href={pageUrl(pageFiles.integration, "verify-token")}>Voir l’exemple <span>›</span></a></article>
        </div>
      </div>
    </section>
  );
}
