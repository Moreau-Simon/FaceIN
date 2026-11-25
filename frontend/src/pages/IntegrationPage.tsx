import { useMemo, useState } from "react";
import { prototypeStatus } from "../app/content";
import { pageFiles } from "../app/navigation";
import { CodeBlock } from "../components/ui/CodeBlock";
import { Reveal } from "../components/ui/Reveal";

const docsSearchLabel = "Rechercher dans la doc";

const integrationSteps = [
  {
    id: "declare-service",
    title: "1. Déclarer votre service",
    searchTerms: "identifiant clé serveur",
    content: (
      <>
        <p>Dans l’espace prévu, chaque service aurait sa configuration propre : identité, droits demandés et règles d’accès. Le format des identifiants reste à définir.</p>
        <p className="callout callout--warn"><strong>Une clé de service resterait côté serveur.</strong> Elle ne devrait jamais être ajoutée au code de la page.</p>
      </>
    ),
  },
  {
    id: "script",
    title: "2. Ajouter le script",
    searchTerms: "HTML SDK balise",
    content: (
      <>
        <p>L’intégration visée passerait par un script ajouté avant la fermeture de la balise <code>body</code>. Aucun SDK opérationnel n’est fourni dans ce dépôt.</p>
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
        <p>Exemple de bouton envisagé :</p>
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
    title: "4. Vérifier le résultat",
    searchTerms: "Python jeton résultat serveur",
    content: (
      <>
        <p>La vérification côté serveur reste à définir. Si un jeton est retenu, sa durée de vie, son destinataire et sa révocation devront être précisés.</p>
        <CodeBlock
          label="Python · exemple de la maquette"
          code={'from facein_verify import verify_token\n\nuser = verify_token(token, service_id="VOTRE_ID")\nif user.valid:\n    open_session(user.id)'}
        />
      </>
    ),
  },
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
          <h1>Intégrer FaceIN : <span>le parcours visé</span></h1>
          <p className="note">Objectif : le service reçoit un résultat d’authentification, pas une donnée biométrique brute. Le format du jeton reste à définir.</p>
          <div className="requirements" id="requirements">
            <span><i>✓</i> Un compte FaceIN</span>
            <span><i>✓</i> Un site en HTTPS (la caméra ne s’active pas en HTTP)</span>
            <span><i>✓</i> Un serveur prêt à vérifier un résultat d’authentification</span>
          </div>
          <p className="note">{prototypeStatus} Les exemples ci-dessous ne sont reliés ni à un SDK ni à un endpoint opérationnel.</p>
          </div>
        </div>
      </section>

      <section className="container section-padding">
        <div className="docs-layout">
          <aside className="docs-sidebar">
            <label htmlFor="docs-search">{docsSearchLabel}</label>
            <input id="docs-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)} />
            <nav aria-label="Sommaire de l’intégration">
              <h2>Démarrer</h2><a href="#overview">Vue d’ensemble</a><a href="#requirements">Avant de commencer</a>
              <h2>Intégration</h2>
              {integrationSteps.map((step) => <a key={step.id} href={`#${step.id}`}>{step.title.replace(/^\d+\.\s/, "")}</a>)}
              <h2>Ressources</h2><a href="#resources">Site de démonstration</a><a href="#resources">SDK (à venir)</a><a href="#resources">Questions fréquentes</a>
            </nav>
          </aside>
          <div className="docs-content">
            <div id="overview" className="docs-intro">
              <p className="lead-label">Vue d’ensemble</p>
              <h2>Avant de commencer</h2>
              <p>Un compte FaceIN, un site en HTTPS et un serveur prêt à vérifier un résultat d’authentification dont le format reste à définir.</p>
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
              <h2>Suivre le parcours de démonstration</h2>
              <p>Consultez les écrans prévus ; aucune vérification réelle n’est effectuée ici.</p>
              <a className="button button-primary" href={pageFiles.connection}>Ouvrir la démo <span className="button-arrow" aria-hidden="true" /></a>
              <p className="note">Aucun SDK téléchargeable n’est fourni dans ce dépôt.</p>
              <div className="resource-grid">
                <a href="#script"><b>HTML</b><span>Ajouter le script</span></a>
                <a href="#button"><b>HTML</b><span>Ajouter le bouton</span></a>
                <a href="#verify-token"><b>Python</b><span>Vérifier le résultat</span></a>
              </div>
            </Reveal>
          </div>
        </div>
      </section>
    </div>
  );
}
