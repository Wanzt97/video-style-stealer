/*
 * Moteur de base du gabarit.
 *
 * Il ne contient aucune durée ni aucune courbe : tout vient de window.JETONS (lib/jetons.js),
 * fabriqué depuis la section 12 de FICHE.md par scripts/jetons.mjs.
 * Les modèles de scène n'écrivent jamais une durée en dur : ils appellent ces fonctions.
 *
 * C'est une base. Les gestes propres au style (caméra virtuelle, surlignage, bascule…) s'ajoutent
 * dans scene(), sur le même principe : une valeur lue dans les jetons, un temps donné par la scène.
 */
(function () {
  const JETONS = window.JETONS || {};

  // Un jeton absent est une erreur : on ne remplace jamais une valeur de la fiche par une valeur inventée.
  function lire(chemin) {
    const v = chemin.split(".").reduce((o, k) => (o == null ? o : o[k]), JETONS);
    if (v === undefined || v === null || (typeof v === "string" && v.includes("{{")))
      throw new Error(`Jeton manquant : ${chemin}. L'écrire dans FICHE.md (section 12), puis relancer scripts/jetons.mjs.`);
    return v;
  }
  const s = (ms) => ms / 1000;
  const borne = (v) => Math.max(0, Math.min(1, v));

  function bezier(x1, y1, x2, y2) {
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
    const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    const X = (t) => ((ax * t + bx) * t + cx) * t;
    const Y = (t) => ((ay * t + by) * t + cy) * t;
    return (p) => {
      if (p <= 0) return 0;
      if (p >= 1) return 1;
      let bas = 0, haut = 1, t = p;
      for (let i = 0; i < 40; i++) {
        if (X(t) < p) bas = t; else haut = t;
        t = (bas + haut) / 2;
      }
      return Y(t);
    };
  }
  // Une courbe de la fiche : quatre nombres, ou "lineaire".
  const courbe = (chemin) => { const c = lire(chemin); return Array.isArray(c) ? bezier(...c) : "none"; };

  const liste = (cible) =>
    typeof cible === "string"
      ? Array.from(document.querySelectorAll(cible))
      : cible instanceof Element ? [cible] : Array.from(cible);
  const un = (cible) => liste(cible)[0];

  /*
   * Une scène.
   *   tl      la timeline GSAP en pause de la sous-composition
   *   duree   la durée de la scène en secondes (= data-duration du host)
   */
  function scene({ tl, duree }) {
    const horloges = [];
    const sc = {
      tl,

      /** Décale un instant de voix : l'élément apparaît un peu après le début de son mot. */
      auMot: (t) => t + s(lire("entrees.calage_apres_le_mot_ms")),

      /** Entrée standard : fondu sur place. */
      apparaitre(cible, t) {
        tl.fromTo(liste(cible), { opacity: 0 }, { opacity: 1, duration: s(lire("entrees.fondu_ms")), ease: courbe("entrees.fondu_courbe") }, t);
        return sc;
      },

      /** Visible d'un coup, en une image. */
      dUnCoup(cible, t) {
        tl.fromTo(liste(cible), { opacity: 0 }, { opacity: 1, duration: 0.001, ease: "none" }, t);
        return sc;
      },

      /** Plusieurs éléments à la suite, à l'écart fixé par la fiche. */
      cascade(cible, t) {
        const pas = s(lire("entrees.cascade_ms"));
        liste(cible).forEach((el, i) => sc.apparaitre(el, t + i * pas));
        return sc;
      },

      /** Texte mot à mot. `temps` = début de chaque mot dans la voix, en secondes locales à la scène. */
      motAMot(cible, temps) {
        const el = un(cible);
        const mots = el.textContent.trim().split(/\s+/);
        el.textContent = "";
        mots.forEach((mot, i) => {
          const span = document.createElement("span");
          span.textContent = mot;
          el.appendChild(span);
          if (i < mots.length - 1) el.appendChild(document.createTextNode(" "));
          sc.apparaitre(span, sc.auMot(temps[Math.min(i, temps.length - 1)]));
        });
        if (temps.length !== mots.length) console.warn(`${mots.length} mots mais ${temps.length} temps pour`, el.id);
        return sc;
      },

      /** Compteur. Il s'arrête à `fin` (fin du nombre dans la voix) ou après la durée de la fiche. */
      compteur(cible, { de = 0, a, t, fin, ecrire = (v) => String(Math.round(v)) }) {
        const el = un(cible);
        const d = fin ? fin - t : s(lire("compteur.ms"));
        const poser = (v) => { el.textContent = ecrire(v); };
        horloges.push((temps) => poser(de + (a - de) * (1 - Math.pow(1 - borne((temps - t) / d), 3))));
        poser(de);
        sc.apparaitre(el, t);
        return t + d;
      },

      /** Fonction libre, recalculée à chaque image à partir du temps de la scène. */
      aChaqueImage(f) { horloges.push(f); return sc; },

      /** À appeler en dernier. Renvoie la timeline à enregistrer dans window.__timelines. */
      terminer() {
        // Une seule horloge fait avancer tout ce qui n'est pas une interpolation GSAP.
        // Chaque fonction recalcule son état depuis le temps : le rendu est exact quelle que soit l'image demandée.
        const horloge = { t: 0 };
        const appliquer = (t) => horloges.forEach((f) => f(t));
        tl.to(horloge, { t: duree, duration: duree, ease: "none", onUpdate: () => appliquer(horloge.t) }, 0);
        appliquer(0);
        return tl;
      },
    };
    return sc;
  }

  /**
   * Zoom lent du visage, bloc par bloc, si la fiche en donne un. Il repart du début à chaque retour au visage.
   *   blocs   [[debut, fin], ...] en secondes de montage
   */
  function visage(tl, cible, blocs) {
    const de = lire("visage.zoom_de"), a = lire("visage.zoom_a");
    if (de === a) return;
    blocs.forEach(([debut, fin]) => {
      tl.fromTo(cible, { scale: de }, { scale: a, transformOrigin: "50% 40%", duration: fin - debut, ease: "none" }, debut);
    });
  }

  /**
   * Attend les polices avant de construire la scène : la place des textes dépend de leur largeur réelle,
   * et une police utilisée seulement dans une scène masquée ne se charge pas toute seule.
   *   polices   ['800 100px "Titre"', '400 40px "Technique"']
   */
  const pret = (polices, construire) =>
    Promise.all((polices || []).map((f) => document.fonts.load(f))).then(() => document.fonts.ready).then(construire);

  /** Démonstration seulement : des temps réguliers. Dans un vrai montage, les temps viennent de la transcription. */
  const cadence = (t0, n, pas) => Array.from({ length: n }, (_, i) => +(t0 + i * pas).toFixed(3));

  window.Moteur = { JETONS, lire, bezier, scene, visage, pret, cadence };
})();
