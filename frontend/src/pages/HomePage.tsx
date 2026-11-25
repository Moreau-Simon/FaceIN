import { prototypeStatus } from "../app/content";
import { pageFiles, pageUrl } from "../app/navigation";
import { ProofRays, RibbonArtwork } from "../components/visuals/Artwork";
import { CodeBlock } from "../components/ui/CodeBlock";
import { ContactForm } from "../components/ui/ContactForm";
import { WidgetCard } from "../components/home/WidgetCard";
import { DashboardVisual, IdentityVisual, NetworkVisual, PartnerLoginVisual, ProofVisual, SecurityVisual } from "../components/home/Widgets";
import { Reveal } from "../components/ui/Reveal";
import { BrandMark } from "../components/ui/BrandMark";
import { DemoBanner } from "../features/home/components/DemoBanner";

const compatibility = [
  "Biométrie locale",
  "Preuve cryptographique",
  "Réseau de nœuds",
  "Multi-service",
  "Multi-appareil",
  "Fuzzy extractor",
  "Révocation",
  "Métadonnées",
  "Journal chaîné",
  "Prototype",
];

function TrustTicker() {
  return (
    <div className="trust-ticker" aria-label="Briques et objectifs du projet">
      <div className="trust-ticker__track">
        {[...compatibility, ...compatibility].map((item, index) => (
          <span key={`${item}-${index}`} aria-hidden={index >= compatibility.length}>{item}</span>
        ))}
      </div>
    </div>
  );
}

const benefits = [
  {
    title: "Vers une connexion sans mot de passe",
    detail: "L’objectif est d’utiliser la biométrie comme point de départ d’une vérification. Le parcours complet reste à intégrer et à tester.",
  },
  {
    title: "Une capture destinée à rester locale",
    detail: "La conception visée prévoit que la biométrie brute soit traitée sur l’appareil. Cette propriété devra être confirmée par l’implémentation et l’analyse du flux réseau.",
  },
  {
    title: "Appareil perdu : une révocation à définir",
    detail: "La révocation devra être connue des nœuds avant de nouvelles authentifications. Son délai de propagation et son comportement en cas de panne restent à documenter.",
  },
];

