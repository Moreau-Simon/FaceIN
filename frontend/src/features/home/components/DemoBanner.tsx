import { pageFiles } from "../../../app/navigation";
import { TypedTerminal } from "../../../components/ui/TypedTerminal";
import { ExperienceWidget } from "../../../components/visuals/ExperienceWidget";
import { RibbonArtwork } from "../../../components/visuals/Artwork";

/** Scénario du terminal : strictement aligné sur le statut prototype (rien de « déjà fonctionnel »). */
const demoLines = [
  { text: "capture visage (cible, appareil)", delay: 0.4 },
  { text: "preuve cryptographique générée", delay: 0.4 },
  { text: "votes des nœuds — simulé", delay: 0.4 },
  { text: "décision : statut à venir", delay: 0.4 },
] as const;

export function DemoBanner() {
  return (
    <section className="demo-banner">
      <div className="demo-banner__copy">
        <p className="eyebrow">Démonstration envisagée</p>
        <h2>Le parcours que nous construisons</h2>
        <p>Une fois les fonctions implémentées : capture, preuve, votes des nœuds et décision.</p>
        <div className="button-row demo-banner__actions">
          <a className="button button-light" href={pageFiles.howItWorks}>
            Découvrir le parcours <span aria-hidden="true">›</span>
          </a>
          <ExperienceWidget />
        </div>
        <TypedTerminal className="demo-banner__terminal" lines={demoLines} />
      </div>
      <span className="demo-duration">à venir</span>
      <RibbonArtwork className="demo-banner__art" />
    </section>
  );
}
