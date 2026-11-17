import { useState } from "react";
import { BrandMark } from "./BrandMark";

const plans = {
  standard: { label: "Standard", price: "Gratuit", vectors: "128 valeurs" },
  reinforced: { label: "Renforcée", price: "2,99 € / mois", vectors: "256 valeurs" },
} as const;

type PlanId = keyof typeof plans;

const planOptions = [
  { id: "standard", ...plans.standard },
  { id: "reinforced", ...plans.reinforced },
] satisfies { id: PlanId; label: string; price: string; vectors: string }[];

function PlanSelector({
  selectedPlan,
  onSelect,
}: {
  selectedPlan: PlanId;
  onSelect: (plan: PlanId) => void;
}) {
  return (
    <div className="experience-plan-selector" role="group" aria-label="Choisir une formule d’aperçu">
      {planOptions.map(({ id, label, price }) => (
        <button
          className={`experience-plan-option${selectedPlan === id ? " is-selected" : ""}`}
          type="button"
          key={id}
          aria-pressed={selectedPlan === id}
          onClick={() => onSelect(id)}
        >
          <span>{label}</span>
          <small>{price}</small>
        </button>
      ))}
    </div>
  );
}

function CheckoutPreview({
  selectedPlan,
  onSelect,
}: {
  selectedPlan: PlanId;
  onSelect: (plan: PlanId) => void;
}) {
  const plan = plans[selectedPlan];

  return (
    <article className="experience-checkout" aria-label="Aperçu illustratif d’une page de paiement">
      <div className="experience-checkout__top">
        <span className="experience-checkout__merchant"><span className="merchant-mark">A</span> atelier lune</span>
        <span className="experience-checkout__secure"><span aria-hidden="true">⌑</span> Aperçu</span>
      </div>
      <div className="experience-checkout__body">
        <p className="experience-checkout__eyebrow">ABONNEMENT PARTENAIRE</p>
        <h3>Choisissez votre formule</h3>
        <p className="experience-checkout__description">Une expérience de connexion simple, avec FaceIN.</p>
        <PlanSelector selectedPlan={selectedPlan} onSelect={onSelect} />
        <div className="experience-checkout__summary">
          <div><span>Formule {plan.label}</span><strong>{plan.price}</strong></div>
          <div><span>Preuve locale</span><strong>{plan.vectors}</strong></div>
        </div>
        <div className="experience-payment-method">
          <span className="payment-card-icon" aria-hidden="true"><i /><i /></span>
          <span>Étape de paiement partenaire</span>
          <span className="payment-lock" aria-label="Illustration uniquement">i</span>
        </div>
        <div className="experience-checkout__submit" aria-hidden="true">
          Continuer avec FaceIN <span>→</span>
        </div>
        <p className="experience-checkout__note">Maquette illustrative · aucun paiement n’est effectué.</p>
      </div>
    </article>
  );
}

export function ExperienceWidgetVisual() {
  const [selectedPlan, setSelectedPlan] = useState<PlanId>("reinforced");
  const plan = plans[selectedPlan];

  return (
    <div className="experience-visual">
      <article className="experience-brand-card">
        <div className="experience-brand-card__top"><BrandMark /><span>FACEIN · IDENTITÉ PRIVÉE</span></div>
        <div className="experience-brand-card__art" aria-hidden="true">
          <span className="experience-orbit experience-orbit--one" />
          <span className="experience-orbit experience-orbit--two" />
          <span className="experience-orbit experience-orbit--three" />
          <span className="experience-brand-core"><BrandMark /></span>
        </div>
        <div className="experience-brand-card__copy">
          <span>UNE PREUVE, PAS UNE IMAGE</span>
          <h3>Votre identité reste à vous.</h3>
        </div>
        <span className="experience-brand-card__glint" aria-hidden="true" />
      </article>

      <CheckoutPreview selectedPlan={selectedPlan} onSelect={setSelectedPlan} />

      <aside className="experience-metrics" aria-label="Indicateurs FaceIN illustratifs">
        <article className="experience-metric experience-metric--warm">
          <span className="experience-metric__label">IMAGE TRANSMISE</span>
          <strong>0</strong>
          <span className="experience-metric__caption">l’image reste sur l’appareil</span>
          <span className="experience-metric__spark" aria-hidden="true"><i /><i /><i /><i /><i /><i /><i /></span>
        </article>
        <article className="experience-metric experience-metric--cool">
          <span className="experience-metric__label">PREUVE LOCALE</span>
          <strong>{plan.vectors.split(" ")[0]}<small> valeurs</small></strong>
          <span className="experience-metric__caption">formule {plan.label.toLowerCase()}</span>
          <div className="experience-metric__progress" aria-hidden="true"><i /></div>
        </article>
        <p className="experience-metrics__note">Chiffres et interface présentés à titre illustratif.</p>
      </aside>
    </div>
  );
}
