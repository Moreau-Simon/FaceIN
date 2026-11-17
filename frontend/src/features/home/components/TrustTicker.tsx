const compatibility = [
  "Biométrie locale",
  "Preuve cryptographique",
  "Réseau de nœuds",
  "Multi-service",
  "Multi-appareil",
  "Fuzzy extractor",
  "Révocation",
  "Métadonnées",
  "Journal chaîné",
  "Prototype",
];

export function TrustTicker() {
  return (
    <div className="trust-ticker" aria-label="Briques et objectifs du projet">
      <div className="trust-ticker__track">
        {[...compatibility, ...compatibility].map((item, index) => (
          <span key={`${item}-${index}`}>{item}</span>
        ))}
      </div>
    </div>
  );
}
