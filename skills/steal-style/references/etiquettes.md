# Les fichiers d'étiquettes

Trois fichiers texte, écrits à la main par l'agent, dans `STYLE/analyse/`. La commande `etiqueter` les applique. On peut la relancer autant de fois qu'on veut.

Format commun : une ligne par élément, champs séparés par `|`. Une plage s'écrit `12-15`. Les lignes vides et celles qui commencent par `#` sont ignorées.

## `etiquettes_plans.txt`

```
numéro|famille|sous-type|description|texte à l'écran
```

```
# planche 01
1|visage||Face caméra, plan poitrine, néons en fond|
2|animation|mur de vignettes|Grille d'extraits qui se remplit, les anciens passent en noir et blanc|étiquette mono sous chaque vignette
3|visage||Même cadre|
4|animation|pièce à conviction|Tweet sur fond blanc, incliné, phrase lue surlignée|texte du tweet
5-7|b-roll||Extraits plein cadre, 1 à 2 s chacun|légende de source en bas
```

**Famille** (liste fermée) :

| Famille | Quand |
|---|---|
| `visage` | Une personne parle à la caméra et remplit le cadre. Avec du texte posé dessus : toujours `visage`, sous-type `visage + texte`. |
| `animation` | Tout ce qui est fabriqué : motion design, documents animés, schémas, 3D, extrait posé dans un cadre dessiné. |
| `ecran` | Enregistrement d'écran continu (une démo), sans mise en scène. |
| `b-roll` | Un extrait filmé qui remplit tout le cadre. |
| `autre` | Carton noir, générique, écran de fin. À expliquer dans la description. |

**Sous-type** : libre, mais tenu. Il deviendra la liste des types de scène de la fiche. Nommer la **fonction** (« pièce à conviction », « frise », « texte seul ») et non le contenu (« tweet d'Untel »). Viser 8 à 14 sous-types pour toute la vidéo ; regrouper ceux qui n'apparaissent qu'une fois.

**Description** : ce qu'on voit, en une ligne. **Texte à l'écran** : ce qui est écrit, sa place, son style.

Tous les plans doivent avoir une ligne : la commande refuse sinon.

## `coupes_confirmees.txt`

Les numéros d'image des coupes sautées vérifiées sur les planches `coupes_XX.jpg`, séparés par des espaces ou des retours à la ligne. Le numéro est écrit en haut à gauche de chaque ligne de la planche. La coupe est réelle quand la tête ou les mains changent de place d'un coup entre les images `−1` et `0`, sans que rien d'autre ne change.

## `etiquettes_mouvements.txt`

```
identifiant|type|description
```

```
M017|pliage 3D|un cube se déplie puis se referme
M019-M020|compteur|la date s'écrit par morceaux, de gauche à droite
M022|vol de caméra|glisse de la date vers le document, à droite
M023|apparition|le chiffre héros entre en fondu, en haut à gauche
```

Le **type** nomme le geste. Liste fermée, 15 types au plus, construite en avançant. Des types qu'on retrouve dans beaucoup de styles : `vol de caméra`, `apparition`, `d'un coup`, `texte mot à mot`, `compteur`, `surlignage`, `glissement`, `cascade`, `bascule 3D`, `extinction`, `coupe interne`, `mouvement dans un extrait` (à écarter des statistiques : ce n'est pas une animation du monteur).

Regarder en particulier :
- ce qui **sort** de l'écran, et comment (souvent : rien ne sort, la coupe ou la caméra s'en charge) ;
- ce qui se passe **pendant** qu'un nouvel élément entre (les autres s'éteignent-ils ?) ;
- si la caméra **dérive** entre deux gestes ;
- les **dépassements** et rebonds (présents ou totalement absents : les deux sont une règle).

## `etiquettes_phrases.txt`

```
identifiant|nature
```

```
P001|adresse au public
P002-P004|fait
P005|question
P006|raisonnement
```

La **nature** dit ce que fait la phrase dans le discours, d'après son texte seul. Liste fermée, 8 au plus. Une base qui marche pour une vidéo d'explication :

| Nature | Ce que c'est |
|---|---|
| `fait` | Un chiffre, une date, un nom, un événement, une citation, une source. |
| `exemple` | Un cas concret qui illustre. |
| `raisonnement` | Un lien logique, une déduction, une opinion argumentée. |
| `question` | Une question posée au public ou à soi-même. |
| `transition` | Une phrase qui annonce la suite ou clôt une partie. |
| `avis` | Un jugement, une émotion, une réaction. |
| `adresse au public` | Accroche, appel à s'abonner, remerciement, publicité. |

L'adapter au genre de la vidéo, mais garder la liste fermée et écrire sa définition dans la fiche.

**Ne pas regarder la colonne `a_l_ecran` en étiquetant.** Le test consiste à voir si la nature prédit le traitement : si on regarde la réponse, le test confirme toujours.
