import { useSpotlight } from "../../../components/ui/useSpotlight";

export function IdentityCard() {
  const cardRef = useSpotlight<HTMLElement>();

  return (
    <article ref={cardRef} className="proof-card proof-card--identity spotlight-card">
      <div className="proof-card__top"><h3>Une identité liée à un appareil</h3></div>
      <div className="identity-art">
        <div className="identity-glow"><span className="mini-brand">F</span><b>ZK</b></div>
        <div className="identity-details"><strong>manon_m</strong><span>Engagement à définir</span><b>FaceIN</b></div>
      </div>
    </article>
  );
}
