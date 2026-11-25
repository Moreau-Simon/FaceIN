import { pageFiles, pageUrl } from "../app/navigation";
import { Reveal } from "../components/ui/Reveal";
import { SectionHeading } from "../components/ui/SectionHeading";

const offers = [
  {
    name: "Standard",
    description: "Une formule individuelle indicative.",
    price: "Gratuit",
    cadence: "tarif indicatif",
    action: "Découvrir le parcours",
    features: [
      "Compte de démonstration",
      "Parcours de connexion visé",
      "Révocation à définir",
      "Renouvellement à définir",
    ],
  },
  {
    name: "Renforcée",
    description: "Une piste pour les usages demandant plus de garanties.",
    price: "2,99 €",
    cadence: "par mois · tarif indicatif",
    action: "Voir le parcours",
    features: [
      "Tout de l’offre Standard",
      "Niveau de vérification renforcé (cible)",
      "Options à définir avec l’équipe",
    ],
    featured: true,
  },
  {
    name: "Enterprise",
    description: "Une formule à construire avec les organisations.",
    price: "Sur devis",
    cadence: "tarif indicatif",
    action: "Nous contacter",
    features: [
      "Tarif adapté à la taille du groupe",
      "Abonnement centralisé pour l’équipe",
      "Contactez-nous pour définir votre offre",
    ],
  },
];

const comparisons = [
  ["Usage", "Individuel", "Individuel", "Par groupe"],
  ["Niveau de vérification", "Standard", "Renforcé", "Selon l’offre"],
  ["Disponibilité", "À venir", "À venir", "À venir"],
  ["Abonnement", "Individuel", "Individuel", "Par groupe"],
  ["Tarification", "Gratuit (indicatif)", "2,99 € / mois (indicatif)", "Selon la taille du groupe"],
];

const questions = [
  ["Puis-je changer d’offre ?", "Les modalités de changement d’offre restent à définir avec la mise en service des abonnements."],
  ["Que change une offre renforcée ?", "Le niveau de vérification et les garanties associées restent à préciser. Aucun vecteur de 256 valeurs n’est implémenté à ce stade."],
  ["Comment fonctionne l’offre Enterprise ?", "Enterprise est une piste d’abonnement par groupe, dont le tarif serait établi selon la taille de l’équipe."],
];

export function PricingPage() {
  return (
    <div className="page-pricing">
      <section className="page-hero grid-lines">
        <div className="container page-hero__inner">
          <div>
          <p className="lead-label">Offres envisagées.</p>
          <h1>Des formules à définir <span>avec les premiers services.</span></h1>
          <p className="note">Les montants ci-dessous sont indicatifs. Aucun abonnement ni paiement n’est opérationnel.</p>
          </div>
          <div className="pricing-orbit" aria-hidden="true"><span>FaceIN</span><i /><i /><i /></div>
        </div>
      </section>
      <section className="container section-padding">
        <div className="pricing-grid">
          {offers.map((offer, index) => (
            <Reveal className={`pricing-card${offer.featured ? " pricing-card--featured" : ""}`} key={offer.name} delay={index * 0.07}>
              {offer.featured && <span className="pricing-recommended">Exemple</span>}
              <h2>{offer.name}</h2>
              <p>{offer.description}</p>
              <div className="pricing-price"><strong>{offer.price}</strong><span>{offer.cadence}</span></div>
              <a className={`button ${offer.featured ? "button-primary" : "button-outline"} button-full`} href={offer.name === "Enterprise" ? pageUrl(pageFiles.home, "contact") : pageUrl(pageFiles.connection, "register")}>{offer.action}</a>
              <ul>{offer.features.map((feature) => <li key={feature}><span aria-hidden="true">✓</span>{feature}</li>)}</ul>
            </Reveal>
          ))}
        </div>
      </section>
      <section className="container section-padding">
        <SectionHeading eyebrow="Comparer les offres." title="Les fonctionnalités prévues." align="center" />
        <div className="comparison-table-wrap">
          <table className="comparison-table">
            <thead><tr><th scope="col">Fonctionnalité</th><th scope="col">Standard</th><th scope="col">Renforcée</th><th scope="col">Enterprise</th></tr></thead>
            <tbody>{comparisons.map(([feature, standard, enhanced, enterprise]) => (
              <tr key={feature}><th scope="row">{feature}</th><td>{standard}</td><td>{enhanced}</td><td>{enterprise}</td></tr>
            ))}</tbody>
          </table>
        </div>
        <p className="note">Les tarifs sont indicatifs : aucun abonnement ni paiement n’est relié à un service de facturation.</p>
      </section>
      <section className="container section-padding">
        <SectionHeading eyebrow="Questions sur les offres." title="Une question sur les formules ?" align="center" />
        <div className="faq-list">
          {questions.map(([question, answer]) => <details key={question}><summary>{question}<span className="accordion-plus" aria-hidden="true" /></summary><p>{answer}</p></details>)}
        </div>
      </section>
    </div>
  );
}
