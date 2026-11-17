import { useState } from "react";

export function ContactForm() {
  const [notice, setNotice] = useState("");

  return (
    <form
      className="contact-form"
      onSubmit={(event) => {
        event.preventDefault();
        setNotice("Le formulaire est valide, mais aucun service d’envoi n’est configuré. Votre message n’a pas été transmis.");
      }}
    >
      <div className="contact-form__fields">
        <label>
          Votre nom
          <input name="name" autoComplete="name" required />
        </label>
        <label>
          Votre adresse e-mail
          <input name="email" type="email" autoComplete="email" required />
        </label>
        <label className="contact-form__message">
          Votre message
          <textarea name="message" rows={5} required />
        </label>
      </div>
      <p className="contact-form__note">
        Aucun message ne sera envoyé tant qu’un canal de contact n’aura pas été configuré.
      </p>
      <button className="button button-primary" type="submit">Préparer le message</button>
      <p className="contact-form__status" role="status" aria-live="polite">{notice}</p>
    </form>
  );
}
