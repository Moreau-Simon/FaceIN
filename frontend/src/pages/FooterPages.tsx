import type { ReactNode } from "react";
import { prototypeStatus } from "../app/content";
import { pageFiles, pageUrl } from "../app/navigation";

type InformationPageProps = {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
};

function InformationPage({ eyebrow, title, description, children }: InformationPageProps) {
  return (
    <div className="footer-content-page">
      <section className="page-hero page-hero--single grid-lines">
        <div className="container page-hero__inner">
          <div>
            <p className="lead-label">{eyebrow}</p>
            <h1>{title}</h1>
            <p className="note">{description}</p>
          </div>
        </div>
      </section>
      <section className="container section-padding">
        <div className="footer-content-page__body">{children}</div>
      </section>
    </div>
  );
}

type InformationSectionProps = {
  id?: string;
  title: string;
  children: ReactNode;
};

function InformationSection({ id, title, children }: InformationSectionProps) {
  return (
    <section className="footer-content-page__section" id={id} aria-labelledby={id ? `${id}-title` : undefined}>
      <h2 id={id ? `${id}-title` : undefined}>{title}</h2>
      {children}
    </section>
  );
}

export function AboutPage() {
  return (
    <InformationPage
      eyebrow="Le projet"
      title="À propos de FaceIN."
      description="Un projet étudiant qui explore une autre façon de prouver son identité en ligne."
    >
      <p className="callout callout--warn" role="note">{prototypeStatus}</p>
      <InformationSection id="projet" title="Un projet de SAE 5">
        <p>FaceIN est un projet étudiant consacré à l’authentification biométrique décentralisée. Il explore l’idée de transmettre une preuve cryptographique plutôt que l’image du visage.</p>
        <p>Le site présente la cible et les maquettes du projet. Les parcours réels, la vérification complète et les garanties de sécurité restent à construire et à valider.</p>
      </InformationSection>
      <InformationSection title="Une approche à vérifier">
        <p>La conception vise à traiter la capture biométrique sur l’appareil et à limiter les informations transmises. Ce fonctionnement n’est pas encore démontré par un service opérationnel.</p>
        <a className="text-link" href={pageFiles.howItWorks}>Découvrir le fonctionnement envisagé <span aria-hidden="true">↗</span></a>
      </InformationSection>
      <InformationSection id="equipe" title="L’équipe">
        <p>Les noms et rôles des membres ne sont pas renseignés dans cette version du projet ; ils ne sont donc pas inventés sur cette page.</p>
        <p>Le formulaire de contact est une maquette et n’envoie pas encore de message.</p>
        <a className="text-link" href={pageUrl(pageFiles.home, "contact")}>Accéder au formulaire de contact <span aria-hidden="true">↗</span></a>
      </InformationSection>
    </InformationPage>
  );
}

export function PrivacyPage() {
  return (
    <InformationPage
      eyebrow="Données personnelles"
      title="Confidentialité et données."
      description="Cette page décrit l’état du prototype et les principes envisagés ; elle ne constitue pas encore une politique de confidentialité définitive."
    >
      <p className="callout callout--warn" role="note">Avant une mise en service, les responsables, finalités, bases légales, durées de conservation, destinataires et modalités d’exercice des droits devront être définis et publiés.</p>
      <InformationSection id="prototype" title="Le prototype actuel">
        <p>Les pages de démonstration ne créent pas de compte et n’effectuent pas d’authentification réelle. Le formulaire de contact affiche un état local : il ne transmet pas les informations saisies.</p>
        <p>Les offres ne déclenchent aucun paiement. Ne fournissez pas de données sensibles dans les maquettes.</p>
      </InformationSection>
      <InformationSection title="Principes envisagés">
        <p>Le projet vise à traiter la capture biométrique sur l’appareil et à transmettre une preuve plutôt que l’image brute. La faisabilité et le comportement du système devront être vérifiés avant de présenter cette cible comme une garantie.</p>
        <p>Les informations auxiliaires, preuves, demandes et métadonnées peuvent aussi avoir des enjeux de confidentialité. Leur nature, leur circulation et leur protection restent à documenter.</p>
      </InformationSection>
      <InformationSection title="Avant tout service réel">
        <ul>
          <li>identifier l’organisme responsable du traitement et un contact effectif ;</li>
          <li>décrire les données concernées, les finalités et les destinataires ;</li>
          <li>définir les durées de conservation, la sécurité et les éventuels transferts ;</li>
          <li>indiquer les droits applicables et une procédure permettant de les exercer.</li>
        </ul>
        <a className="text-link" href={pageFiles.howItWorks}>Voir les données envisagées dans le parcours <span aria-hidden="true">↗</span></a>
      </InformationSection>
    </InformationPage>
  );
}

