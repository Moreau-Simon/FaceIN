import { useState } from "react";

export function ContactForm() {
  const [notice, setNotice] = useState("");

  return (
    <form
      className="contact-form"
      onSubmit={(event) => {
        event.preventDefault();
        setNotice("Votre message est prêt, mais l’envoi n’est pas encore activé. Il n’a pas été transmis.");
      }}
    >
      <label className="field"><span>Nom</span><input name="name" autoComplete="name" required /></label>
      <label className="field"><span>Adresse e-mail</span><input name="email" type="email" autoComplete="email" required /></label>
      <label className="field contact-form__message"><span>Message</span><textarea name="message" rows={5} required /></label>
      <div className="contact-form__foot">
        <button className="button button-primary" type="submit">Envoyer le message</button>
        <p className="contact-form__status" role="status" aria-live="polite">{notice}</p>
      </div>
    </form>
  );
}
