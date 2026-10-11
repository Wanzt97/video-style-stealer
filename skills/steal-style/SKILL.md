---
name: steal-style
description: "Analyse une vidéo de référence (lien YouTube ou fichier) et en tire un design system vidéo réutilisable : une fiche de règles de montage mesurées, un habillage, un gabarit HyperFrames et un skill prêt à installer pour monter dans ce style. À utiliser quand on donne un lien de vidéo et qu'on demande de copier, voler, reproduire ou analyser son style de montage, ou de créer un design system vidéo. Triggers: steal this editing style, copy the editing style of this video, video design system from a reference video."
---

# steal-style

On donne une vidéo. On repart avec un style de montage qu'on peut appliquer à ses propres vidéos, autant de fois qu'on veut.

Ce que le skill fabrique, dans un dossier au nom du style :

| Pièce | Ce que c'est |
|---|---|
| `FICHE.md` | La grammaire du style : quand animer, comment, à quel rythme, ce qu'on ne fait jamais. Chaque règle porte son niveau de preuve. **Elle fait foi.** |
| `HABILLAGE-reference.md` | La peau : couleurs, rôles des polices, textures. Se remplace par une marque sans toucher à la grammaire. |
| `SIGNATURE.md` | Ce que l'utilisateur ajoute de lui-même (sons, logo, formule de fin). Jamais copié de la référence. |
| `gabarit/` | Un projet HyperFrames : un modèle par type de scène, un moteur qui porte les valeurs de la fiche. |
| `SKILL.md` + `scripts/` | Le skill du style : celui qu'on installe pour monter. |
| `<nom>.zip` | Le tout, prêt à installer. |

On copie une **façon de monter**. On ne copie ni les images, ni la musique, ni les logos, ni le texte de la vidéo d'origine.

## Les cinq règles qui ne se discutent pas

1. **Un chiffre vient d'un fichier.** Toute valeur écrite dans la fiche se retrouve dans `analyse/` (`mesures.json`, un CSV, une planche). Un chiffre qu'on ne peut pas montrer n'entre pas dans la fiche. Ne jamais arrondir vers une valeur « qui sonne bien », ne jamais compléter par ce qu'on croit savoir du genre.
2. **Chaque règle porte son niveau de preuve** : *Mesuré* (calculé sur les images ou le son), *Compté* (tant de cas sur tant), *Lu* (vu sur des planches, sans compte), *Choix* (décision prise pour combler un vide). Une seule vidéo suffit à condition de ne jamais cacher ce niveau.
3. **Regarder avant d'écrire.** Les scripts mesurent, ils ne comprennent pas. Toute famille de plan, tout type d'animation, toute couleur se vérifie sur une planche d'images, à l'œil.
4. **Une règle de décision se teste.** « Quand le texte dit X, l'image fait Y » ne s'écrit qu'après avoir compté les cas pour et les cas contre. Sous 75 % ou sous 8 cas, ce n'est pas une règle : c'est un arbitrage ou une incertitude, et on l'écrit comme tel.
5. **La grammaire, la peau et la signature restent séparées.** C'est ce qui permet de garder le style et de changer de marque.

## Avant de commencer

**Outils.** Lancer d'abord la vérification :

```bash
uv run SKILL/scripts/analyse.py verifier
```

Elle dit ce qui est installé, ce qui manque et la commande pour l'installer. Lire sa sortie à l'utilisateur en langage courant.
- `MANQUE` : indispensable. Donner la commande d'installation et attendre.
- `ABSENT` : ne concerne que le gabarit (étape 8). Prévenir dès maintenant qu'on s'arrêtera à la fiche si rien n'est installé d'ici là.
- Si la commande `uv` elle-même est introuvable : macOS `brew install uv`, autres systèmes https://docs.astral.sh/uv/.

Les bibliothèques Python s'installent toutes seules à ce premier lancement.

