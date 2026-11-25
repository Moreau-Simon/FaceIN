import { useMemo, useState } from "react";
import { CodeBlock } from "../components/CodeBlock";
import { Reveal } from "../components/Reveal";

const integrationSteps = [
  {
    id: "declare-service",
    title: "1. Déclarer votre service",
    searchTerms: "identifiant clé serveur",
    content: (
      <>
        <p>Depuis votre espace, ajoutez votre site. Vous obtenez un identifiant de service et une clé secrète.</p>
        <p className="callout callout--warn"><strong>Gardez votre clé sur votre serveur.</strong> Ne l’ajoutez jamais au code de la page.</p>
      </>
    ),
  },
  {
    id: "script",
    title: "2. Ajouter le script",
    searchTerms: "HTML SDK balise",
    content: (
      <>
        <p>Ajoutez le SDK avant la fermeture de la balise <code>body</code>.</p>
        <CodeBlock label="HTML" code={'<script src="facein-sdk.js"></script>'} />
      </>
    ),
  },
  {
    id: "button",
    title: "3. Ajouter le bouton",
    searchTerms: "HTML data-facein-login service ID",
    content: (
      <>
        <p>Placez le bouton où vous le souhaitez. Voici le rendu :</p>
        <div className="integration-button-preview"><span className="facein-button">Se connecter avec FaceIN</span></div>
        <CodeBlock
          label="HTML"
          code={'<button data-facein-login\n  data-service-id="VOTRE_ID">\n  Se connecter avec FaceIN\n</button>'}
        />
      </>
    ),
  },
  {
    id: "verify-token",
    title: "4. Vérifier le jeton",
    searchTerms: "Python JWT token serveur",
    content: (
      <>
        <p>FaceIN vous transmet un jeton JWT signé, valable une heure. Vérifiez-le sur votre serveur avant d’ouvrir la session.</p>
        <CodeBlock
          label="Python"
          code={'from facein_verify import verify_token\n\nuser = verify_token(token, service_id="VOTRE_ID")\nif user.valid:\n    open_session(user.id)'}
        />
      </>
    ),
  },
];

const documentationIndex = [
  "Rechercher dans la doc",
  "Démarrer",
  "Vue d’ensemble",
  "Avant de commencer",
  "Intégration",
  "Déclarer votre service",
  "Ajouter le script",
  "Ajouter le bouton",
  "Vérifier le jeton",
  "Ressources",
  "Tester le parcours",
];

export function IntegrationPage() {
  const [query, setQuery] = useState("");
  const filteredSteps = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase("fr");
    if (!normalizedQuery) return integrationSteps;
    return integrationSteps.filter((step) =>
      `${step.title} ${step.id} ${step.searchTerms}`.toLocaleLowerCase("fr").includes(normalizedQuery),
    );
  }, [query]);

  return (
    <div className="page-integration">
      <section className="page-hero page-hero--single grid-lines">
        <div className="container page-hero__inner">
          <div>
          <p className="lead-label">Guide d’intégration</p>
          <h1>Intégrez FaceIN à votre site. <span>Vous ne recevez jamais de donnée biométrique, seulement un jeton.</span></h1>
          <div className="requirements" id="requirements">
            <span><i>✓</i> Un compte FaceIN</span>
            <span><i>✓</i> Un site en HTTPS (la caméra ne s’active pas en HTTP)</span>
            <span><i>✓</i> Un serveur qui peut vérifier un jeton JWT</span>
          </div>
          <p className="note">Le SDK n’est pas encore publié : les extraits ci-dessous présentent l’intégration prévue.</p>
          </div>
        </div>
      </section>

      <section className="container section-padding">
        <div className="docs-layout">
          <aside className="docs-sidebar">
            <label htmlFor="docs-search">{documentationIndex[0]}</label>
            <input id="docs-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)} />
            <nav aria-label="Sommaire de l’intégration">
              <h2>Démarrer</h2><a href="#overview">Vue d’ensemble</a><a href="#requirements">Avant de commencer</a>
              <h2>Intégration</h2>
              {integrationSteps.map((step) => <a key={step.id} href={`#${step.id}`}>{step.title.replace(/^\d+\.\s/, "")}</a>)}
              <h2>Ressources</h2><a href="#resources">Tester le parcours</a>
            </nav>
          </aside>
          <div className="docs-content">
            <div id="overview" className="docs-intro">
              <p className="lead-label">Vue d’ensemble</p>
              <h2>Avant de commencer</h2>
              <p>Il vous faut un compte FaceIN, un site en HTTPS (la caméra ne s’active pas en HTTP) et un serveur capable de vérifier un jeton JWT.</p>
            </div>
            {filteredSteps.length === 0 ? (
              <p className="empty-state" role="status">Aucune étape ne correspond à « {query} ».</p>
            ) : filteredSteps.map((step, index) => (
              <Reveal className="docs-step" key={step.id} id={step.id} delay={index * 0.035}>
                <span className="docs-step__number">{step.title.slice(0, 1)}</span>
                <div><h2>{step.title.replace(/^\d+\.\s/, "")}</h2>{step.content}</div>
              </Reveal>
            ))}
            <Reveal className="docs-next-step" id="resources">
              <span className="lead-label">Étape suivante</span>
              <h2>Testez le parcours vous-même</h2>
              <p>Créez une identité et connectez-vous pour voir exactement ce que vivront vos utilisateurs.</p>
              <a className="button button-primary" href="connexion.html#register">Essayer le parcours <span className="button-arrow" aria-hidden="true" /></a>
              <div className="resource-grid">
                <a href="#script"><b>HTML</b><span>Ajouter le script</span></a>
                <a href="#button"><b>HTML</b><span>Ajouter le bouton</span></a>
                <a href="#verify-token"><b>Python</b><span>Vérifier le jeton</span></a>
              </div>
            </Reveal>
          </div>
        </div>
      </section>
    </div>
  );
}
