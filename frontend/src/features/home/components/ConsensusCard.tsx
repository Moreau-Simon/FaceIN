import { NetworkSphere } from "../../../components/visuals/Artwork";
import { useSpotlight } from "../../../components/ui/useSpotlight";

export function ConsensusCard() {
  const cardRef = useSpotlight<HTMLElement>();

  return (
    <article ref={cardRef} className="proof-card proof-card--network spotlight-card">
      <div className="proof-card__top"><h3>Un réseau de nœuds à construire</h3></div>
      <NetworkSphere />
    </article>
  );
}
