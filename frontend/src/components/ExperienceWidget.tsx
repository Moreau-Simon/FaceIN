import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "motion/react";
import { ExperienceWidgetVisual } from "./ExperienceWidgetVisual";

const closeDuration = 280;

const benefits = [
  "Votre image reste sur votre appareil",
  "Une preuve mathématique, jamais la photo",
  "Une vérification indépendante",
];

export function ExperienceWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const closeTimerRef = useRef<number | null>(null);
  const isClosingRef = useRef(false);
  const reduceMotion = useReducedMotion();

  function closeModal() {
    if (isClosingRef.current) return;
    isClosingRef.current = true;
    setIsClosing(true);
    closeTimerRef.current = window.setTimeout(() => {
      closeTimerRef.current = null;
      dialogRef.current?.close();
      setIsOpen(false);
      setIsClosing(false);
      isClosingRef.current = false;
      triggerRef.current?.focus();
    }, reduceMotion ? 0 : closeDuration);
  }

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen && !dialog.open) {
      isClosingRef.current = false;
      dialog.showModal();
      closeRef.current?.focus();
    } else if (!isOpen && dialog.open) {
      dialog.close();
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeModal();
      }
    };

    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [isOpen]);

  useEffect(() => () => {
    if (closeTimerRef.current !== null) window.clearTimeout(closeTimerRef.current);
  }, []);

  return (
    <>
      <button
        className="button experience-widget-trigger"
        type="button"
        ref={triggerRef}
        onClick={() => {
          setIsClosing(false);
          setIsOpen(true);
        }}
      >
        Explorer l’aperçu interactif <span aria-hidden="true">↗</span>
      </button>
      <dialog
        className={`experience-modal${isClosing ? " is-closing" : ""}`}
        ref={dialogRef}
        aria-labelledby="experience-modal-title"
        onCancel={(event) => {
          event.preventDefault();
          closeModal();
        }}
        onClose={() => {
          setIsOpen(false);
          setIsClosing(false);
          isClosingRef.current = false;
          triggerRef.current?.focus();
        }}
        onClick={(event) => {
          if (event.target === dialogRef.current) closeModal();
        }}
      >
        <section className="experience-modal__panel">
          <button
            className="experience-modal__close"
            type="button"
            ref={closeRef}
            aria-label="Fermer l’aperçu interactif"
            onClick={closeModal}
          >
            <span aria-hidden="true">×</span>
          </button>
          <header className="experience-modal__intro">
            <div className="experience-modal__copy">
              <p className="experience-modal__eyebrow">FACEIN · IDENTITÉ NUMÉRIQUE</p>
              <h2 id="experience-modal-title">Une preuve qui circule.<br />Votre image, jamais.</h2>
              <p>Une expérience de connexion fluide, conçue pour vérifier votre identité sans exposer votre visage.</p>
              <div className="experience-modal__actions">
                <a className="button button-primary" href="connexion.html#register">Créer mon identité <span aria-hidden="true">↗</span></a>
                <a className="button experience-modal__secondary" href="comment-ca-marche.html">Comment ça marche</a>
              </div>
            </div>
            <ul className="experience-benefits">
              {benefits.map((benefit, index) => (
                <li key={benefit} className={`experience-benefit experience-benefit--${index + 1}`}>
                  <span className="experience-benefits__icon" aria-hidden="true">✓</span>
                  <span>{benefit}</span>
                </li>
              ))}
            </ul>
          </header>
          <ExperienceWidgetVisual />
          <p className="experience-modal__disclaimer">Démo visuelle uniquement : l’interface de paiement et les indicateurs ne déclenchent aucune transaction ni authentification.</p>
        </section>
      </dialog>
    </>
  );
}
