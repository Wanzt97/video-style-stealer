# Gabarit {{nom-du-style}} pour HyperFrames

Un projet HyperFrames prêt à copier. Il applique [la fiche](../FICHE.md) : on ne règle ici aucune durée ni aucune courbe, on pose du contenu et des temps.

**La fiche fait foi.** Si une règle change : corriger la fiche, puis `node ../scripts/jetons.mjs`.

## Ce qu'il y a dedans

| Pièce | Rôle |
|---|---|
| `index.html` | La démonstration : toutes les scènes, comme dans un vrai montage. |
| `compositions/` | Un modèle par type de scène. On les copie, on ne les modifie pas. |
| `lib/jetons.js` | Les valeurs de la fiche. Fabriqué par `scripts/jetons.mjs`, jamais à la main. |
| `lib/moteur.js` | Les gestes du style. Il lit `jetons.js`. |
| `lib/habillage.css` | Couleurs, polices, composition. Le bloc du haut se remplace pour changer de marque. |
| `storyboard.exemple.json` | Le format du plan de montage. |

## Les modèles

| Modèle | Types de scène couverts | Décision de la fiche |
|---|---|---|
| {{modèle}} | {{types}} | {{n° …}} |

## Monter une vidéo avec le gabarit

{{les étapes, dans l'ordre : copier, remplacer la voix, une copie de modèle par scène, textes et pièces, temps}}

## Ce que le moteur sait faire

| Fonction | Effet |
|---|---|
| {{fonction}} | {{effet, et la règle de la fiche qu'elle applique}} |
