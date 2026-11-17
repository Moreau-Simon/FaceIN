import { CodeBlock } from "../components/CodeBlock";
import { NetworkSphere, ProofRays, RibbonArtwork } from "../components/Artwork";
import { ContactForm } from "../components/ContactForm";
import { ExperienceWidget } from "../components/ExperienceWidget";
import { Reveal } from "../components/Reveal";
import { SectionHeading } from "../components/SectionHeading";
import { ZoomableWidget } from "../components/ZoomableWidget";

const connectionRows = [
  ["Nouveau : Les Ateliers", "France", "1", "100 %"],
  ["Atelier Lune", "—", "7 513", "99,2 %"],
  ["Studio Kora", "Belgique", "1 352", "98,7 %"],
  ["Biblio+", "—", "1 122", "99,5 %"],
  ["Vélo Nomade", "Suisse", "3 290", "98,9 %"],
  ["Maison Sel", "—", "302", "99,0 %"],
  ["Campus Nord", "Canada", "2 021", "99,4 %"],
  ["Pixel Café", "—", "594", "97,8 %"],
];

const compatibility = [
  "Chrome",
  "Firefox",
  "Safari",
  "Edge",
  "Opera",
  "Brave",
  "React",
  "Vue.js",
  "Next.js",
  "Svelte",
];

function TrustTicker() {
  return (
    <div className="trust-ticker" aria-label="Navigateurs et frameworks">
      <div className="trust-ticker__track">
        {[...compatibility, ...compatibility].map((item, index) => (
          <span key={`${item}-${index}`}>{item}</span>
        ))}
      </div>
    </div>
  );
}

function PartnerBrowserMockup() {
  return (
    <div className="browser-mockup browser-mockup--partner">
      <div className="browser-chrome">
        <span className="window-dots" aria-hidden="true"><i /><i /><i /></span>
        <span>atelier lune</span>
        <nav aria-label="Navigation du site illustré">
          <span>Boutique</span><span>Journal</span><span>Compte</span>
        </nav>
      </div>
      <div className="partner-login">
        <p>Connexion à votre compte</p>
        <div className="face-scan" aria-hidden="true"><span>✦</span></div>
        <span className="mock-caption">L’image reste sur cet appareil</span>
        <div className="mock-primary-button"><span className="mini-brand">F</span> Connecté avec FaceIN</div>
      </div>
      <div className="verification-popover">
        <div className="popover-head"><span className="window-dots"><i /><i /><i /></span><span>verify.facein.fr</span></div>
        <strong>Récapitulatif de la vérification</strong>
        <div className="verification-line"><span>Vecteur calculé localement</span><b>128 valeurs</b></div>
        <div className="verification-line"><span>Image supprimée</span><b className="state-ok">✓</b></div>
        <div className="verification-line"><span>Preuve générée</span><b>zk-SNARK</b></div>
        <div className="node-list"><span>Nœud A <b>✓</b></span><span>Nœud B <b>✓</b></span><span>Nœud C <b>!</b></span></div>
        <div className="mock-timeout">Délai dépassé</div>
        <div className="popover-consensus"><span>Consensus <b>2 sur 3</b></span><strong>Connexion autorisée</strong></div>
      </div>
    </div>
  );
}

function SecurityMockup() {
  return (
    <aside className="security-mockup">
      <p className="mockup-title">Choisissez votre niveau de sécurité</p>
      <div className="security-plan">
        <span className="plan-icon"><span className="mini-brand">F</span></span>
        <div><strong>Offre Renforcée</strong><small>Vecteur de 256 valeurs</small></div>
        <span className="pill">ZK</span>
        <small>Sécurité</small>
        <div className="security-meter"><i /></div>
        <div className="plan-foot"><span>Temps de connexion</span><b>un peu plus long</b></div>
      </div>
      <div className="chart-card">
        <small>Connexions des 30 derniers jours</small>
        <strong>1 248</strong>
        <div className="bar-chart" role="img" aria-label="Graphique illustratif des connexions">
          {Array.from({ length: 14 }, (_, index) => <i key={index} />)}
        </div>
      </div>
    </aside>
  );
}

