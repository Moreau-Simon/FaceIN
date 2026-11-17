import { prototypeStatus } from "../../app/content";
import { pageFiles, pageUrl } from "../../app/navigation";
import { ContactForm } from "../../components/ui/ContactForm";
import { Reveal } from "../../components/ui/Reveal";
import { SectionHeading } from "../../components/ui/SectionHeading";
import { ZoomableWidget } from "../../components/ui/ZoomableWidget";
import { Identity3DArtwork } from "./three/Identity3DArtwork";
import { ConsensusCard } from "./components/ConsensusCard";
import { DashboardMockup } from "./components/DashboardMockup";
import { DemoBanner } from "./components/DemoBanner";
import { DeveloperSection } from "./components/DeveloperSection";
import { IdentityCard } from "./components/IdentityCard";
import { PartnerBrowserMockup } from "./components/PartnerBrowserMockup";
import { ProofCard } from "./components/ProofCard";
import { SecurityMockup } from "./components/SecurityMockup";
import { SecuritySection } from "./components/SecuritySection";
import { TrustTicker } from "./components/TrustTicker";

export function HomePage() {
  return (
    <div className="home-page">
      <section className="home-hero">
        <div className="container home-hero__inner">
          <div className="hero-kpis">
            <span>Projet étudiant <b>en développement</b></span>
            <i aria-hidden="true" />
            <span>Vérification de bout en bout <b>à raccorder</b></span>
          </div>
          <p className="hero-demo-note">{prototypeStatus}</p>
          <div className="home-hero__content">
            <div className="home-hero__copy">
              <h1>Prouver son identité sans exposer sa biométrie.</h1>
              <p className="home-hero__description">FaceIN explore une authentification biométrique décentralisée : transmettre une preuve cryptographique plutôt que l’image du visage.</p>
              <div className="button-row">
                <a className="button button-primary" href={pageFiles.howItWorks}>Découvrir le fonctionnement <span aria-hidden="true">›</span></a>
                <a className="button button-outline" href={pageUrl(pageFiles.howItWorks, "architecture")}>Voir l’architecture <span aria-hidden="true">›</span></a>
              </div>
              <p className="hero-footnote"><span>Biométrie traitée localement (cible).</span><span>Preuve et réseau à construire.</span></p>
            </div>
            <div className="home-hero__visual">
              <Identity3DArtwork className="home-hero__model" />
            </div>
          </div>
        </div>
      </section>

      <TrustTicker />

      <section className="container section-padding">
        <div className="section-lead">
          <p className="eyebrow">Le problème</p>
          <h2>Un visage ne se remplace pas comme un mot de passe. FaceIN étudie une approche où la biométrie brute n’a pas besoin d’être envoyée au serveur.</h2>
        </div>
        <div className="showcase-grid">
          <Reveal>
            <ZoomableWidget title="Parcours de connexion visé">
              <div className="showcase-panel showcase-panel--browser">
                <div className="showcase-panel__title"><p>Le parcours de démonstration prévu pour un service partenaire.</p></div>
                <PartnerBrowserMockup />
              </div>
            </ZoomableWidget>
          </Reveal>
          <Reveal delay={0.08}>
            <ZoomableWidget title="Tableau de bord illustratif">
              <div className="showcase-panel showcase-panel--security"><SecurityMockup /></div>
            </ZoomableWidget>
          </Reveal>
        </div>
      </section>

      <section className="container section-padding proof-section">
        <SectionHeading
          eyebrow="Le projet en bref"
          title="Quatre idées, une cible à construire."
          description="Biométrie locale, preuve cryptographique, réseau de nœuds et usage multi-service : ces éléments décrivent la cible, pas une solution finalisée."
          align="center"
        />
        <div className="proof-grid">
          <Reveal><ZoomableWidget title="Preuve cryptographique (cible)"><ProofCard /></ZoomableWidget></Reveal>
          <Reveal delay={0.06}><ZoomableWidget title="Identité liée à un appareil"><IdentityCard /></ZoomableWidget></Reveal>
          <Reveal delay={0.12}><ZoomableWidget title="Réseau de nœuds (cible)"><ConsensusCard /></ZoomableWidget></Reveal>
        </div>
        <Reveal><ZoomableWidget title="Tableau de bord illustratif"><DashboardMockup /></ZoomableWidget></Reveal>
        <p className="prototype-note">Données illustratives : aucun tableau de bord réel n’est connecté dans ce dépôt.</p>
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
          <p className="eyebrow">Suivre le projet</p>
          <h2>FaceIN est un prototype en développement.</h2>
          <p>Les parcours de cette page illustrent la cible du projet. Aucune authentification réelle n’est encore connectée.</p>
          <div className="button-row">
            <a className="button button-primary" href={pageFiles.connection}>Voir le parcours de démonstration <span>›</span></a>
          </div>
        </div>
        <div className="closing-links">
          <article><span className="closing-icon">◇</span><h3>Offres envisagées</h3><p>Des formules indicatives, sans paiement opérationnel.</p><a href={pageFiles.pricing}>Voir les offres <span>›</span></a></article>
          <article><span className="closing-icon">⌘</span><h3>Guide d’intégration</h3><p>Les étapes et le SDK restent à construire.</p><a href={pageFiles.integration}>Lire le guide <span>›</span></a></article>
        </div>
      </section>
    </div>
  );
}
