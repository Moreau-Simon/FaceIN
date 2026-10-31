/**
 * liveness-guide.js - Couronne biométrique (60 ticks) + glyphe Face ID 2.5D piloté par GSAP
 * Chorégraphie en 2 temps par étape : démonstration centrale (1,5 s) puis dock dans la pilule.
 */
(() => {
  const NS = 'http://www.w3.org/2000/svg';
  const TICKS = 60, C = 180, R1 = 161, R2 = 175;
  const COLOR_A = '#00F0FF', COLOR_B = '#3B82F6', COLOR_OK = '#34F5B0';
  const MOUTH = { neutral: 'M36 66q12 3 24 0', smile: 'M31 61q17 20 34 0' };
  const EYES = { neutral: ['M34 38v8', 'M62 38v8'], wide: ['M34 35v13', 'M62 35v13'] };
  const BLUR_ON = 'blur(12px) brightness(0.5)', BLUR_OFF = 'blur(0px) brightness(1)';

  const STEPS = [
    { id: 'HEAD_RIGHT', title: 'Tournez la tête à droite',  counter: 'Étape 1 sur 3', pct: 33,  label: 'À droite' },
    { id: 'HEAD_LEFT',  title: 'Tournez la tête à gauche',  counter: 'Étape 2 sur 3', pct: 66,  label: 'À gauche' },
    { id: 'SMILE',      title: 'Faites un sourire franc',   counter: 'Étape 3 sur 3', pct: 100, label: 'Souriez' }
  ];

  /** Couronne de 60 micro-segments : une couche terne + une couche lumineuse (glow). */
  class BiometricRing {
    constructor(baseSvg, litSvg) {
      this.n = 0;
      this.lit = [];
      for (let i = 0; i < TICKS; i++) {
        const a = (i / TICKS) * Math.PI * 2 - Math.PI / 2, c = Math.cos(a), s = Math.sin(a);
        const make = (svg, cls) => {
          const l = document.createElementNS(NS, 'line');
          l.setAttribute('x1', C + R1 * c); l.setAttribute('y1', C + R1 * s);
          l.setAttribute('x2', C + R2 * c); l.setAttribute('y2', C + R2 * s);
          l.setAttribute('class', cls);
          svg.appendChild(l);
          return l;
        };
        make(baseSvg, 'fi-tick');
        const t = make(litSvg, 'fi-tick fi-tick-lit');
        t.dataset.color = gsap.utils.interpolate(COLOR_A, COLOR_B, i / (TICKS - 1));
        this.lit.push(t);
      }
      this.reset();
    }

    reset() {
      this.n = 0;
      gsap.killTweensOf(this.lit);
      this.lit.forEach(t => gsap.set(t, { opacity: 0, stroke: t.dataset.color }));
    }

    setProgress(pct) {
      const n = Math.round(TICKS * pct / 100);
      if (n > this.n) gsap.to(this.lit.slice(this.n, n), { opacity: 1, duration: 0.3, ease: 'power2.out', stagger: 0.02 });
      else if (n < this.n) gsap.to(this.lit.slice(n, this.n), { opacity: 0, duration: 0.2 });
      this.n = n;
    }

    celebrate() {
      gsap.to(this.lit, { opacity: 1, stroke: COLOR_OK, duration: 0.5, stagger: 0.01 });
    }
  }

  class LivenessGuide {
    /**
     * @param {Object} o  stage, glyph, pill, pillSlot, pillLabel, video, canvas, wave,
     *                    ringBase, ringLit, counterEl, titleEl, onStepReached()
     */
    constructor(o) {
      this.o = o;
      this.index = 0;
      this.held = 0;
      this.tl = null;
      this.loopTl = null;
      this.ring = new BiometricRing(o.ringBase, o.ringLit);

      const q = s => o.glyph.querySelector(s);
      this.el = {
        frame: q('#g-frame'), face: q('#g-face'), eyes: q('#g-eyes'), eyeL: q('#g-eye-l'), eyeR: q('#g-eye-r'),
        nose: q('#g-nose'), mouthW: q('#g-mouth-wrap'), mouth: q('#g-mouth'),
        arrowR: q('#g-arrow-r'), arrowRPath: q('#g-arrow-r-path'),
        arrowL: q('#g-arrow-l'), arrowLPath: q('#g-arrow-l-path'),
        check: q('#g-check'), circle: q('#g-circle'), tick: q('#g-check-path')
      };
      gsap.set([this.el.face, this.el.frame, this.el.arrowR, this.el.arrowL], { svgOrigin: '48 48' });
      gsap.set(this.el.nose, { svgOrigin: '48 36' });
    }

    /* ---------- Cycle de vie ---------- */

    reset() {
      const o = this.o;
      this.kill();
      this.index = 0;
      this.held = 0;
      this.ring.reset();
      gsap.set(o.video, { filter: BLUR_OFF });
      gsap.set(o.canvas, { opacity: 1 });
      gsap.set(o.pill, { autoAlpha: 0, clearProps: 'transform' });
      gsap.set(o.wave, { opacity: 0 });
      this.resetGlyph();
      gsap.set(o.glyph, { opacity: 0 });
      o.counterEl.textContent = 'Préparation…';
      o.titleEl.textContent = 'Positionnez votre visage au centre';
    }

    start() { this.playStep(0); }
    stop() { this.kill(); }

    kill() {
      const o = this.o, e = this.el;
      [this.tl, this.loopTl].forEach(t => t && t.kill());
      this.tl = this.loopTl = null;
      gsap.killTweensOf([o.glyph, o.pill, o.video, o.canvas, o.wave, e.face, e.frame, e.check, e.circle, e.tick]);
    }

    resetGlyph() {
      const e = this.el;
      gsap.set(this.o.glyph, { x: 0, y: 0, scale: 1, color: '#7DF3FF' });
      gsap.set([e.face, e.frame], { opacity: 1, scale: 1, x: 0 });
      gsap.set([e.eyes, e.nose, e.mouthW], { x: 0, rotation: 0 });
      gsap.set(e.mouth, { attr: { d: MOUTH.neutral } });
      gsap.set(e.eyeL, { attr: { d: EYES.neutral[0] } });
      gsap.set(e.eyeR, { attr: { d: EYES.neutral[1] } });
      gsap.set([e.arrowR, e.arrowL], { opacity: 0 });
      gsap.set([e.arrowRPath, e.arrowLPath], { strokeDasharray: 100, strokeDashoffset: 100 });
      gsap.set(e.check, { opacity: 0 });
      gsap.set([e.circle, e.tick], { strokeDasharray: 100, strokeDashoffset: 100 });
    }

    /* ---------- Validation d'étape ---------- */

    /** Détection locale : valide l'étape après ~0,5 s de maintien. */
    processMetrics(m) {
      const step = STEPS[this.index];
      if (!step) return;
      const ok = (step.id === 'HEAD_RIGHT' && m.yaw > 0.35) ||
                 (step.id === 'HEAD_LEFT' && m.yaw < -0.35) ||
                 (step.id === 'SMILE' && m.smile > 0.46);
      this.held = ok ? this.held + 1 : Math.max(0, this.held - 1);
      if (this.held >= 15) { this.held = 0; this.o.onStepReached(); }
    }

    /** Étape validée : allume la couronne, passe à la suivante. Retourne true si c'était la dernière. */
    validateStep() {
      this.ring.setProgress(STEPS[this.index].pct);
      this.held = 0;
      this.index++;
      if (this.index < STEPS.length) { this.playStep(this.index); return false; }
      return true;
    }

    /* ---------- Chorégraphie ---------- */

    playStep(i) {
      const s = STEPS[i], o = this.o;
      this.kill();
      this.resetGlyph();
      o.counterEl.textContent = s.counter;
      o.titleEl.textContent = s.title;
      o.pillLabel.textContent = s.label;
      gsap.set(o.pill, { autoAlpha: 0, clearProps: 'transform' });

      // Phase 1 : démonstration centrale (1,5 s)
      this.tl = gsap.timeline()
        .to(o.video, { filter: BLUR_ON, duration: 0.35, ease: 'power2.out' }, 0)
        .to(o.canvas, { opacity: 0.12, duration: 0.35 }, 0)
        .fromTo(o.glyph, { opacity: 0, scale: 0.55 }, { opacity: 1, scale: 1, duration: 0.45, ease: 'back.out(1.7)' }, 0)
        .add(this.demo(s.id, 0), 0.35)
        .add(() => this.dock(s.id), 1.5);
    }

    /** Phase 2 : le glyphe se loge dans la pilule, le flou se dissipe, le scan LiDAR réapparaît. */
    dock(id) {
      const o = this.o;
      const st = o.stage.getBoundingClientRect(), sl = o.pillSlot.getBoundingClientRect();
      const dx = sl.left + sl.width / 2 - (st.left + st.width / 2);
      const dy = sl.top + sl.height / 2 - (st.top + st.height / 2);

      gsap.fromTo(o.pill, { autoAlpha: 0, y: 10, scale: 0.85 }, { autoAlpha: 1, y: 0, scale: 1, duration: 0.45, ease: 'back.out(1.7)' });
      gsap.to(o.glyph, {
        x: dx, y: dy, scale: sl.width / 128, duration: 0.7, ease: 'power3.inOut',
        onComplete: () => { this.loopTl = this.demo(id, -1); }
      });
      gsap.to(o.video, { filter: BLUR_OFF, duration: 0.6, ease: 'power2.out' });
      gsap.to(o.canvas, { opacity: 1, duration: 0.6 });
    }

    /** Animation 2.5D : parallaxe par calque + compression perspective, ou morphing du sourire. */
    demo(id, repeat) {
      const e = this.el, d = 0.42, ease = 'power2.inOut';
      const tl = gsap.timeline({ repeat, repeatDelay: 0.25 });

      if (id === 'SMILE') {
        tl.to(e.mouth, { attr: { d: MOUTH.smile }, duration: d, ease }, 0)
          .to(e.eyeL, { attr: { d: EYES.wide[0] }, duration: d, ease }, 0)
          .to(e.eyeR, { attr: { d: EYES.wide[1] }, duration: d, ease }, 0)
          .to(e.mouth, { attr: { d: MOUTH.neutral }, duration: d, ease }, d + 0.3)
          .to(e.eyeL, { attr: { d: EYES.neutral[0] }, duration: d, ease }, d + 0.3)
          .to(e.eyeR, { attr: { d: EYES.neutral[1] }, duration: d, ease }, d + 0.3);
        return tl;
      }

      const isRight = id === 'HEAD_RIGHT';
      const dir = isRight ? 1 : -1;
      const arrow = isRight ? e.arrowR : e.arrowL;
      const arrowPath = isRight ? e.arrowRPath : e.arrowLPath;

      // Rotation de la tête 2.5D et animation de la flèche correspondante (gauche ou droite)
      tl.to(e.face, { scaleX: 0.88, duration: d, ease }, 0)
        .to(e.eyes, { x: 5 * dir, duration: d, ease }, 0)
        .to(e.nose, { x: 9 * dir, rotation: 14 * dir, duration: d, ease }, 0)
        .to(e.mouthW, { x: 4 * dir, duration: d, ease }, 0)
        .to(arrow, { opacity: 1, duration: 0.18 }, 0)
        .fromTo(arrowPath, { strokeDashoffset: 100 }, { strokeDashoffset: 0, duration: d + 0.08, ease: 'power1.out' }, 0)
        .to(arrow, { x: 4 * dir, duration: d * 0.5, yoyo: true, repeat: 1, ease: 'sine.inOut' }, 0.1)
        .to(e.face, { scaleX: 1, duration: d, ease }, d + 0.3)
        .to([e.eyes, e.nose, e.mouthW], { x: 0, rotation: 0, duration: d, ease }, d + 0.3)
        .to(arrow, { opacity: 0, x: 0, duration: 0.2 }, d + 0.3);
      return tl;
    }

    /** Succès : glyphe au centre -> checkmark animé + onde radiale. Résolu une fois le statut lisible. */
    playSuccess() {
      const o = this.o, e = this.el;
      this.kill();
      this.ring.celebrate();
      o.counterEl.textContent = 'Authentification réussie';
      o.titleEl.textContent = 'Identité vérifiée • Preuve ZKP validée';
      return new Promise(resolve => {
        gsap.timeline({ onComplete: resolve })
          .to(o.video, { filter: BLUR_ON, duration: 0.4 }, 0)
          .to(o.canvas, { opacity: 0, duration: 0.3 }, 0)
          .to(o.pill, { autoAlpha: 0, duration: 0.25 }, 0)
          .to(o.glyph, { x: 0, y: 0, scale: 1.15, opacity: 1, color: '#6EF2B8', duration: 0.6, ease: 'back.out(1.4)' }, 0)
          .to([e.face, e.frame], { opacity: 0, scale: 0.6, duration: 0.35, ease: 'power2.in' }, 0.1)
          .set(e.check, { opacity: 1 }, 0.4)
          .to(e.circle, { strokeDashoffset: 0, duration: 0.5, ease: 'power2.out' }, 0.4)
          .to(e.tick, { strokeDashoffset: 0, duration: 0.4, ease: 'power2.out' }, 0.7)
          .fromTo(o.wave, { scale: 0.55, opacity: 0.8 }, { scale: 1.35, opacity: 0, duration: 1.1, ease: 'power2.out' }, 0.7)
          .to({}, { duration: 0.9 });
      });
    }
  }

  window.LivenessGuide = LivenessGuide;
})();
