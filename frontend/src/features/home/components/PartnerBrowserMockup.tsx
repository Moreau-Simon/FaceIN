export function PartnerBrowserMockup() {
  return (
    <div className="browser-mockup browser-mockup--partner">
      <div className="browser-chrome">
        <span className="window-dots" aria-hidden="true"><i /><i /><i /></span>
        <span>atelier lune</span>
        <nav aria-label="Navigation du site illustré">
          <span>Boutique</span><span>Journal</span><span>Compte</span>
        </nav>
      </div>
      <div className="partner-login">
        <p>Connexion à votre compte</p>
        <div className="face-scan" aria-hidden="true"><span>✦</span></div>
        <span className="mock-caption">Traitement local visé</span>
        <div className="mock-primary-button"><span className="mini-brand">F</span> Connecté avec FaceIN</div>
      </div>
      <div className="verification-popover">
        <div className="popover-head"><span className="window-dots"><i /><i /><i /></span><span>verify.facein.fr</span></div>
        <strong>Récapitulatif illustratif</strong>
        <div className="verification-line"><span>Traitement local</span><b>cible</b></div>
        <div className="verification-line"><span>Image non transmise</span><b className="state-ok">✓</b></div>
        <div className="verification-line"><span>Preuve à générer</span><b>à définir</b></div>
        <div className="node-list"><span>Nœud A <b>✓</b></span><span>Nœud B <b>✓</b></span><span>Nœud C <b>!</b></span></div>
        <div className="mock-timeout">Délai dépassé</div>
        <div className="popover-consensus"><span>Seuil <b>à définir</b></span><strong>Décision simulée</strong></div>
      </div>
    </div>
  );
}
