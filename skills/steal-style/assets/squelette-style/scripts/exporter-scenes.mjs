// Mode « animations seules » : rend chaque scène animée en un clip vidéo séparé,
// à poser dans un autre outil de montage, au-dessus de la vidéo déjà coupée.
//   node exporter-scenes.mjs <dossier-du-projet> [storyboard.json] [--seulement s03,s07] [--sans-rendu]
// Sortie : <projet>/renders/scenes/<id>_<timecode>.mp4 et placement.csv (où poser chaque clip).
// HyperFrames : `npx hyperframes` par défaut ; un autre exécutable se donne par la variable HYPERFRAMES.
import { readFileSync, writeFileSync, mkdirSync, rmSync, readdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join, resolve } from "node:path";

const args = process.argv.slice(2);
const options = args.filter((a) => a.startsWith("--"));
const libres = args.filter((a, i) => !a.startsWith("--") && !(args[i - 1] === "--seulement"));
const projet = resolve(libres[0] || ".");
const storyboard = resolve(libres[1] || join(projet, "storyboard.json"));
const filtre = args.includes("--seulement") ? args[args.indexOf("--seulement") + 1].split(",") : null;
const sansRendu = options.includes("--sans-rendu");
const [bin, ...binArgs] = (process.env.HYPERFRAMES || "npx hyperframes").split(" ");

const plan = JSON.parse(readFileSync(storyboard, "utf8"));
const [largeur, hauteur] = [plan.largeur || 1920, plan.hauteur || 1080];
const animations = plan.scenes.filter((s) => s.type === "animation" && (!filtre || filtre.includes(s.id)));
const timecode = (t) => {
  const m = Math.floor(t / 60), sec = t - m * 60;
  return `${String(m).padStart(2, "0")}m${sec.toFixed(2).padStart(5, "0").replace(".", "s")}`;
};
// Le moteur et l'habillage du projet : jetons.js d'abord, puis les autres fichiers de lib/.
const lib = readdirSync(join(projet, "lib")).sort((a, b) => (b === "jetons.js") - (a === "jetons.js") || a.localeCompare(b));
const scripts = lib.filter((f) => f.endsWith(".js")).map((f) => `    <script src="lib/${f}"></script>`).join("\n");
const styles = lib.filter((f) => f.endsWith(".css")).map((f) => `    <link rel="stylesheet" href="lib/${f}" />`).join("\n");

mkdirSync(join(projet, "renders", "scenes"), { recursive: true });
const lignes = ["clip,debut_s,debut,duree_s"];
let echecs = 0;

for (const scene of animations) {
  const source = readFileSync(join(projet, scene.fichier), "utf8");
  const id = source.match(/data-composition-id="([^"]+)"/)[1];
  const duree = +(scene.end - scene.start).toFixed(3);
  const racine = `export-${scene.id}`;
  const page = `<!doctype html>
<html>
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=${largeur}, height=${hauteur}" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
${scripts}
${styles}
    <style>
      body { margin: 0; background: #000; }
      #root { position: relative; width: 100%; height: 100%; overflow: hidden; }
      .scene { position: absolute; inset: 0; }
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="${racine}" data-start="0" data-width="${largeur}" data-height="${hauteur}" data-duration="${duree}">
      <div class="scene" data-composition-id="${id}" data-composition-src="${scene.fichier}"
           data-start="0" data-duration="${duree}" data-track-index="1" data-width="${largeur}" data-height="${hauteur}"></div>
    </div>
    <script>
      window.__timelines["${racine}"] = gsap.timeline({ paused: true });
    </script>
  </body>
</html>
`;
  const fichierRacine = join(projet, `${racine}.html`);
  const clip = `${scene.id}_${timecode(scene.start)}.mp4`;
  writeFileSync(fichierRacine, page);
  lignes.push(`${clip},${scene.start},${timecode(scene.start)},${duree}`);
  if (sansRendu) continue;

  console.log(`→ ${clip} (${duree} s)`);
  const r = spawnSync(bin, [...binArgs, "render", "-c", `${racine}.html`, "-o", join("renders", "scenes", clip), "--fps", "30", "--quiet"],
    { cwd: projet, stdio: "inherit" });
  if (r.status !== 0) { echecs++; console.error(`  échec du rendu de ${scene.id}`); }
  rmSync(fichierRacine);
}

writeFileSync(join(projet, "renders", "scenes", "placement.csv"), lignes.join("\n") + "\n");
console.log(`\n${animations.length} scène(s). Où poser chaque clip : renders/scenes/placement.csv`);
process.exit(echecs ? 1 : 0);
