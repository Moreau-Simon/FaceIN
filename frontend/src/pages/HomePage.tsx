import { ProofRays, RibbonArtwork } from "../components/Artwork";
import { CodeBlock } from "../components/CodeBlock";
import { ContactForm } from "../components/ContactForm";
import { CountUp } from "../components/CountUp";
import { DemoWalkthrough } from "../components/home/DemoWalkthrough";
import { WidgetCard } from "../components/home/WidgetCard";
import { DashboardVisual, IdentityVisual, NetworkVisual, PartnerLoginVisual, ProofVisual, SecurityVisual } from "../components/home/Widgets";
import { Reveal } from "../components/Reveal";
import { BrandMark } from "../components/BrandMark";

const compatibility = ["Chrome", "Firefox", "Safari", "Edge", "Opera", "Brave", "React", "Vue.js", "Next.js", "Svelte"];

function TrustTicker() {
  return (
    <div className="trust-ticker" aria-label="Compatible avec les principaux navigateurs et frameworks">
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
    title: "Plus aucun mot de passe à retenir",
    detail: "Votre visage devient votre clé. Il n’est ni envoyé ni stocké par FaceIN : il reste dans le coffre de votre appareil.",
  },
  {
    title: "Une photo ne suffit pas à vous imiter",
    detail: "À chaque connexion, deux défis tirés au hasard (cligner des yeux, tourner la tête, sourire) vérifient qu’une personne réelle est devant la caméra.",
  },
  {
    title: "Vous gardez la main sur vos connexions",
    detail: "Votre espace client liste les sites auxquels vous êtes connecté. Vous pouvez mettre fin à une connexion à tout moment.",
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
              <span>Connexions vérifiées aujourd’hui <b>12 847</b></span>
              <i aria-hidden="true" />
              <span>Images de visage reçues <b className="kpi-zero">0</b></span>
            </p>
            <h1>
              Votre visage vous connecte. Il ne quitte jamais votre appareil.{" "}
              <span>Les sites vérifient une preuve mathématique, jamais votre image.</span>
            </h1>
            <div className="button-row">
              <a className="button button-primary" href="connexion.html#register">Créer un compte <span className="button-arrow" aria-hidden="true" /></a>
              <a className="button button-outline" href="integrer.html">Intégrer FaceIN <span className="button-arrow" aria-hidden="true" /></a>
            </div>
            <p className="hero-footnote">Chiffres d’exemple, donnés à titre d’illustration.</p>
          </Reveal>
        </div>
      </section>

      <TrustTicker />

      <section className="home-section grid-lines">
        <div className="container">
          <div className="section-lead">
            <h2>Une connexion qui ne demande rien d’autre que vous. <span>Inscription, connexion, révocation : tout se passe sur votre appareil, et un réseau indépendant vérifie le reste.</span></h2>
          </div>
          <div className="widget-grid widget-grid--two">
            <WidgetCard className="widget--partner" label="Connexion sur un site partenaire" title="Connectez-vous à n’importe quel site partenaire, d’un simple regard">
              {() => <PartnerLoginVisual />}
            </WidgetCard>
            <WidgetCard className="widget--security" label="Niveau de sécurité" title="Choisissez votre niveau de sécurité">
              {() => <SecurityVisual />}
            </WidgetCard>
          </div>
          <div className="widget-grid widget-grid--three">
            <WidgetCard className="widget--proof" label="Preuve à divulgation nulle" title={<>Prouvez qui vous êtes,<br />sans jamais le révéler</>}>
              {() => <ProofVisual />}
            </WidgetCard>
            <WidgetCard className="widget--identity" label="Identité numérique" title="Une identité numérique qui n’appartient qu’à vous">
              {() => <IdentityVisual />}
            </WidgetCard>
            <WidgetCard className="widget--network" label="Réseau de vérification" title="Vérifiée par un réseau de serveurs indépendants">
              {() => <NetworkVisual />}
            </WidgetCard>
          </div>
          <WidgetCard className="widget--dashboard" label="Tableau de bord partenaire" title="Ajoutez la connexion par le visage à votre site">
            {(expanded) => <DashboardVisual expanded={expanded} />}
          </WidgetCard>
        </div>
      </section>

      <section className="home-section home-section--tight grid-lines">
        <div className="container">
          <Reveal className="demo-banner">
            <div className="demo-banner__copy">
              <h2>Voyez FaceIN en action</h2>
              <p>Le parcours de connexion en cinq étapes, sans jargon.</p>
              <DemoWalkthrough />
            </div>
            <RibbonArtwork className="demo-banner__art" />
          </Reveal>
        </div>
      </section>

      <section className="security-section grid-lines" id="security">
        <div className="container">
          <h2 className="section-title section-title--center">Une sécurité que tout le monde peut vérifier</h2>
          <div className="security-metrics">
            <div><strong><CountUp value={0} /></strong><span>image de visage reçue par nos serveurs</span></div>
            <div><strong><CountUp value={128} /></strong><span>valeurs décrivent votre visage</span></div>
            <div><strong>2 sur 3</strong><span>serveurs suffisent pour valider</span></div>
            <div><strong><CountUp value={60} suffix=" s" /></strong><span>de validité pour chaque défi, à usage unique</span></div>
          </div>
          <div className="ray-field"><ProofRays /></div>
          <div className="people-grid">
            <div className="people-intro">
              <h2>Pensé pour chacun. <span>Que vous vous connectiez ou que vous intégriez FaceIN, tout reste simple.</span></h2>
              <a className="button button-primary" href="connexion.html#register">Créer un compte <span className="button-arrow" aria-hidden="true" /></a>
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
            <article><h3>Pour les sites partenaires</h3><p>Ajoutez un bouton et recevez un jeton vérifié, sans jamais traiter de donnée biométrique.</p><a className="text-link" href="integrer.html">Lire le guide <span className="button-arrow" aria-hidden="true" /></a></article>
            <article><h3>Contre la fraude</h3><p>Chaque connexion utilise un défi unique, valable 60 secondes : une preuve interceptée ne peut pas être rejouée.</p><a className="text-link" href="comment-ca-marche.html">Comprendre la sécurité <span className="button-arrow" aria-hidden="true" /></a></article>
            <article><h3>Dans le temps</h3><p>Votre photo de référence se renouvelle tous les 6 mois si vous êtes mineur, chaque année sinon.</p><a className="text-link" href="comment-ca-marche.html#renewal">En savoir plus <span className="button-arrow" aria-hidden="true" /></a></article>
          </div>
        </div>
      </section>

      <section className="developer-section" id="developers">
        <div className="container">
          <div className="developer-heading">
            <div>
              <p className="lead-label lead-label--light">Pour les développeurs</p>
              <h2>Un script, un bouton, une vérification côté serveur.</h2>
              <p>Vous ne recevez jamais de donnée biométrique, seulement un jeton JWT signé.</p>
            </div>
            <dl className="developer-stats">
              <div><dt>2</dt><dd>balises pour ajouter le bouton</dd></div>
              <div><dt>1</dt><dd>jeton à vérifier par connexion</dd></div>
              <div><dt>0</dt><dd>donnée biométrique reçue</dd></div>
            </dl>
          </div>
          <div className="developer-demo">
            <CodeBlock label="index.html" code={`<script src="facein-sdk.js"></script>\n\n<button\n  data-facein-login\n  data-service-id="VOTRE_ID"\n>\n  Se connecter avec FaceIN\n</button>`} />
            <div className="developer-preview">
              <span>Résultat</span>
              <div className="developer-preview__canvas">
                <a className="facein-button" href="connexion.html#login"><BrandMark inverted /> Se connecter avec FaceIN</a>
              </div>
            </div>
          </div>
          <div className="developer-resources">
            <article><h3>Bouton prêt à l’emploi</h3><p>Deux balises à copier-coller, et le bouton est en ligne.</p><a className="text-link" href="integrer.html#button">Voir l’exemple <span className="button-arrow" aria-hidden="true" /></a></article>
            <article><h3>SDK JavaScript</h3><p>Gardez la main sur l’apparence et le parcours.</p><a className="text-link" href="integrer.html#script">Ajouter le script <span className="button-arrow" aria-hidden="true" /></a></article>
            <article><h3>Vérification côté serveur</h3><p>Contrôlez la signature du jeton avant d’ouvrir la session.</p><a className="text-link" href="integrer.html#verify-token">Lire la documentation <span className="button-arrow" aria-hidden="true" /></a></article>
          </div>
        </div>
      </section>

      <section className="home-section grid-lines" id="contact" aria-labelledby="contact-title">
        <div className="container contact-section">
          <div className="contact-section__intro">
            <h2 id="contact-title">Parlons de votre projet.</h2>
            <p>Un besoin d’intégration, une question sur la sécurité ou les offres ? Écrivez-nous.</p>
          </div>
          <ContactForm />
        </div>
      </section>

      <section className="home-section home-section--tight grid-lines">
        <div className="container closing-section">
          <div>
            <h2>Prêt à essayer ? <span>Créez votre identité en une minute, ou intégrez FaceIN à votre site.</span></h2>
            <div className="button-row">
              <a className="button button-primary" href="connexion.html#register">Créer un compte <span className="button-arrow" aria-hidden="true" /></a>
            </div>
          </div>
          <div className="closing-links">
            <article><h3>Découvrez les offres</h3><p>Standard ou Renforcée, selon votre besoin.</p><a className="text-link" href="tarif.html">Voir les tarifs <span className="button-arrow" aria-hidden="true" /></a></article>
            <article><h3>Intégrez en 10 minutes</h3><p>Un guide pas à pas pour votre site.</p><a className="text-link" href="integrer.html">Lire le guide <span className="button-arrow" aria-hidden="true" /></a></article>
          </div>
        </div>
      </section>
    </div>
  );
}