export function TermsPage() {
  return (
    <InformationPage
      eyebrow="Conditions de vente"
      title="Conditions générales."
      description="Les offres FaceIN sont encore indicatives : aucune souscription ni transaction n’est disponible sur ce prototype."
    >
      <p className="callout callout--warn" role="note">Ce document informe sur l’état actuel du projet ; il ne constitue pas des conditions contractuelles applicables à un service commercial.</p>
      <InformationSection title="Aucun achat n’est proposé">
        <p>Les tarifs et formules affichés sont à confirmer. Le site ne comporte pas de paiement, de commande ou d’abonnement opérationnel.</p>
        <a className="text-link" href={pageFiles.pricing}>Consulter les offres envisagées <span aria-hidden="true">↗</span></a>
      </InformationSection>
      <InformationSection title="Conditions à définir avant une commercialisation">
        <p>Avant toute souscription, il faudra préciser notamment :</p>
        <ul>
          <li>l’identité du fournisseur et la description exacte du service ;</li>
          <li>les prix, la facturation, la durée et les modalités de résiliation ;</li>
          <li>les conditions de support, de disponibilité et de responsabilité ;</li>
          <li>les règles applicables aux données et à la fin du service.</li>
        </ul>
        <p>Ces éléments ne sont pas fixés par cette maquette et devront être validés avant publication.</p>
      </InformationSection>
      <InformationSection title="Parcours de démonstration">
        <p>La création de compte et la connexion FaceIN sont indisponibles dans cette version. Aucun compte ni abonnement n’est créé en suivant ces liens.</p>
        <a className="text-link" href={pageFiles.connection}>Consulter l’état du parcours <span aria-hidden="true">↗</span></a>
      </InformationSection>
    </InformationPage>
  );
}

export function LegalNoticePage() {
  return (
    <InformationPage
      eyebrow="Informations réglementaires"
      title="Mentions légales."
      description="Cette page est un brouillon : plusieurs informations obligatoires dépendent de l’éditeur et de l’hébergeur, qui ne sont pas identifiés dans le dépôt."
    >
      <p className="callout callout--warn" role="note">Les champs indiqués « à renseigner » doivent être complétés et vérifiés avant toute mise en ligne publique. Cette page ne doit pas être considérée comme des mentions légales complètes.</p>
      <InformationSection title="Éditeur du site">
        <dl className="footer-content-page__details">
          <dt>Projet</dt><dd>FaceIN — projet étudiant, SAE 5.</dd>
          <dt>Nom ou raison sociale</dt><dd>À renseigner par l’éditeur responsable.</dd>
          <dt>Adresse</dt><dd>À renseigner par l’éditeur responsable.</dd>
          <dt>Responsable de publication</dt><dd>À désigner.</dd>
          <dt>Contact</dt><dd>Aucune adresse de contact n’est fournie. Le formulaire présent sur le site est une maquette et ne transmet pas de message.</dd>
        </dl>
      </InformationSection>
      <InformationSection title="Hébergement">
        <dl className="footer-content-page__details">
          <dt>Hébergeur</dt><dd>À renseigner selon la plateforme retenue pour le déploiement.</dd>
          <dt>Adresse de l’hébergeur</dt><dd>À renseigner.</dd>
          <dt>Contact de l’hébergeur</dt><dd>À renseigner.</dd>
        </dl>
      </InformationSection>
      <InformationSection title="Propriété intellectuelle">
        <p>Les titulaires des droits sur les contenus, marques et éléments graphiques doivent être confirmés par les responsables du projet avant publication.</p>
      </InformationSection>
    </InformationPage>
  );
}
