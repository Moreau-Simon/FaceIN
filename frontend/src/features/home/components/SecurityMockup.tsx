export function SecurityMockup() {
  return (
    <aside className="security-mockup">
      <p className="mockup-title">Niveaux de vérification envisagés</p>
      <div className="security-plan">
        <span className="plan-icon"><span className="mini-brand">F</span></span>
        <div><strong>Offre Renforcée</strong><small>Niveau renforcé (cible)</small></div>
        <span className="pill">ZK</span>
        <small>Sécurité</small>
        <div className="security-meter"><i /></div>
        <div className="plan-foot"><span>Disponibilité</span><b>à venir</b></div>
      </div>
      <div className="chart-card">
        <small>Connexions illustratives</small>
        <strong>1 248</strong>
        <div className="bar-chart" role="img" aria-label="Graphique illustratif des connexions">
          {Array.from({ length: 14 }, (_, index) => <i key={index} />)}
        </div>
      </div>
    </aside>
  );
}
