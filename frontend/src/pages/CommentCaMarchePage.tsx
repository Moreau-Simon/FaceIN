import { Reveal } from "../components/Reveal";
import { SectionHeading } from "../components/SectionHeading";

const steps = [
  { title: "Vous ouvrez la connexion FaceIN", description: "Sur le site partenaire, vous cliquez sur « Se connecter avec FaceIN » et saisissez votre pseudo." },
  { title: "Vous prouvez votre présence", description: "FaceIN vous demande deux gestes tirés au hasard : cligner des yeux, tourner la tête ou sourire." },
  { title: "Votre navigateur lit votre visage", description: "128 valeurs décrivent votre visage. L’image de la caméra n’est jamais enregistrée." },
  { title: "Votre navigateur génère une preuve", description: "Il prouve que ces valeurs sont proches de celles de l’inscription, sans les révéler." },
  { title: "Trois serveurs vérifient", description: "La preuve est contrôlée par trois nœuds indépendants. Si deux la valident, le site reçoit un jeton." },
];

const questions = [
  {
    question: "Une photo de moi peut-elle me connecter ?",
    answer: "Non. Avant chaque connexion, FaceIN impose deux défis aléatoires (clignement, rotation de la tête, sourire) et vérifie que le visage bouge de façon continue. Une photo ou un écran tenu devant la caméra ne peut pas les réussir.",
  },
  {
    question: "Le site partenaire voit-il mon visage ?",
    answer: "Non. Le site reçoit uniquement un jeton signé qui confirme votre pseudo. Ni l’image, ni les 128 valeurs ne lui sont transmises.",
  },
  {
    question: "Que se passe-t-il si je change d’appareil ?",
    answer: "Votre vecteur de référence est gardé dans le coffre de l’appareil sur lequel vous vous êtes inscrit. Sur un nouvel appareil, vous refaites l’inscription.",
  },
  {
    question: "Pourquoi 128 valeurs ?",
    answer: "C’est la taille du descripteur produit par le modèle de reconnaissance faciale. Il suffit à distinguer deux visages, sans permettre de reconstruire une photo.",
  },
  {
    question: "Une preuve interceptée peut-elle être réutilisée ?",
    answer: "Non. Chaque connexion utilise un défi à usage unique, valable 60 secondes. Une preuve rejouée plus tard est refusée.",
  },
];

export function CommentCaMarchePage() {
  return (
    <div className="page-how">
      <section className="page-hero grid-lines">
        <div className="container page-hero__inner">
          <div>
            <p className="lead-label">Comment ça marche</p>
            <h1>Votre visage reste chez vous. <span>Seule une preuve mathématique voyage, et un réseau indépendant la vérifie.</span></h1>
            <div className="button-row">
              <a className="button button-primary" href="connexion.html#register">Créer un compte <span className="button-arrow" aria-hidden="true" /></a>
              <a className="button button-outline" href="integrer.html">Intégrer FaceIN <span className="button-arrow" aria-hidden="true" /></a>
            </div>
          </div>
          <div className="page-hero__network-art" aria-hidden="true"><span>A</span><i /><span>B</span><i /><span>C</span></div>
        </div>
      </section>

      <section className="container section-padding">
        <SectionHeading eyebrow="D’un regard à la connexion" title="Cinq étapes, quelques secondes." align="center" />
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
            <div><span>Étapes 1 à 4</span><strong>Rien ne quitte l’appareil</strong></div>
            <i aria-hidden="true" />
            <div><span>Étape 5</span><strong>La preuve</strong></div>
            <i aria-hidden="true" />
            <div><span>Résultat</span><strong>Un jeton pour le site</strong></div>
          </div>
        </div>
      </section>

      <section className="container section-padding">
        <SectionHeading eyebrow="Qui fait quoi" title="Chaque acteur ne voit que ce dont il a besoin." align="center" />
        <div className="actor-grid">
          <Reveal className="actor-card">
            <h3>Votre navigateur</h3>
            <ul><li>Accède à la caméra</li><li>Calcule les 128 valeurs</li><li>Les garde dans un coffre local</li><li>Génère la preuve</li></ul>
          </Reveal>
          <Reveal className="actor-card" delay={0.06}>
            <h3>Serveur FaceIN</h3>
            <ul><li>Délivre un défi à usage unique</li><li>Reçoit la preuve</li><li>Transmet aux nœuds</li></ul>
          </Reveal>
          <Reveal className="actor-card actor-card--accent" delay={0.12}>
            <h3>Nœuds de vérification</h3>
            <ul><li>Nœud A</li><li>Nœud B</li><li>Nœud C</li><li>Deux accords sur trois suffisent</li></ul>
          </Reveal>
          <Reveal className="actor-card" delay={0.18}>
            <h3>Site partenaire</h3>
            <ul><li>Reçoit un jeton signé</li><li>Vérifie le jeton côté serveur</li></ul>
          </Reveal>
        </div>
      </section>

      <section className="container section-padding" id="privacy">
        <SectionHeading eyebrow="Vos données" title="Ce qui reste chez vous, et ce qui est envoyé." align="center" />
        <div className="privacy-columns">
          <article className="privacy-column privacy-column--local">
            <h3>Reste sur votre appareil</h3>
            <ul><li>L’image de la caméra, jamais enregistrée</li><li>Votre vecteur facial de 128 valeurs</li><li>Le coffre local qui le protège</li></ul>
          </article>
          <article className="privacy-column privacy-column--sent">
            <h3>Envoyé à FaceIN</h3>
            <ul><li>Votre pseudo</li><li>À l’inscription : une empreinte cryptographique du vecteur</li><li>À la connexion : la preuve et le défi utilisé</li></ul>
          </article>
        </div>
      </section>

      <section className="renewal-section" id="renewal">
        <div className="container renewal-section__inner">
          <div>
            <p className="lead-label">Dans le temps</p>
            <h2>Votre photo de référence se renouvelle.</h2>
            <p>Un visage change avec les années. Pour rester fiable, FaceIN vous demande de refaire l’inscription à intervalles réguliers.</p>
          </div>
          <div className="renewal-timelines"><div><strong>6 mois</strong><span>pour les mineurs</span></div><div><strong>1 an</strong><span>pour les majeurs</span></div></div>
        </div>
      </section>

      <section className="container section-padding">
        <SectionHeading eyebrow="Questions fréquentes" title="Ce que vous nous demandez." align="center" />
        <div className="faq-list">
          {questions.map(({ question, answer }) => (
            <details key={question}>
              <summary>{question}<span className="accordion-plus" aria-hidden="true" /></summary>
              <p>{answer}</p>
            </details>
          ))}
        </div>
      </section>
    </div>
  );
}
