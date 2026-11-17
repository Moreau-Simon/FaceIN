import { useSpotlight } from "../../../components/ui/useSpotlight";

export function ProofCard() {
  const cardRef = useSpotlight<HTMLElement>();

  return (
    <article ref={cardRef} className="proof-card proof-card--visual spotlight-card">
      <div className="proof-card__top"><h3>La preuve<br />plutôt que l’image</h3></div>
      <div className="commitment-art" aria-hidden="true">
        <div className="commitment-ring" />
        <span className="commitment-label">preuve · ••••••••</span>
        <span className="proof-valid"><i>✓</i> Preuve simulée</span>
      </div>
    </article>
  );
}
