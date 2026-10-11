# La méthode, et pourquoi elle est faite ainsi

## L'idée

Un style de montage tient en quatre questions :

1. **Quand** quitte-t-on le visage pour une animation, et quand y revient-on ?
2. **Comment** les choses bougent-elles (durées, courbes, caméra) ?
3. **À quel rythme** (parts du temps, longueur des blocs, fréquence des animations) ?
4. **Avec quelle peau** (couleurs, polices, textures) ?

Les questions 2, 3 et 4 se mesurent. La question 1 se compte, phrase par phrase. Ce qui ne se mesure ni ne se compte se lit sur des planches et s'écrit comme une lecture.

## Qui fait quoi

| Tâche | Le script | L'agent |
|---|---|---|
| Trouver les coupes | oui | vérifie les coupes sautées |
| Dire ce qu'on voit dans un plan | propose (visage ou non) | décide, sur planche |
| Repérer les animations | oui | nomme chaque geste |
| Durée d'un vol de caméra, courbe | oui | retient les mesures fiables |
| Couleurs | propose | vérifie sur une vraie image |
| Nature d'une phrase | non | décide, sans regarder l'image |
| Règle de décision | compte | formule, puis lit les exceptions |
| Fiche | non | écrit, chiffre par chiffre |

## Les niveaux de preuve

| Niveau | Ce que ça veut dire | Exemple |
|---|---|---|
| **Mesuré** | Calculé sur les images ou le son, avec le nombre de cas. | « Vol de caméra : 1 240 ms (médiane de 66 vols). » |
| **Compté** | Tant de cas pour, tant contre. | « Un fait chiffré part en animation : 29 cas sur 31. » |
| **Lu** | Vu sur les planches, sans décompte. | « Les éléments ne sortent jamais par une animation. » |
| **Choix** | Rien dans la vidéo ne tranche : on décide, et on le dit. | « Polices de remplacement. » |

Une fiche honnête contient les quatre. Une fiche où tout est « Mesuré » est une fiche qui ment.

## Les erreurs déjà commises, à ne pas refaire

**Se fier aux sous-titres automatiques.** Leurs temps décalent d'une demi-seconde. Sur la vidéo qui a servi à mettre la méthode au point, ils donnaient une règle fausse (« après *sauf que*, jamais de visage ») que la transcription mot à mot a démentie. D'où `transcrire.py`.

**Lire le traitement d'une phrase à son premier instant.** Une coupe tombe souvent 0,2 s après le premier mot. Le traitement se lit à la majorité sur les 1,2 premières secondes de la phrase : c'est ce que fait `phrases`.

**Trois valeurs pour la même couleur.** Mesurée sur une image compressée, sur un bord de lettre ou sur un aplat, la même couleur ne donne pas le même code. On mesure sur les aplats, en pleine définition, et on écrit le nombre de pixels.

**Deux documents qui se contredisent.** Dès qu'une valeur est écrite à deux endroits, elle finit par différer. D'où un seul bloc de valeurs dans la fiche, et `jetons.mjs` qui le recopie dans le gabarit.

**Demander à un modèle de « regarder la vidéo et décrire le style ».** Le résultat a la forme d'une analyse et le contenu d'une généralité : pourcentages ronds, « punch-in toutes les 4 secondes », écran de fin, bruitages, tout ce qu'on attend d'une vidéo du genre et que la vidéo ne contient pas forcément. Un tel retour ne vaut que comme liste de sujets de scène, à vérifier. Aucun de ses chiffres n'entre dans la fiche.

**Un mot ne fait pas une règle.** « Les mots de liaison ramènent au visage » était vrai 27 fois sur 52 : une pièce lancée en l'air. Sans le compte, la règle serait partie dans la fiche.

**Une statistique tronquée.** Un filtre posé en amont (« seulement les animations de 8 images au plus ») change le sens du chiffre en aval. Quand un chiffre surprend, relire comment il est obtenu.

**Confondre le style et le sujet.** Une vidéo sur un logiciel montre des interfaces. Ce n'est pas le style, c'est le sujet. La liste des types de scène doit dire la fonction (« pièce à conviction »), pas le contenu (« capture du site X »).

## Ce qu'une seule vidéo permet, et ne permet pas

Elle permet de mesurer précisément le mouvement, le rythme et la peau, parce qu'une vidéo de dix minutes contient des centaines d'animations.

Elle permet moins bien de dire ce qui est une habitude de l'auteur et ce qui est un accident de cette vidéo-là. Les règles de décision reposent sur 150 à 250 phrases : assez pour les règles fortes, pas pour les cas rares.

La fiche le dit dans sa section « Ce qui reste incertain ». Ne jamais gommer cette section pour faire propre.

## Le droit

Un style de montage n'est pas protégé : rythme, types de plans, durées, courbes. Ce qui l'est : les images, la musique, les logos, les polices sous licence, le texte. Le paquet final ne contient donc aucun extrait de la vidéo d'origine, et l'habillage de référence propose des polices libres qui jouent le même rôle, pas les polices de l'auteur.

Le téléchargement d'une vidéo depuis une plateforme reste sous la responsabilité de l'utilisateur. Le dossier `analyse/` est un dossier de travail : il ne se publie pas et ne part pas dans le zip.
