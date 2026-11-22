import { Reveal } from "../components/Reveal";
import { SectionHeading } from "../components/SectionHeading";

const offers = [
  {
    name: "Standard",
    description: "Pour se connecter rapidement, au quotidien.",
    price: "Gratuit",
    cadence: "sans frais mensuels",
    action: "Commencer",
    features: [
      "Vecteur facial de 128 valeurs",
      "Connexion rapide",
      "Révocation en un clic",
      "Renouvellement de la photo",
    ],
  },
  {
    name: "Renforcée",
    description: "Pour les comptes qui demandent plus de sécurité.",
    price: "2,99 €",
    cadence: "par mois",
    action: "Choisir Renforcée",
    features: [
      "Tout de l’offre Standard",
      "Vecteur facial de 256 valeurs",
      "Meilleure résistance aux fraudes",
    ],
    featured: true,
  },
  {
    name: "Enterprise",
    description: "Pour les organisations qui équipent leurs équipes.",
    price: "Sur devis",
    cadence: "abonnement par groupe",
    action: "Nous contacter",
    features: [
      "Tarif adapté à la taille du groupe",
      "Abonnement centralisé pour l’équipe",
      "Contactez-nous pour définir votre offre",
    ],
  },
];

const comparisons = [
  ["Taille du vecteur facial", "128 valeurs", "256 valeurs", "Selon l’offre choisie"],
  ["Vitesse de connexion", "Plus rapide", "Un peu plus longue", "Selon la formule"],
  ["Niveau de sécurité", "Standard", "Renforcé", "Selon la formule"],
  ["Abonnement", "Individuel", "Individuel", "Par groupe"],
  ["Tarification", "Gratuit", "2,99 € / mois", "Selon la taille du groupe"],
];

const questions = [
  ["Puis-je changer d’offre ?", "Oui. Vous pourrez passer d’une offre à l’autre depuis votre espace dès l’ouverture des abonnements."],
  ["Que change un vecteur de 256 valeurs ?", "Il décrit votre visage plus finement, ce qui réduit encore le risque de confusion entre deux personnes. La connexion prend un peu plus de temps."],
  ["Comment fonctionne l’offre Enterprise ?", "C’est un abonnement unique pour tout un groupe, dont le tarif dépend du nombre de personnes. Contactez-nous pour un devis."],
];

export function PricingPage() {
  return (
    <div className="page-pricing">
      <section className="page-hero grid-lines">
        <div className="container page-hero__inner">
          <div>
          <p className="lead-label">Tarifs</p>
          <h1>Des offres simples. <span>Gratuit pour démarrer, 2,99 € par mois pour une sécurité renforcée.</span></h1>
          </div>
          <div className="pricing-orbit" aria-hidden="true"><span>FaceIN</span><i /><i /><i /></div>
        </div>
      </section>
      <section className="container section-padding">
        <div className="pricing-grid">
          {offers.map((offer, index) => (
            <Reveal className={`pricing-card${offer.featured ? " pricing-card--featured" : ""}`} key={offer.name} delay={index * 0.07}>
              {offer.featured && <span className="pricing-recommended">Recommandée</span>}
              <h2>{offer.name}</h2>
              <p>{offer.description}</p>
              <div className="pricing-price"><strong>{offer.price}</strong><span>{offer.cadence}</span></div>
              <a className={`button ${offer.featured ? "button-primary" : "button-outline"} button-full`} href={offer.name === "Enterprise" ? "index.html#contact" : "connexion.html#register"}>{offer.action}</a>
              <ul>{offer.features.map((feature) => <li key={feature}><span aria-hidden="true">✓</span>{feature}</li>)}</ul>
            </Reveal>
          ))}
        </div>
      </section>
      <section className="container section-padding">
        <SectionHeading eyebrow="Comparer" title="Ce que comprend chaque offre." align="center" />
        <div className="comparison-table-wrap">
          <table className="comparison-table">
            <thead><tr><th scope="col">Fonctionnalité</th><th scope="col">Standard</th><th scope="col">Renforcée</th><th scope="col">Enterprise</th></tr></thead>
            <tbody>{comparisons.map(([feature, standard, enhanced, enterprise]) => (
              <tr key={feature}><th scope="row">{feature}</th><td>{standard}</td><td>{enhanced}</td><td>{enterprise}</td></tr>
            ))}</tbody>
          </table>
        </div>
        <p className="note">Les tarifs sont indicatifs : la facturation ouvrira avec les abonnements.</p>
      </section>
      <section className="container section-padding">
        <SectionHeading eyebrow="Questions fréquentes" title="Une question sur les offres ?" align="center" />
        <div className="faq-list">
          {questions.map(([question, answer]) => <details key={question}><summary>{question}<span className="accordion-plus" aria-hidden="true" /></summary><p>{answer}</p></details>)}
        </div>
      </section>
    </div>
  );
}
