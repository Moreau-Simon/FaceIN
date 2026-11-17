import { Reveal } from "../components/Reveal";
import { SectionHeading } from "../components/SectionHeading";

const offers = [
  {
    name: "Standard",
    description: "Pour se connecter vite au quotidien.",
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
    description: "Pour les usages qui demandent plus de sécurité.",
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
    description: "Une formule pensée pour les organisations et leurs équipes.",
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
  ["Puis-je changer d’offre ?", "Les modalités de changement d’offre seront précisées lors de la mise en service des abonnements."],
  ["Que change un vecteur de 256 valeurs ?", "L’offre renforcée prévoit un vecteur de 256 valeurs pour privilégier un niveau de sécurité supérieur."],
  ["Comment fonctionne l’offre Enterprise ?", "Enterprise est proposée sous forme d’un abonnement par groupe, avec un tarif établi selon la taille de l’équipe."],
];

export function PricingPage() {
  return (
    <div className="page-pricing">
      <section className="page-hero page-hero--pricing">
        <div className="container page-hero__inner">
          <p className="eyebrow">Des offres simples.</p>
          <h1>Choisissez entre une connexion rapide et une sécurité renforcée.</h1>
          <p className="page-hero__lead">Une offre gratuite pour démarrer, une sécurité renforcée à 2,99 € par mois et une formule Enterprise par groupe.</p>
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
        <SectionHeading eyebrow="Comparer les offres." title="Les fonctionnalités prévues." align="center" />
        <div className="comparison-table-wrap">
          <table className="comparison-table">
            <thead><tr><th scope="col">Fonctionnalité</th><th scope="col">Standard</th><th scope="col">Renforcée</th><th scope="col">Enterprise</th></tr></thead>
            <tbody>{comparisons.map(([feature, standard, enhanced, enterprise]) => (
              <tr key={feature}><th scope="row">{feature}</th><td>{standard}</td><td>{enhanced}</td><td>{enterprise}</td></tr>
            ))}</tbody>
          </table>
        </div>
        <p className="prototype-note">Les abonnements et paiements ne sont pas encore reliés à un service de facturation.</p>
      </section>
      <section className="container section-padding">
        <SectionHeading eyebrow="Questions sur les tarifs." title="Une question sur les offres ?" align="center" />
        <div className="faq-list">
          {questions.map(([question, answer]) => <details key={question}><summary>{question}<span aria-hidden="true">+</span></summary><p>{answer}</p></details>)}
        </div>
      </section>
    </div>
  );
}
