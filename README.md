# video-style-stealer

Donne un lien de vidéo. Repars avec son style de montage, prêt à réutiliser.

Un skill pour Claude Code, Codex et les agents qui lisent les skills. Il regarde une vidéo de référence, mesure comment elle est montée, et fabrique un **design system vidéo** :

| Pièce | À quoi elle sert |
|---|---|
| **La fiche** | Les règles du style : quand on passe du visage à l'animation, comment les choses bougent, à quel rythme, ce qu'on ne fait jamais. Chaque règle dit sur quoi elle s'appuie. |
| **L'habillage** | Couleurs, polices, matières. Se remplace par ta marque sans toucher aux règles. |
| **Le gabarit** | Un projet [HyperFrames](https://github.com/heygen-com/hyperframes) avec un modèle par type de scène. |
| **Le skill du style** | Ce que tu installes ensuite pour dire « monte mes rushs dans ce style ». |

On copie une façon de monter. Pas les images, pas la musique, pas les logos de la vidéo d'origine.

## Installer

Il faut [`uv`](https://docs.astral.sh/uv/) et `ffmpeg`. Sur macOS :

```bash
brew install uv ffmpeg
```

Pour savoir si tout est en place, une fois l'outil récupéré :

```bash
uv run skills/steal-style/scripts/analyse.py verifier
```

Le gabarit demande en plus Node.js 22 ou plus. Sans lui, l'outil s'arrête à la fiche.

**Claude Code**

```
/plugin marketplace add Wanzt97/video-style-stealer
/plugin install video-style-stealer@wanzt
```

**Codex**

```bash
git clone https://github.com/Wanzt97/video-style-stealer
bash video-style-stealer/install.sh codex
```

**Autre agent** : `bash install.sh <dossier-des-skills>`.

## Utiliser

Dans une nouvelle session, dans le dossier où tu veux ranger le style :

```
Vole le style de cette vidéo : https://youtu.be/…
```

L'agent te demande un nom pour le style et ton outil de montage, puis :

1. télécharge la vidéo et la découpe en plans ;
2. regarde chaque plan et chaque animation sur des planches d'images ;
3. transcrit la voix mot à mot et croise chaque phrase avec ce qui est à l'écran ;
4. mesure les durées, les courbes, les couleurs, le rythme ;
5. écrit la fiche et te la montre ;
6. construit le gabarit et te le montre ;
7. fabrique un zip à installer.

Compte 5 à 10 minutes de calcul pour une vidéo de 15 minutes, plus le temps de lecture de l'agent. Le premier lancement télécharge un modèle de transcription de 500 Mo.

## Ce que ça mesure vraiment

| Mesuré par le programme | Lu par l'agent sur des images | Pas mesuré |
|---|---|---|
| Coupes, durée des plans | Ce qu'on voit dans chaque plan | Le nom des bruitages |
| Part du visage, de l'animation, des extraits | Le nom de chaque geste d'animation | La musique |
| Durée et courbe des mouvements de caméra | Ce que le style refuse de faire | Les polices exactes |
| Durée des fondus, rythme des animations | La nature de chaque phrase | L'intention de l'auteur |
| Couleurs de fond et d'accent | | |
| Débit et silences de la voix | | |

Dans la fiche, chaque règle porte une de ces quatre mentions : **Mesuré**, **Compté**, **Lu** ou **Choix**. Tu sais toujours à quoi te fier.

## Limites

- Une seule vidéo dit comment *cette* vidéo est montée. Pour séparer le style de l'auteur du sujet de la vidéo, il en faudrait deux.
- Pensé pour les vidéos où quelqu'un parle (face caméra, voix off) avec du motion design. Un clip musical ou un film sans parole donnera une fiche pauvre.
- Le gabarit vise HyperFrames. Pour un autre logiciel de montage, le skill livre la fiche et peut rendre les scènes animées en clips à poser dessus.
- La détection de visage, les coupes sautées et le zoom lent du visage sont des propositions : l'agent les vérifie à l'œil.

## Sans agent

Les mesures marchent seules :

```bash
uv run skills/steal-style/scripts/analyse.py recuperer "https://youtu.be/…" mon-style
uv run skills/steal-style/scripts/analyse.py plans mon-style
uv run skills/steal-style/scripts/analyse.py --help
```

## Droit

Un style de montage n'est pas protégé. Les images, la musique, les logos et les polices le sont. Le dossier `analyse/`, qui contient la vidéo téléchargée, reste chez toi : il ne part jamais dans le zip. Le téléchargement d'une vidéo depuis une plateforme relève de ta responsabilité.

## Licence

MIT.