export function HomePage() {
  return (
    <div className="home-page">
      <section className="home-hero grid-lines">
        <RibbonArtwork className="home-hero__ribbons" />
        <div className="container home-hero__inner">
          <Reveal className="home-hero__copy">
            <p className="hero-kpis">
              <span>Projet étudiant <b>en développement</b></span>
              <i aria-hidden="true" />
              <span>Vérification de bout en bout <b>à raccorder</b></span>
            </p>
            <p className="hero-footnote">{prototypeStatus}</p>
            <h1>
              Prouver son identité sans exposer sa biométrie.
            </h1>
            <p className="hero-footnote">FaceIN explore une authentification biométrique décentralisée : transmettre une preuve cryptographique plutôt que l’image du visage.</p>
            <div className="button-row">
              <a className="button button-primary" href={pageFiles.howItWorks}>Découvrir le fonctionnement <span className="button-arrow" aria-hidden="true" /></a>
              <a className="button button-outline" href={pageUrl(pageFiles.howItWorks, "architecture")}>Voir l’architecture <span className="button-arrow" aria-hidden="true" /></a>
            </div>
            <p className="hero-footnote"><span>Biométrie traitée localement (cible).</span><span>Preuve et réseau à construire.</span></p>
          </Reveal>
        </div>
      </section>

      <TrustTicker />

      <section className="home-section grid-lines">
        <div className="container">
          <div className="section-lead">
            <p className="lead-label">Le problème</p>
            <h2>Un visage ne se remplace pas comme un mot de passe. FaceIN étudie une approche où la biométrie brute n’a pas besoin d’être envoyée au serveur.</h2>
          </div>
          <div className="widget-grid widget-grid--two">
            <WidgetCard className="widget--partner" label="Parcours de connexion visé" title="Le parcours de démonstration prévu pour un service partenaire">
              {() => <PartnerLoginVisual />}
            </WidgetCard>
            <WidgetCard className="widget--security" label="Tableau de bord illustratif" title="Tableau de bord illustratif">
              {() => <SecurityVisual />}
            </WidgetCard>
          </div>
          <div className="section-lead">
            <p className="lead-label">Le projet en bref</p>
            <h2>Quatre idées, une cible à construire.</h2>
            <p>Biométrie locale, preuve cryptographique, réseau de nœuds et usage multi-service : ces éléments décrivent la cible, pas une solution finalisée.</p>
          </div>
          <div className="widget-grid widget-grid--three">
            <WidgetCard className="widget--proof" label="Preuve cryptographique (cible)" title="Preuve cryptographique (cible)">
              {() => <ProofVisual />}
            </WidgetCard>
            <WidgetCard className="widget--identity" label="Identité numérique (cible)" title="Identité liée à un appareil">
              {() => <IdentityVisual />}
            </WidgetCard>
            <WidgetCard className="widget--network" label="Réseau de nœuds (cible)" title="Réseau de nœuds (cible)">
              {() => <NetworkVisual />}
            </WidgetCard>
          </div>
          <WidgetCard className="widget--dashboard" label="Tableau de bord illustratif" title="Tableau de bord illustratif">
            {(expanded) => <DashboardVisual expanded={expanded} />}
          </WidgetCard>
          <p className="note">Données illustratives : aucun tableau de bord réel n’est connecté dans ce dépôt.</p>
        </div>
      </section>

      <section className="home-section home-section--tight grid-lines">
        <div className="container"><DemoBanner /></div>
      </section>

      <section className="security-section grid-lines" id="security">
        <div className="container">
          <h2 className="section-title section-title--center">Contrôle, révocation et limites</h2>
          <div className="security-metrics">
            <div><strong>0</strong><span>image brute à envoyer<br />dans la conception visée</span></div>
            <div><strong>4</strong><span>briques à réunir : biométrie,<br />preuve, réseau, multi-service</span></div>
            <div><strong>Seuil</strong><span>règle de décision<br />encore à définir</span></div>
            <div><strong>À venir</strong><span>révocation et propagation<br />entre les nœuds</span></div>
          </div>
          <div className="ray-field"><ProofRays /></div>
          <div className="people-grid" id="team">
            <div className="people-intro">
              <p className="lead-label">Ce que le projet doit encore traiter.</p>
              <h2>Les limites font partie de la conception.</h2>
              <h3>Pour vous : une biométrie qui ne devient pas un identifiant permanent</h3>
              <p>La biométrie brute ne doit pas être transmise aux nœuds. Les données dérivées et auxiliaires devront elles aussi être étudiées et sécurisées.</p>
              <a className="button button-primary" href={pageFiles.connection}>Voir le parcours de démonstration <span className="button-arrow" aria-hidden="true" /></a>
            </div>
            <div className="accordion-list">
              {benefits.map((item, index) => (
                <details key={item.title} open={index === 0}>
                  <summary>{item.title}<span className="accordion-plus" aria-hidden="true" /></summary>
                  <p>{item.detail}</p>
                </details>
              ))}
            </div>
          </div>
          <div className="audience-grid">
            <article><h3>Pour les services.</h3><p>Chaque service aurait sa configuration propre. L’isolation et la non-corrélation ne sont pas garanties automatiquement par les preuves cryptographiques.</p><a className="text-link" href={pageFiles.integration}>Voir la cible <span className="button-arrow" aria-hidden="true" /></a></article>
            <article><h3>Analyse des métadonnées.</h3><p>Fréquence, horaires ou service visé pourraient signaler un comportement inhabituel. Cette analyse ne remplace pas une validation biométrique.</p><a className="text-link" href={pageUrl(pageFiles.howItWorks, "privacy")}>En savoir plus <span className="button-arrow" aria-hidden="true" /></a></article>
            <article><h3>Journalisation et intégrité.</h3><p>Un journal chaîné et une synchronisation entre nœuds sont envisagés, mais ne seront présentés comme réalisés qu’après implémentation et vérification.</p><a className="text-link" href={pageUrl(pageFiles.howItWorks, "revocation")}>En savoir plus <span className="button-arrow" aria-hidden="true" /></a></article>
          </div>
        </div>
      </section>

      <section className="developer-section" id="developers">
        <div className="container">
          <div className="developer-heading">
            <div>
            <p className="lead-label lead-label--light">Intégration envisagée.</p>
            <h2>Un parcours d’intégration à définir.</h2>
            <p>Aucun SDK opérationnel n’est fourni dans ce dépôt.</p>
            </div>
            <dl className="developer-stats">
            <div><dt>Cible</dt><dd>un bouton à intégrer</dd></div>
            <div><dt>1</dt><dd>résultat à transmettre, format à définir</dd></div>
            <div><dt>0</dt><dd>donnée biométrique brute à recevoir (objectif)</dd></div>
            </dl>
          </div>
          <div className="developer-demo">
            <CodeBlock label="index.html" code={`<script src="facein-sdk.js"></script>\n\n<button\n  data-facein-login\n  data-service-id="VOTRE_ID"\n>\n  Se connecter avec FaceIN\n</button>`} />
            <div className="developer-preview">
              <span>Résultat</span>
              <div className="developer-preview__canvas">
                <a className="facein-button" href={pageUrl(pageFiles.connection, "login")}><BrandMark inverted /> Se connecter avec FaceIN</a>
              </div>
            </div>
          </div>
          <div className="developer-resources">
            <article><h3>Exemple de bouton.</h3><p>Le code illustre l’intégration visée, pas un composant prêt à l’emploi.</p><a className="text-link" href={pageUrl(pageFiles.integration, "button")}>Voir l’exemple <span className="button-arrow" aria-hidden="true" /></a></article>
            <article><h3>SDK JavaScript (à venir).</h3><p>L’apparence et le parcours restent à définir avec le futur SDK.</p><a className="text-link" href={pageUrl(pageFiles.integration, "script")}>Voir la cible <span className="button-arrow" aria-hidden="true" /></a></article>
            <article><h3>Module Python (à venir).</h3><p>La vérification des résultats côté serveur reste à concevoir.</p><a className="text-link" href={pageUrl(pageFiles.integration, "verify-token")}>Voir l’exemple <span className="button-arrow" aria-hidden="true" /></a></article>
          </div>
        </div>
      </section>

      <section className="home-section grid-lines" id="contact" aria-labelledby="contact-title">
        <div className="container contact-section">
          <div className="contact-section__intro">
            <p className="eyebrow">Parlons de votre projet.</p>
            <h2 id="contact-title">Contactez l’équipe FaceIN.</h2>
            <p>Décrivez votre besoin d’intégration ou posez-nous une question.</p>
          </div>
          <ContactForm />
        </div>
        <p className="note">Le formulaire de contact est une maquette et n’envoie pas encore de message.</p>
      </section>

      <section className="home-section home-section--tight grid-lines">
        <div className="container closing-section">
          <div>
            <h2>FaceIN est un prototype en développement.</h2>
            <p>Les parcours de cette page illustrent la cible du projet. Aucune authentification réelle n’est encore connectée.</p>
            <div className="button-row">
              <a className="button button-primary" href={pageFiles.connection}>Voir le parcours de démonstration <span className="button-arrow" aria-hidden="true" /></a>
            </div>
          </div>
          <div className="closing-links">
            <article><h3>Offres envisagées</h3><p>Des formules indicatives, sans paiement opérationnel.</p><a className="text-link" href={pageFiles.pricing}>Voir les offres <span className="button-arrow" aria-hidden="true" /></a></article>
            <article><h3>Guide d’intégration</h3><p>Les étapes et le SDK restent à construire.</p><a className="text-link" href={pageFiles.integration}>Lire le guide <span className="button-arrow" aria-hidden="true" /></a></article>
          </div>
        </div>
      </section>
    </div>
  );
}
