import { pageFiles, pageUrl } from "../../../app/navigation";

const connectionRows = [
  ["Nouveau : Les Ateliers", "France", "1", "100 %"],
  ["Atelier Lune", "—", "7 513", "99,2 %"],
  ["Studio Kora", "Belgique", "1 352", "98,7 %"],
  ["Biblio+", "—", "1 122", "99,5 %"],
  ["Vélo Nomade", "Suisse", "3 290", "98,9 %"],
  ["Maison Sel", "—", "302", "99,0 %"],
  ["Campus Nord", "Canada", "2 021", "99,4 %"],
  ["Pixel Café", "—", "594", "97,8 %"],
];

export function DashboardMockup() {
  return (
    <article className="dashboard-showcase">
      <div className="dashboard-showcase__intro">
        <span className="mini-brand">F</span>
        <h3>Aperçu du tableau de bord visé</h3>
        <p>Données et connexions illustratives, sans authentification réelle.</p>
        <div className="dashboard-login-card">
          <div className="dashboard-user"><span>AL</span><b>Atelier Lune<small>Connexion à votre compte</small></b></div>
          <div className="choice is-selected"><i /> Mon visage <span>FaceIN</span></div>
          <div className="choice"><i /> Mot de passe</div>
          <a href={pageUrl(pageFiles.connection, "login")} className="dashboard-submit">Se connecter</a>
        </div>
      </div>
      <div className="dashboard-window">
        <div className="browser-chrome"><span className="window-dots"><i /><i /><i /></span><span>dashboard.facein.fr</span></div>
        <div className="dashboard-content">
          <aside><b><span className="mini-brand">F</span> FaceIN</b><span>Accueil</span><span>Services</span><span>Journal</span><span>Clés</span></aside>
          <div className="dashboard-table-wrap">
            <h4>Connexions par service</h4>
            <table className="dashboard-table">
              <thead><tr><th>Service</th><th>Pays</th><th>Connexions</th><th>Réussite</th></tr></thead>
              <tbody>{connectionRows.map(([service, country, count, success]) => (
                <tr key={service}><td><i />{service}</td><td>{country}</td><td>{count}</td><td>{success}</td></tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      </div>
    </article>
  );
}
