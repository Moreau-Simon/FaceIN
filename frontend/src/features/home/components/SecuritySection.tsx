import { pageFiles, pageUrl } from "../../../app/navigation";
import { SectionHeading } from "../../../components/ui/SectionHeading";
import { ProofRays } from "../../../components/visuals/Artwork";

const accordionItems = [
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

export function SecuritySection() {
  return (
    <section className="security-section" id="team">
      <div className="container">
        <SectionHeading title="Contrôle, révocation et limites" align="center" />
        <div className="security-metrics">
          <div><strong>0</strong><span>image brute à envoyer<br />dans la conception visée</span></div>
          <div><strong>4</strong><span>briques à réunir : biométrie,<br />preuve, réseau, multi-service</span></div>
          <div><strong>Seuil</strong><span>règle de décision<br />encore à définir</span></div>
          <div><strong>À venir</strong><span>révocation et propagation<br />entre les nœuds</span></div>
        </div>
        <div className="ray-field"><ProofRays /></div>
        <div className="people-section">
          <div className="people-section__heading">
            <p className="eyebrow">Ce que le projet doit encore traiter.</p>
            <h2>Les limites font partie de la conception.</h2>
          </div>
          <div className="people-grid">
            <div className="people-intro">
              <h3>Pour vous : une biométrie qui ne devient pas un identifiant permanent</h3>
              <p>La biométrie brute ne doit pas être transmise aux nœuds. Les données dérivées et auxiliaires devront elles aussi être étudiées et sécurisées.</p>
              <a className="button button-primary" href={pageFiles.connection}>Voir le parcours de démonstration <span aria-hidden="true">›</span></a>
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
            <article><span className="audience-icon">↗</span><h3>Pour les services.</h3><p>Chaque service aurait sa configuration propre. L’isolation et la non-corrélation ne sont pas garanties automatiquement par les preuves cryptographiques.</p><a href={pageFiles.integration}>Voir la cible <span aria-hidden="true">→</span></a></article>
            <article><span className="audience-icon">⌁</span><h3>Analyse des métadonnées.</h3><p>Fréquence, horaires ou service visé pourraient signaler un comportement inhabituel. Cette analyse ne remplace pas une validation biométrique.</p><a href={pageUrl(pageFiles.howItWorks, "privacy")}>En savoir plus <span aria-hidden="true">→</span></a></article>
            <article><span className="audience-icon">◷</span><h3>Journalisation et intégrité.</h3><p>Un journal chaîné et une synchronisation entre nœuds sont envisagés, mais ne seront présentés comme réalisés qu’après implémentation et vérification.</p><a href={pageUrl(pageFiles.howItWorks, "revocation")}>En savoir plus <span aria-hidden="true">→</span></a></article>
          </div>
        </div>
      </div>
    </section>
  );
}
