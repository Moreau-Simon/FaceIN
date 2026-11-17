import { Reveal } from "../components/Reveal";
import { SectionHeading } from "../components/SectionHeading";

const steps = [
  {
    title: "Vous ouvrez la page de connexion",
    description: "Sur le site partenaire, vous cliquez sur « Se connecter avec FaceIN ».",
  },
  {
    title: "Votre navigateur lit votre visage",
    description: "La caméra s’active. 128 valeurs décrivent votre visage, puis l’image est supprimée.",
  },
  {
    title: "Votre navigateur génère une preuve",
    description: "Il prouve que ces valeurs sont proches de celles de l’inscription, sans les révéler.",
  },
  {
    title: "Seule la preuve est envoyée",
    description: "Le serveur FaceIN reçoit la preuve. Ni image, ni vecteur.",
  },
  {
    title: "Plusieurs serveurs vérifient",
    description: "Trois nœuds contrôlent la preuve. Si deux la valident, le site reçoit un jeton.",
  },
];

const questions = [
  {
    question: "Une photo de moi peut-elle me connecter ?",
    answer: "[Réponse à rédiger avec l’équipe dev.]",
  },
  {
    question: "Et mon jumeau ?",
    answer: "Réponse à confirmer avec l’équipe FaceIN.",
  },
  {
    question: "Que se passe-t-il si je perds mon téléphone ?",
    answer: "Pour rester fiable, FaceIN vous demande de refaire l’inscription. Les modalités de révocation sont à confirmer.",
  },
  {
    question: "Le site partenaire voit-il mon visage ?",
    answer: "Le parcours présenté indique que seule une preuve est envoyée au serveur FaceIN; le site partenaire reçoit un jeton.",
  },
  {
    question: "Pourquoi 128 valeurs ?",
    answer: "La maquette décrit 128 valeurs comme représentation du visage. Les détails de fonctionnement sont à confirmer avec l’équipe.",
  },
];

export function CommentCaMarchePage() {
  return (
    <div className="page-how">
      <section className="page-hero page-hero--network">
        <div className="container page-hero__inner">
          <p className="eyebrow"><span className="eyebrow-number">02</span> Comment ça marche</p>
          <h1>Votre visage reste chez vous.</h1>
          <p className="page-hero__lead">Seule une preuve mathématique voyage, et un réseau indépendant la vérifie.</p>
          <p className="prototype-note">Ce parcours décrit le fonctionnement envisagé ; il n’est pas opérationnel dans cette maquette.</p>
          <a className="button button-primary" href="integrer.html">Intégrer FaceIN <span aria-hidden="true">→</span></a>
          <div className="page-hero__network-art" aria-hidden="true"><span>A</span><i /><span>B</span><i /><span>C</span></div>
        </div>
      </section>

      <section className="container section-padding">
        <SectionHeading
          eyebrow="D’un regard à la connexion"
          title="Cinq étapes, quelques secondes."
          align="center"
        />
        <ol className="process-list">
          {steps.map((step, index) => (
            <Reveal key={step.title} className="process-step" delay={index * 0.045}>
              <span className="process-step__number">{index + 1}</span>
              <div><h3>{step.title}</h3><p>{step.description}</p></div>
            </Reveal>
          ))}
        </ol>
      </section>

      <section className="journey-band">
        <div className="container journey-band__inner">
          <h2>Ce qui circule à chaque étape</h2>
          <div className="journey-track">
            <div><span>Étapes 1 à 3</span><strong>Rien ne sort</strong></div>
            <i aria-hidden="true">→</i>
            <div><span>Étape 4</span><strong>Preuve</strong></div>
            <i aria-hidden="true">→</i>
            <div><span>Étape 5</span><strong>Jeton</strong></div>
          </div>
        </div>
      </section>

      <section className="container section-padding">
        <SectionHeading
          eyebrow="Qui fait quoi"
          title="Chaque acteur ne voit que ce dont il a besoin."
          align="center"
        />
        <div className="actor-grid">
          <Reveal className="actor-card actor-card--browser">
            <span className="actor-icon">⌘</span>
            <h3>Votre navigateur</h3>
            <ul><li>Caméra</li><li>Calcul du vecteur</li><li>Coffre-fort local</li><li>Génération de la preuve</li></ul>
          </Reveal>
          <Reveal className="actor-card actor-card--server" delay={0.08}>
            <span className="actor-icon">▦</span>
            <h3>Serveur FaceIN</h3>
            <ul><li>Réception de la preuve</li><li>Vérification rapide</li></ul>
          </Reveal>
          <Reveal className="actor-card actor-card--nodes" delay={0.16}>
            <span className="actor-icon">◎</span>
            <h3>Nœuds</h3>
            <ul><li>Nœud A</li><li>Nœud B</li><li>Nœud C</li></ul>
          </Reveal>
          <Reveal className="actor-card actor-card--partner" delay={0.24}>
            <span className="actor-icon">↗</span>
            <h3>Site partenaire</h3>
            <ul><li>Reçoit un jeton</li></ul>
          </Reveal>
        </div>
      </section>

      <section className="container section-padding" id="privacy">
        <SectionHeading
          eyebrow="Vos données"
          title="Ce qui reste chez vous, et ce qui est envoyé."
          align="center"
        />
        <div className="privacy-columns">
          <article className="privacy-column privacy-column--local">
            <p className="eyebrow">Reste sur votre appareil</p>
            <ul><li>L’image de la caméra, supprimée aussitôt</li><li>Votre vecteur facial</li><li>Votre coffre-fort chiffré</li></ul>
          </article>
          <article className="privacy-column privacy-column--sent">
            <p className="eyebrow">Envoyé à FaceIN</p>
            <ul><li>La preuve cryptographique</li><li>Une empreinte de votre appareil</li><li>Votre adresse IP et votre région, pour repérer les connexions suspectes</li></ul>
          </article>
        </div>
        <a className="text-link" href="index.html#legal-notice">Lire la politique de confidentialité <span aria-hidden="true">↗</span></a>
      </section>

      <section className="renewal-section" id="renewal">
        <div className="container renewal-section__inner">
          <div><p className="eyebrow">Dans le temps</p><h2>Votre photo de référence se renouvelle.</h2><p>Un visage change avec le temps. Pour rester fiable, FaceIN vous demande de refaire l’inscription.</p></div>
          <div className="renewal-timelines"><div><strong>6 mois</strong><span>pour les mineurs</span></div><div><strong>1 an</strong><span>pour les majeurs</span></div></div>
        </div>
      </section>

      <section className="container section-padding">
        <SectionHeading eyebrow="Questions fréquentes" title="Ce que vous nous demandez." align="center" />
        <div className="faq-list">
          {questions.map(({ question, answer }) => (
            <details key={question}>
              <summary>{question}<span aria-hidden="true">+</span></summary>
              <p>{answer}</p>
            </details>
          ))}
        </div>
      </section>
    </div>
  );
}