function ProofCard() {
  return (
    <article className="proof-card proof-card--visual">
      <div className="proof-card__top"><h3>Prouvez qui vous êtes,<br />sans jamais le révéler</h3></div>
      <div className="commitment-art" aria-hidden="true">
        <div className="commitment-ring" />
        <span className="commitment-label">vecteur · ••••••••</span>
        <span className="proof-valid"><i>✓</i> Preuve valide</span>
      </div>
    </article>
  );
}

function IdentityCard() {
  return (
    <article className="proof-card proof-card--identity">
      <div className="proof-card__top"><h3>Une identité numérique qui n’appartient qu’à vous</h3></div>
      <div className="identity-art">
        <div className="identity-glow"><span className="mini-brand">F</span><b>ZK</b></div>
        <div className="identity-details"><strong>manon_m</strong><span>Engagement actif</span><b>FaceIN</b></div>
      </div>
    </article>
  );
}

function ConsensusCard() {
  return (
    <article className="proof-card proof-card--network">
      <div className="proof-card__top"><h3>Vérifiée par un réseau de serveurs indépendants</h3></div>
      <NetworkSphere />
    </article>
  );
}

function DashboardMockup() {
  return (
    <article className="dashboard-showcase">
      <div className="dashboard-showcase__intro">
        <span className="mini-brand">F</span>
        <h3>Ajoutez la connexion par le visage à votre site</h3>
        <p>Voyez FaceIN en action, sans exposer de donnée biométrique.</p>
        <div className="dashboard-login-card">
          <div className="dashboard-user"><span>AL</span><b>Atelier Lune<small>Connexion à votre compte</small></b></div>
          <div className="choice is-selected"><i /> Mon visage <span>FaceIN</span></div>
          <div className="choice"><i /> Mot de passe</div>
          <a href="connexion.html#login" className="dashboard-submit">Se connecter</a>
        </div>
      </div>
      <div className="dashboard-window">
        <div className="browser-chrome"><span className="window-dots"><i /><i /><i /></span><span>dashboard.facein.fr</span></div>
        <div className="dashboard-content">
          <aside><b><span className="mini-brand">F</span> FaceIN</b><span>Accueil</span><span>Services</span><span>Journal</span><span>Clés</span></aside>
          <div className="dashboard-table-wrap">
            <h4>Connexions par service</h4>
            <table className="dashboard-table">
              <thead><tr><th>Service</th><th>Pays</th><th>Connexions</th><th>Réussite</th></tr></thead>
              <tbody>{connectionRows.map(([service, country, count, success]) => (
                <tr key={service}><td><i />{service}</td><td>{country}</td><td>{count}</td><td>{success}</td></tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      </div>
    </article>
  );
}

function DemoBanner() {
  return (
    <section className="demo-banner">
      <div className="demo-banner__copy">
        <p className="eyebrow">Une démonstration de 2 min</p>
        <h2>Voyez FaceIN en action</h2>
        <p>Un aperçu du parcours de vérification, étape par étape.</p>
        <div className="button-row demo-banner__actions">
          <a className="button button-light" href="comment-ca-marche.html">
            <span className="play-icon" aria-hidden="true">▶</span> Regarder la démo <span aria-hidden="true">›</span>
          </a>
          <ExperienceWidget />
        </div>
      </div>
      <span className="demo-duration">2 min</span>
      <RibbonArtwork className="demo-banner__art" />
    </section>
  );
}

const accordionItems = [
  {
    title: "Plus aucun mot de passe à retenir",
    detail: "Votre visage devient votre clé. Il n’est ni envoyé, ni stocké : vous gardez le contrôle, même en cas de perte d’appareil.",
  },
  {
    title: "Votre visage reste sur votre appareil",
    detail: "L’image est traitée localement dans le parcours prévu. La preuve envoyée ne contient ni image ni vecteur facial.",
  },
  {
    title: "Appareil perdu ? Révoquez en un clic",
    detail: "Révoquer votre identité permet de couper son usage; le mécanisme de révocation devra être relié au service lorsqu’il sera disponible.",
  },
];

function SecuritySection() {
  return (
    <section className="security-section" id="team">
      <div className="container">
        <SectionHeading title="Une sécurité que tout le monde peut vérifier" align="center" />
        <div className="security-metrics">
          <div><strong>0</strong><span>image de visage reçue par<br />nos serveurs</span></div>
          <div><strong>128</strong><span>valeurs décrivent<br />votre visage</span></div>
          <div><strong>2 sur 3</strong><span>nœuds suffisent<br />pour valider</span></div>
          <div><strong>1 clic</strong><span>pour révoquer<br />votre identité</span></div>
        </div>
        <div className="ray-field"><ProofRays /></div>
        <div className="people-section">
          <div className="people-section__heading">
            <p className="eyebrow">Pensé pour chacun.</p>
            <h2>Que vous vous connectiez ou que vous intégriez FaceIN, tout reste simple.</h2>
          </div>
          <div className="people-grid">
            <div className="people-intro">
              <h3>Pour vous : une connexion sans mot de passe ni donnée exposée</h3>
              <p>Votre visage devient votre clé. Il n’est ni envoyé, ni stocké : vous gardez le contrôle, même en cas de perte d’appareil.</p>
              <a className="button button-primary" href="connexion.html#register">Créer un compte <span aria-hidden="true">›</span></a>
            </div>
            <div className="accordion-list">
              {accordionItems.map((item) => (
                <details key={item.title}>
                  <summary><span className="accordion-icon" aria-hidden="true">✦</span>{item.title}<span className="accordion-plus" aria-hidden="true">+</span></summary>
                  <p>{item.detail}</p>
                </details>
              ))}
            </div>
          </div>
          <div className="audience-grid">
            <article><span className="audience-icon">↗</span><h3>Pour les sites partenaires.</h3><p>Ajoutez un bouton et recevez un jeton vérifié, sans jamais gérer de donnée biométrique.</p><a href="integrer.html">Lire le guide <span aria-hidden="true">→</span></a></article>
            <article><span className="audience-icon">⌁</span><h3>Pour la sécurité.</h3><p>Les connexions inhabituelles reçoivent un score de risque : nouvel appareil, horaire ou région.</p><a href="comment-ca-marche.html">En savoir plus <span aria-hidden="true">→</span></a></article>
            <article><span className="audience-icon">◷</span><h3>Dans le temps.</h3><p>Votre photo de référence se renouvelle tous les 6 mois si vous êtes mineur, chaque année sinon.</p><a href="comment-ca-marche.html#renewal">En savoir plus <span aria-hidden="true">→</span></a></article>
          </div>
        </div>
      </div>
    </section>
  );
}

function DeveloperSection() {
  const snippet = `<script src="facein-sdk.js"></script>\n\n<button\n  data-facein-login\n  data-service-id="VOTRE_ID"\n>\n  Se connecter avec FaceIN\n</button>`;

  return (
    <section className="developer-section" id="developers">
      <div className="container">
        <div className="developer-heading">
          <div>
            <p className="eyebrow">Conçu pour les développeurs.</p>
            <h2>Un script, un bouton, une vérification côté serveur.</h2>
            <p>Aucune donnée biométrique à gérer.</p>
          </div>
          <div className="developer-stats">
            <div><strong>2</strong><span>balises pour ajouter le bouton</span></div>
            <div><strong>1</strong><span>jeton propre à chaque site</span></div>
            <div><strong>0</strong><span>donnée biométrique reçue</span></div>
          </div>
        </div>
        <div className="developer-demo">
          <div className="developer-code">
            <CodeBlock label="index.html · server.py" code={snippet} />
          </div>
          <div className="developer-preview">
            <span>Résultat</span>
            <div className="developer-preview__canvas"><a href="connexion.html#login"><span className="mini-brand">F</span> Se connecter avec FaceIN</a></div>
          </div>
        </div>
        <div className="developer-resources">
          <article><h3>Bouton prêt à l’emploi.</h3><p>Copiez-collez deux balises et c’est en ligne.</p><a href="integrer.html#button">Voir l’exemple <span>›</span></a></article>
          <article><h3>SDK JavaScript.</h3><p>Gardez la main sur l’apparence et le parcours.</p><a href="integrer.html#script">Télécharger <span>›</span></a></article>
          <article><h3>Module Python.</h3><p>Vérifiez les jetons sur votre serveur en une ligne.</p><a href="integrer.html#verify-token">Lire la doc <span>›</span></a></article>
        </div>
      </div>
    </section>
  );
}

export function HomePage() {
  return (
    <div className="home-page">
      <section className="home-hero">
        <div className="container home-hero__inner">
          <div className="hero-kpis">
            <span>Connexions vérifiées aujourd’hui <b>12 847</b></span>
            <i aria-hidden="true" />
            <span>Images de visage reçues <b className="kpi-zero">0</b></span>
          </div>
          <p className="hero-demo-note">Chiffres et visuels illustratifs; aucune authentification n’est connectée.</p>
          <div className="home-hero__copy">
            <h1>Votre visage vous connecte. Il ne quitte jamais votre appareil.</h1>
            <p>Les sites vérifient une preuve mathématique, jamais votre image.</p>
            <div className="button-row">
              <a className="button button-primary" href="connexion.html#register">Créer un compte <span aria-hidden="true">›</span></a>
              <a className="button button-outline" href="integrer.html">Intégrer FaceIN <span aria-hidden="true">›</span></a>
            </div>
            <p className="hero-footnote"><span>La preuve circule.</span><span>Votre image, jamais.</span></p>
          </div>
          <RibbonArtwork className="home-hero__ribbons" />
        </div>
      </section>

      <TrustTicker />

      <section className="container section-padding">
        <div className="section-lead">
          <p className="eyebrow">Une connexion qui ne demande rien d’autre que vous.</p>
          <h2>Inscription, connexion, révocation : tout se passe sur votre appareil, et un réseau indépendant vérifie le reste.</h2>
        </div>
        <div className="showcase-grid">
          <Reveal>
            <ZoomableWidget title="Connexion sur un site partenaire">
              <div className="showcase-panel showcase-panel--browser">
                <div className="showcase-panel__title"><p>Connectez-vous à n’importe quel site partenaire, d’un simple regard</p></div>
                <PartnerBrowserMockup />
              </div>
            </ZoomableWidget>
          </Reveal>
          <Reveal delay={0.08}>
            <ZoomableWidget title="Niveau de sécurité et connexions">
              <div className="showcase-panel showcase-panel--security"><SecurityMockup /></div>
            </ZoomableWidget>
          </Reveal>
        </div>
      </section>

      <section className="container section-padding proof-section">
        <SectionHeading
          eyebrow="Une identité numérique qui n’appartient qu’à vous"
          title="Prouvez qui vous êtes, sans jamais le révéler."
          description="Vérifiée par un réseau de serveurs indépendants."
          align="center"
        />
        <div className="proof-grid">
          <Reveal><ZoomableWidget title="Preuve d’identité"><ProofCard /></ZoomableWidget></Reveal>
          <Reveal delay={0.06}><ZoomableWidget title="Identité numérique"><IdentityCard /></ZoomableWidget></Reveal>
          <Reveal delay={0.12}><ZoomableWidget title="Réseau de vérification"><ConsensusCard /></ZoomableWidget></Reveal>
        </div>
        <Reveal><ZoomableWidget title="Tableau de bord FaceIN"><DashboardMockup /></ZoomableWidget></Reveal>
      </section>

      <div className="container"><DemoBanner /></div>
      <SecuritySection />
      <DeveloperSection />

      <section className="container contact-section" id="contact" aria-labelledby="contact-title">
        <div className="contact-section__intro">
          <p className="eyebrow">Parlons de votre projet.</p>
          <h2 id="contact-title">Contactez l’équipe FaceIN.</h2>
          <p>Décrivez votre besoin d’intégration ou posez-nous une question.</p>
        </div>
        <ContactForm />
      </section>

      <section className="container closing-section">
        <div>
          <p className="eyebrow">Envie d’essayer ?</p>
          <h2>Découvrez FaceIN à votre rythme.</h2>
          <p>Créez votre identité en une minute ou contactez l’équipe pour intégrer FaceIN à votre site.</p>
          <div className="button-row">
            <a className="button button-primary" href="connexion.html#register">Créer un compte <span>›</span></a>
          </div>
        </div>
        <div className="closing-links">
          <article><span className="closing-icon">◇</span><h3>Découvrez les offres</h3><p>Standard ou renforcée, selon votre besoin.</p><a href="tarif.html">Voir les tarifs <span>›</span></a></article>
          <article><span className="closing-icon">⌘</span><h3>Intégrez en 10 minutes</h3><p>Un guide pas à pas pour votre site.</p><a href="integrer.html">Lire le guide <span>›</span></a></article>
        </div>
      </section>
    </div>
  );
}
