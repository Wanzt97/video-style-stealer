# Construire le gabarit HyperFrames

Le gabarit est un projet HyperFrames que le skill du style copie à chaque nouveau montage. Il porte les valeurs de la fiche, pour qu'on ne règle plus que des temps de voix.

Un départ est déjà en place dans `STYLE/gabarit/` : un moteur de base, un habillage neutre, un modèle d'exemple et une démonstration qui passe `hyperframes check`. Il reste à le mettre au style.

## Avant

- Lire le contrat de composition de HyperFrames (skill `hyperframes-core` ou documentation) : sous-compositions dans `<template>`, `window.__timelines`, attributs `data-*`.
- La fiche doit être finie, section 12 comprise.

## L'ordre

1. **Les valeurs.** `node STYLE/scripts/jetons.mjs` écrit `gabarit/lib/jetons.js` depuis la fiche. À relancer après chaque retouche de la section 12. Ne jamais corriger `jetons.js` à la main.
2. **L'habillage.** Dans `lib/habillage.css`, remplacer le bloc `:root` par les valeurs de `HABILLAGE-reference.md`. Déposer les polices libres dans `assets/fonts/` avec leur fichier de licence, les déclarer en `@font-face` sous un nom de **rôle** (« Titre », « Technique »), jamais sous le nom de la police.
3. **Le moteur.** Dans `lib/moteur.js`, ajouter une fonction par geste de la fiche (section 4). Chaque fonction lit ses durées avec `lire("bloc.cle")`. Un jeton manquant lève une erreur : c'est voulu.
4. **Les modèles.** Un fichier par type de scène de la fiche (section 7) dans `compositions/`, à partir de `m00-exemple.html`. Plusieurs types proches peuvent partager un modèle. Supprimer `m00-exemple.html` à la fin.
5. **La démonstration.** `index.html` enchaîne tous les modèles entre des blocs visage, aux proportions de la fiche. C'est elle que l'utilisateur regarde pour valider le style.
6. **Le mode d'emploi.** Remplir `gabarit/README.md` : les modèles, les étapes, les fonctions du moteur.
7. **Le contrôle** (plus bas).

## Les règles d'un modèle

- **Aucune durée d'animation, aucune courbe dans un modèle.** Seulement des temps de voix, regroupés dans une section `LES BEATS` en tête du script, en secondes locales à la scène.
- **Un contenu de démonstration neutre** : « La phrase clé », « Source · date ». Aucun texte, logo ou image de la vidéo de référence.
- **Les pièces réelles ont un emplacement « À remplacer »** (classe `a-remplacer`) : captures, extraits, logos viennent de l'utilisateur.
- **L'identifiant du modèle préfixe tous ses `id`** (`m03-titre`) : plusieurs scènes vivent dans la même page.
- **Styles et scripts dans le `<template>`**, pas dans le `<head>` du fichier.

## Les pièges, tous déjà rencontrés

**Une scène masquée ne se mesure pas.** Tant qu'une sous-composition n'est pas à l'écran, elle est en `display: none` : `offsetWidth`, `offsetLeft` et `getBoundingClientRect` rendent 0. Tout calcul de position (caméra qui vise un élément, trait qui relie deux blocs) doit se faire **à la première image où la scène est visible**, puis se garder en mémoire :

```js
const mesurable = () => monde.offsetWidth > 0;
function viser(cible) {
  const v = { fixe: null };
  v.lire = () => {
    if (v.fixe) return v.fixe;
    const r = mesurer(cible);        // lit offsetLeft, offsetTop, offsetWidth…
    if (mesurable()) v.fixe = r;     // on ne garde que si la mesure est vraie
    return r;
  };
  return v;
}
```

Symptôme quand on l'oublie : les images de contrôle sont noires ou cadrées sur le coin haut gauche.

**Les polices arrivent tard.** Une police utilisée seulement dans une scène masquée ne se charge pas seule, et la largeur des textes change à son arrivée. Construire chaque scène dans `Moteur.pret([...polices], () => { ... })`.

**Le rendu ne lit pas les images dans l'ordre.** Il saute à n'importe quel instant. Tout ce qui n'est pas une interpolation GSAP posée sur la timeline doit être une **fonction du temps** qui recalcule son état depuis zéro (`sc.aChaqueImage((t) => …)`). Jamais d'état accumulé d'une image à l'autre, jamais de `setTimeout`, jamais de `Math.random()` sans graine.

**Une caméra virtuelle se calcule sur le logarithme du zoom.** Interpoler l'échelle elle-même donne un mouvement qui accélère en zoom avant et traîne en zoom arrière. Écrire `s = de * Math.pow(vers / de, p)`.

**La 3D s'aplatit.** `opacity` ou `filter` sur un élément en `transform-style: preserve-3d` écrase la profondeur. Mettre le fondu sur un bloc parent, la rotation sur l'enfant.

**Les repères du studio.** HyperFrames Studio écrit des `data-hf-id` dans les fichiers et crée des dossiers cachés. `empaqueter` les retire du paquet ; ne pas les recopier à la main d'un fichier à l'autre.

**Un avertissement n'est pas toujours un défaut.** Si la fiche demande d'éteindre les éléments quittés, le contrôle de contraste les signalera. Le noter dans `gabarit/README.md` pour que personne ne le « corrige ».

## Ce que le moteur de base contient

| Fonction | Effet | Jetons lus |
|---|---|---|
| `Moteur.pret(polices, f)` | attend les polices, puis construit | — |
| `Moteur.scene({ tl, duree })` | ouvre une scène, rend `sc` | — |
| `sc.auMot(t)` | décale un temps de voix | `entrees.calage_apres_le_mot_ms` |
| `sc.apparaitre(cible, t)` | fondu d'entrée | `entrees.fondu_ms`, `entrees.fondu_courbe` |
| `sc.dUnCoup(cible, t)` | visible en une image | — |
| `sc.cascade(cible, t)` | éléments à la suite | `entrees.cascade_ms` |
| `sc.motAMot(cible, temps)` | texte mot à mot | ceux d'`apparaitre` et d'`auMot` |
| `sc.compteur(cible, {a, t, fin})` | nombre qui monte | `compteur.ms` |
| `sc.aChaqueImage(f)` | fonction libre du temps | — |
| `sc.terminer()` | à appeler en dernier | — |
| `Moteur.visage(tl, cible, blocs)` | zoom lent du visage par bloc | `visage.zoom_de`, `visage.zoom_a` |

Si le style n'utilise pas un geste (pas de compteur, pas de mot à mot), retirer la fonction et le jeton : un gabarit ne propose que ce que la fiche autorise.

## Le contrôle

```bash
node STYLE/scripts/jetons.mjs --verifier
cd STYLE/gabarit && npx hyperframes check --snapshots
```

1. `check` doit finir sur « Check passed ».
2. Ouvrir les images de `snapshots/` : une par scène au moins. Vérifier le cadrage, la lisibilité, le nombre d'accents à l'écran.
3. Demander des images à des instants précis pour les gestes délicats : `npx hyperframes snapshot --at 12.4`.
4. Rendre **une** scène en vidéo et la regarder image par image sur un geste mesuré : la durée doit être celle de la fiche.
5. `node STYLE/scripts/controle-plan.mjs STYLE/gabarit/storyboard.exemple.json` : la démonstration doit respecter les tolérances de la fiche.
6. Relire « Ce que le style ne fait jamais » en regardant la démonstration.

L'aperçu pour l'utilisateur : `npx hyperframes preview`, lancé **depuis** `STYLE/gabarit`.
