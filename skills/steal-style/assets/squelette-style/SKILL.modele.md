---
name: "{{nom-du-style}}"
description: "{{Une phrase : ce que fait le skill, avec quel outil, pour quel genre de vidéo. Puis : À utiliser quand on demande le style {{nom-du-style}}.}}"
---

# {{nom-du-style}}

Ce skill prend des rushs et produit une vidéo dans le style {{nom-du-style}} : {{le style en une phrase}}.

Le style n'est pas décrit ici. Il vit dans les fichiers de ce dossier, et ce skill ne fait que les appliquer.

| Fichier | Ce qu'il contient | Quand le lire |
|---|---|---|
| `FICHE.md` | La grammaire : quand animer, comment, à quel rythme, ce qu'on ne fait jamais. **Elle fait foi.** | En entier, avant le plan. |
| `HABILLAGE-reference.md` | Couleurs, polices, matières. | Avant la construction. |
| `SIGNATURE.md` | Les sons et la marque de l'utilisateur. | Avant de poser le son. |
| `gabarit/` | Un projet HyperFrames prêt à copier : un modèle par type de scène, un moteur, un habillage. | Avant la construction : lire `gabarit/README.md`. |
| `scripts/` | Contrôle du plan, valeurs du gabarit, export scène par scène. | Aux étapes 3, 6 et 7. |

## Les règles qui ne se discutent pas

1. **La fiche fait foi.** Si elle contredit ce skill, le gabarit ou une habitude de l'outil, c'est elle qui a raison.
2. **Aucune durée, aucune courbe écrite à la main.** Tout mouvement passe par les fonctions du moteur, qui lisent `gabarit/lib/jetons.js`. Dans une scène, les seuls chiffres qu'on règle sont les temps de la voix.
3. **La liste des scènes est fermée** (FICHE, section 7). Si un passage demande autre chose, le dire et proposer le modèle le plus proche.
4. **Rien ne s'invente.** Une citation, un chiffre, une capture, un extrait : fournis par l'utilisateur. S'il en manque, laisser un bloc « À remplacer » et l'ajouter à la liste des pièces à fournir.

## Avant de commencer

- Les skills HyperFrames doivent être disponibles dans le projet. Sinon, le dire à l'utilisateur ; ne pas les installer d'office.
- Les règles techniques de HyperFrames (lint, déterminisme, sous-compositions) restent obligatoires. Ses habitudes de style (rebonds, lueurs, sous-titres par défaut) ne s'appliquent que si la fiche les demande.

## Deux façons de travailler

| Mode | Entrée | Sortie |
|---|---|---|
| **Montage complet** | Les rushs bruts. | La vidéo finie. |
| **Animations seules** | Une vidéo déjà coupée ailleurs. | Un clip par scène animée, et la liste des endroits où les poser. |

## Étape 1 : dérush

Lister les rushs, les transcrire, garder la dernière prise complète de chaque phrase, retirer faux départs et hésitations, couper les silences au-delà de ce que la fiche tolère (section 6). Assembler en un seul fichier de voix.

## Étape 2 : transcription en temps de montage

Transcrire le fichier de voix assemblé, mot à mot. Tous les temps d'animation en sortent. Regrouper les mots en phrases.

## Étape 3 : le plan

1. Classer chaque phrase avec le tableau de décision de la fiche (section 3) : poser les questions dans l'ordre, s'arrêter au premier « oui », noter le numéro.
2. Appliquer les arbitrages et le rythme de la même section.
3. Choisir un modèle du gabarit pour chaque scène animée.
4. Écrire `storyboard.json`, au format de `gabarit/storyboard.exemple.json`.
5. Contrôler :

```bash
node <DOSSIER_DU_SKILL>/scripts/controle-plan.mjs storyboard.json
```

Corriger tant qu'une ligne affiche « À REVOIR », ou expliquer pourquoi on la laisse.

## Étape 4 : validation

Seul arrêt obligatoire avant la construction. Montrer : le résultat du contrôle, le nombre de scènes, les pièces à fournir, et les trois décisions les moins évidentes avec leur raison.

## Étape 5 : construction

Copier `gabarit/` dans le projet et suivre `gabarit/README.md` : une copie de modèle par scène, les textes, les pièces, puis les temps.

## Étape 6 : contrôle

1. `node <DOSSIER_DU_SKILL>/scripts/jetons.mjs --verifier <projet>` : le projet doit porter les valeurs de la fiche.
2. `npx hyperframes check --snapshots` jusqu'à « Check passed ».
3. Regarder une image au milieu de chaque scène.
4. Relire « Ce que le style ne fait jamais » (FICHE, section 8), ligne par ligne.

## Étape 7 : rendu

Seulement après l'accord de l'utilisateur.

- Montage complet : `npx hyperframes render -o renders/final.mp4`
- Animations seules : `node <DOSSIER_DU_SKILL>/scripts/exporter-scenes.mjs <projet>`

## Limites

- Le style vient d'une seule vidéo. Chaque règle de la fiche porte son niveau de preuve : s'y fier en conséquence.
- {{limites propres à ce style}}
