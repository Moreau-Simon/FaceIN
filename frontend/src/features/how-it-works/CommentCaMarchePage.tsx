import { prototypeStatus } from "../../app/content";
import { pageFiles, pageUrl } from "../../app/navigation";
import { Reveal } from "../../components/ui/Reveal";
import { SectionHeading } from "../../components/ui/SectionHeading";

const steps = [
  {
    title: "Créer un compte FaceIN",
    description: "Le compte serait associé à une méthode biométrique. La capture est destinée à être traitée localement, sans être envoyée telle quelle aux nœuds.",
  },
  {
    title: "Utiliser un autre appareil",
    description: "L’idée étudiée consiste à reconstruire une valeur cryptographique à partir d’une nouvelle capture et d’informations auxiliaires. La faisabilité reste à valider.",
  },
  {
    title: "Présenter une preuve",
    description: "Le système génère une demande liée au service et à un nonce temporaire. L’utilisateur produit une preuve cryptographique pour cette demande.",
  },
  {
    title: "Faire vérifier par le réseau",
    description: "Le nœud initiateur transmet la demande aux pairs, qui vérifient la preuve et renvoient leur vote. La règle de seuil reste à définir.",
  },
  {
    title: "Transmettre le résultat au service",
    description: "Si la preuve et la décision sont valides, FaceIN transmet un résultat d’authentification. Forme du jeton, durée de vie et révocation restent à définir.",
  },
];

const questions = [
  {
    question: "FaceIN stocke-t-il le visage de l’utilisateur ?",
    answer: "L’objectif est que la biométrie brute soit traitée localement et ne soit pas envoyée aux nœuds. Cette propriété devra être confirmée par l’implémentation et par des vérifications du flux réseau et du stockage.",
  },
  {
    question: "Peut-on utiliser FaceIN depuis plusieurs appareils ?",
    answer: "C’est un objectif du projet. Il dépend de la capacité à produire une valeur cryptographique stable à partir de captures différentes et de la gestion sûre des informations auxiliaires et de la récupération du compte.",
  },
  {
    question: "Qu’est-ce qu’une preuve à divulgation nulle de connaissance ?",
    answer: "C’est une famille de méthodes cryptographiques qui permet, sous certaines conditions, de démontrer qu’une affirmation est vraie sans révéler directement le secret associé. Le choix et l’intégration d’un protocole adapté restent à mener.",
  },
  {
    question: "Le réseau est-il déjà entièrement décentralisé ?",
    answer: "Un réseau de plusieurs nœuds est prévu et son socle est en cours de construction. Plusieurs instances ne suffisent pas à garantir une décentralisation complète : les règles de vote, les seuils et le comportement en cas de panne restent à définir.",
  },
  {
    question: "FaceIN protège-t-il aussi les métadonnées ?",
    answer: "Pas nécessairement. Les horaires, les services utilisés, les adresses IP et les événements de connexion peuvent révéler des informations. Leur collecte et leur conservation doivent être limitées et documentées.",
  },
];

export function CommentCaMarchePage() {
  return (
    <div className="page-how">
      <section className="page-hero page-hero--network">
        <div className="container page-hero__inner">
          <p className="eyebrow"><span className="eyebrow-number">02</span> Fonctionnement envisagé</p>
          <h1>Comment FaceIN doit fonctionner.</h1>
          <p className="page-hero__lead">De la capture locale à la décision du réseau : le parcours que le projet cherche à construire.</p>
          <p className="prototype-note">{prototypeStatus}</p>
          <a className="button button-primary" href="#architecture">Voir l’architecture <span aria-hidden="true">→</span></a>
          <div className="page-hero__network-art" aria-hidden="true"><span>A</span><i /><span>B</span><i /><span>C</span></div>
        </div>
      </section>

      <section className="container section-padding">
        <SectionHeading
          eyebrow="Cinq étapes envisagées"
          title="Du compte à la décision."
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
          <h2>Ce qui devra circuler à chaque étape</h2>
          <div className="journey-track">
            <div><span>Capture</span><strong>Traitement local visé</strong></div>
            <i aria-hidden="true">→</i>
            <div><span>Preuve</span><strong>Format à définir</strong></div>
            <i aria-hidden="true">→</i>
            <div><span>Résultat</span><strong>Jeton à définir</strong></div>
          </div>
        </div>
      </section>

      <section className="container section-padding" id="architecture">
        <SectionHeading
          eyebrow="Architecture du système"
          title="Les composants du parcours envisagé."
          align="center"
        />
        <div className="actor-grid">
          <Reveal className="actor-card actor-card--browser">
            <span className="actor-icon">⌘</span>
            <h3>Appareil de l’utilisateur</h3>
            <ul><li>Capture biométrique</li><li>Traitement local visé</li><li>Production de la preuve</li></ul>
          </Reveal>
          <Reveal className="actor-card actor-card--server" delay={0.08}>
            <span className="actor-icon">▦</span>
            <h3>Nœud initiateur</h3>
            <ul><li>Reçoit la demande</li><li>Gère le contexte et le nonce</li><li>Contacte les pairs</li></ul>
          </Reveal>
          <Reveal className="actor-card actor-card--nodes" delay={0.16}>
            <span className="actor-icon">◎</span>
            <h3>Nœuds pairs</h3>
            <ul><li>Vérifient la preuve</li><li>Renvoyent leur vote</li><li>Seuil à définir</li></ul>
          </Reveal>
          <Reveal className="actor-card actor-card--partner" delay={0.24}>
            <span className="actor-icon">↗</span>
            <h3>Service demandé</h3>
            <ul><li>Reçoit le résultat</li><li>Jeton et révocation à définir</li></ul>
          </Reveal>
        </div>
      </section>

      <section className="container section-padding" id="privacy">
        <SectionHeading
          eyebrow="Données et métadonnées"
          title="Ce que le système devra traiter, et ce qu’il ne doit pas exposer."
          align="center"
        />
        <div className="privacy-columns">
          <article className="privacy-column privacy-column--local">
            <p className="eyebrow">Traitement local visé</p>
            <ul><li>La capture biométrique, destinée à rester sur l’appareil</li><li>Les données dérivées, à définir et à sécuriser</li><li>Les informations auxiliaires du compte, à protéger</li></ul>
          </article>
          <article className="privacy-column privacy-column--sent">
            <p className="eyebrow">Échanges à définir</p>
            <ul><li>La preuve cryptographique</li><li>Le contexte de la demande et le nonce</li><li>Des métadonnées limitées, dont la collecte reste à documenter</li></ul>
          </article>
        </div>
        <a className="text-link" href={pageUrl(pageFiles.home, "legal-notice")}>Lire la politique de confidentialité <span aria-hidden="true">↗</span></a>
      </section>

      <section className="renewal-section" id="revocation">
        <div className="container renewal-section__inner">
          <div><p className="eyebrow">Contrôle</p><h2>La révocation doit atteindre les nœuds.</h2><p>Après la perte d’un appareil, la révocation devra être connue des nœuds avant d’accepter de nouvelles authentifications. Le délai de propagation et le comportement des nœuds non informés restent à définir.</p></div>
          <div className="renewal-timelines"><div><strong>À définir</strong><span>délai de propagation</span></div><div><strong>À documenter</strong><span>comportement en cas de panne</span></div></div>
        </div>
      </section>

      <section className="container section-padding">
        <SectionHeading eyebrow="Questions fréquentes" title="Ce que le projet peut déjà dire." align="center" />
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