**Ce qu'il faut savoir de l'utilisateur.** Le demander en une fois s'il ne l'a pas dit, sinon prendre le choix par défaut et l'annoncer :
- le lien ou le fichier de la vidéo ;
- le nom du style, en anglais, minuscules et tirets (par défaut : en proposer trois, tirés de ce que la vidéo a de plus reconnaissable, après l'étape 7) ;
- son outil de montage (par défaut : HyperFrames) ;
- la langue de la fiche (par défaut : celle de la conversation).

**Durée.** Compter 5 à 10 minutes de calcul pour une vidéo de 15 minutes, plus le temps de lecture des planches. Sous 2 minutes de vidéo, prévenir que les règles de rythme reposeront sur trop peu de cas.

Dans la suite, `SKILL` est le dossier de ce skill et `STYLE` le dossier du style en cours (par exemple `./mon-style`). Toutes les commandes se lancent ainsi :

```bash
uv run SKILL/scripts/analyse.py <commande> STYLE
```

## Étape 1 : récupérer et découper

```bash
uv run SKILL/scripts/analyse.py demarrer STYLE
uv run SKILL/scripts/analyse.py recuperer "<lien ou fichier>" STYLE
uv run SKILL/scripts/analyse.py plans STYLE
uv run SKILL/scripts/analyse.py signaux STYLE
uv run SKILL/scripts/transcrire.py STYLE --noms "Noms propres, marques, mots rares"
```

`signaux` et `transcrire.py` sont longs et indépendants : les lancer en même temps. Pour un essai rapide sur un extrait : `recuperer ... --de 0 --a 180`.

## Étape 2 : regarder les plans et les nommer

Ouvrir **toutes** les planches `STYLE/analyse/planches/plans_XX.jpg`. Chaque vignette est l'image du milieu d'un plan, avec son numéro.

Écrire `STYLE/analyse/etiquettes_plans.txt`, une ligne par plan (format et exemples : `references/etiquettes.md`) :

```
1|visage||Face caméra, plan poitrine, fond sombre|
2-3|animation|mur de vignettes|Grille d'extraits qui se remplit|étiquettes sous chaque vignette
```

La famille dit **ce qui remplit le cadre** : `visage`, `animation`, `ecran` (capture d'écran filmée en continu), `b-roll` (extrait plein cadre), `autre`. Un extrait posé dans un cadre dessiné est une `animation`.

Les planches `coupes_XX.jpg` montrent les coupes sautées possibles dans les plans face caméra. Noter dans `analyse/coupes_confirmees.txt` les numéros d'image où le saut est net (la tête change de place entre −1 et 0). Elles ne changent que la durée des plans : si elles sont trop nombreuses, en vérifier 40 et le dire dans la fiche.

```bash
uv run SKILL/scripts/analyse.py etiqueter STYLE
```

La commande signale les plans où sa détection de visage contredit l'étiquette : les revoir sur planche.

## Étape 3 : les animations

```bash
uv run SKILL/scripts/analyse.py mouvements STYLE
```

Ouvrir les planches `mouvements_XX.jpg` : une ligne de 8 images par animation. Nommer chaque animation dans `analyse/etiquettes_mouvements.txt` (`M017|pliage 3D|un cube se déplie`), avec une **liste de types fermée** qu'on construit en avançant : 15 types au plus. Au-delà de 150 animations, en nommer une sur deux et le dire dans la fiche. Puis `etiqueter`.

Ce que la mesure donne seule : durée de chaque mouvement, vols de caméra (durée entre images clés, courbe de Bézier), durée d'entrée des éléments, position et taille. Ce qu'elle ne donne pas : le nom du geste, ce qui sort de l'écran, la raison du geste. Cela se lit sur les planches.

## Étape 4 : les couleurs

```bash
uv run SKILL/scripts/analyse.py couleurs STYLE
```

Regarder `planches/couleurs.jpg`, puis vérifier chaque couleur retenue sur une vraie image (`planche --temps ...`). Piège connu : une couleur d'accent ressort avec deux ou trois valeurs voisines selon l'image. En retenir une, celle des grands aplats, et la noter *Mesuré* avec le nombre de pixels.

## Étape 5 : quand anime-t-on ?

C'est la partie la plus utile de la fiche et la plus facile à inventer. La faire lentement.

```bash
uv run SKILL/scripts/analyse.py phrases STYLE
```

1. Lire `analyse/phrases.csv` : chaque phrase prononcée, ce qui est à l'écran quand elle commence, le nombre d'animations qu'elle déclenche.
2. Donner à chaque phrase une **nature**, dans une liste fermée de 8 au plus (par exemple : `fait`, `raisonnement`, `question`, `transition`, `exemple`, `avis`, `adresse au public`). L'écrire dans `analyse/etiquettes_phrases.txt` (`P012|fait`). Nommer la nature d'après le texte seul, sans regarder la colonne `a_l_ecran` : sinon le test ne vaut rien.
3. `etiqueter`, puis :

```bash
uv run SKILL/scripts/analyse.py croiser STYLE
uv run SKILL/scripts/analyse.py croiser STYLE --ligne chiffre
uv run SKILL/scripts/analyse.py croiser STYLE --ligne premier_mot
```

4. Écrire le tableau de décision : des questions posées dans l'ordre, on s'arrête au premier « oui ». Chaque ligne porte son compte (« 29 cas sur 31 »). Les natures qui ne tranchent pas deviennent des arbitrages. Les exceptions se lisent une à une : elles disent souvent la règle suivante.

## Étape 6 : rassembler

```bash
uv run SKILL/scripts/analyse.py mesures STYLE
```

Lire `STYLE/MESURES.md` en entier, y compris « À lire avec prudence ».

## Étape 7 : écrire la fiche, l'habillage, la signature

Suivre `references/ecrire-la-fiche.md`, section par section. Les fichiers à remplir sont déjà dans `STYLE/` : tous les `{{emplacements}}` doivent disparaître.

**Premier arrêt obligatoire.** Montrer à l'utilisateur, en langage courant :
- le style en trois phrases ;
- les cinq chiffres qui le résument ;
- le tableau de décision ;
- ce qui reste incertain, et pourquoi ;
- trois noms possibles s'il n'en a pas donné.

Attendre son retour avant de construire.

## Étape 8 : le gabarit

Un départ est déjà dans `STYLE/gabarit/` : moteur de base, habillage neutre, modèle d'exemple, démonstration. Le mettre au style en suivant `references/gabarit-hyperframes.md`.

Les skills HyperFrames doivent être disponibles dans le projet. Sinon le dire à l'utilisateur ; ne pas les installer d'office.

**Sans HyperFrames** : ne pas improviser un gabarit pour un autre outil. Supprimer `STYLE/gabarit/`, retirer du `SKILL.md` du style ce qui en parle, livrer la fiche, l'habillage et le bloc de valeurs, et dire clairement que le gabarit reste à faire.

## Étape 9 : le skill du style, le contrôle, le paquet

1. Remplir `STYLE/SKILL.md` (le modèle est en place) : c'est le skill que l'utilisateur installera.
2. Relire la fiche contre `MESURES.md` : chaque chiffre, un par un.
3. Vérifier qu'aucune image, aucun son, aucun logo, aucune police sans licence libre de la vidéo d'origine n'est dans le dossier, hors `analyse/`.
4. `node STYLE/scripts/jetons.mjs --verifier` si le gabarit existe.

**Second arrêt obligatoire** : montrer le gabarit en aperçu, attendre l'accord, puis :

```bash
uv run SKILL/scripts/analyse.py empaqueter STYLE
```

Le zip ne contient jamais `analyse/`. Dire à l'utilisateur où est le zip et comment l'installer (`references/installer-un-style.md`).

## Ce que le skill ne sait pas faire

- **Écouter.** Il mesure les silences, le niveau du fond sonore et si les animations tombent sur des attaques sonores. Il ne reconnaît ni un bruitage ni une musique. Le son du style reste en grande partie un *Choix*.
- **Lire les intentions.** Il compte ce qui se passe, pas pourquoi. Le « pourquoi » d'une règle est une lecture, à noter *Lu*.
- **Généraliser.** Une vidéo dit comment cette vidéo est montée. Deux vidéos du même auteur diraient ce qui tient au style et ce qui tient au sujet.
- **Les formats sans voix.** Sans parole, l'étape 5 n'existe pas : le rythme se cale alors sur la musique, que le skill ne mesure pas.

## Fichiers de référence

| Fichier | Quand le lire |
|---|---|
| `references/methode.md` | Une fois, au début : pourquoi ces étapes, et les erreurs déjà commises. |
| `references/etiquettes.md` | Aux étapes 2, 3 et 5. |
| `references/ecrire-la-fiche.md` | À l'étape 7. |
| `references/gabarit-hyperframes.md` | À l'étape 8. |
| `references/installer-un-style.md` | À la fin. |
