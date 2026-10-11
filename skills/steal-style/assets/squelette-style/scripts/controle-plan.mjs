// Calcule le rythme d'un plan de montage et le compare aux tolérances de la fiche (bloc « controle »).
// À lancer après le plan, puis après toute retouche.
//   node scripts/controle-plan.mjs chemin/vers/storyboard.json
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { valeursDeLaFiche } from "./jetons.mjs";

const chemin = process.argv[2];
if (!chemin) {
  console.error("Usage : node controle-plan.mjs chemin/vers/storyboard.json");
  process.exit(2);
}
const style = fileURLToPath(new URL("..", import.meta.url));
const tol = valeursDeLaFiche().controle || {};
const { scenes } = JSON.parse(readFileSync(chemin, "utf8"));

const duree = (s) => s.end - s.start;
const total = Math.max(...scenes.map((s) => s.end));
const visages = scenes.filter((s) => s.type === "visage").sort((a, b) => a.start - b.start);
const animations = scenes.filter((s) => s.type === "animation");
const somme = (l) => l.reduce((n, s) => n + duree(s), 0);
const mediane = (l) => { const t = [...l].sort((a, b) => a - b); return t.length ? t[Math.floor(t.length / 2)] : 0; };

// Plus longue période sans visage, début et fin de vidéo compris.
let absence = 0, fin = 0;
for (const v of visages) { absence = Math.max(absence, v.start - fin); fin = Math.max(fin, v.end); }
absence = Math.max(absence, total - fin);

const beats = animations.reduce((n, s) => n + (s.beats ? s.beats.length : 0), 0);
const pourcent = (v) => `${Math.round(v * 100)} %`;
const secondes = (v) => `${v.toFixed(1)} s`;
const plage = (t) => (Array.isArray(t) ? t : [0, t]);
const lignes = [
  ["Part du visage", somme(visages) / total, tol.part_visage, pourcent],
  ["Part de l'animation", somme(animations) / total, tol.part_animation, pourcent],
  ["Plus longue absence du visage", absence, tol.absence_visage_max_s, secondes],
  ["Durée médiane d'un bloc visage", mediane(visages.map(duree)), tol.bloc_visage_median_s, secondes],
  ["Une animation toutes les", beats ? somme(animations) / beats : Infinity, tol.intervalle_entre_animations_s, secondes],
].filter(([, , t]) => t !== undefined); // une tolérance absente de la fiche n'est pas contrôlée

let ecarts = 0;
console.log(`${scenes.length} scènes, ${total.toFixed(1)} s, ${visages.length} blocs visage, ${beats} animations\n`);
for (const [nom, valeur, t, ecrire] of lignes) {
  const [bas, haut] = plage(t);
  const ok = valeur >= bas && valeur <= haut;
  if (!ok) ecarts++;
  console.log(`${ok ? "OK      " : "À REVOIR"}  ${nom.padEnd(32)} ${ecrire(valeur).padStart(8)}   (attendu : ${ecrire(bas)} à ${ecrire(haut)})`);
}

// La liste des scènes est fermée : ce sont les modèles du gabarit.
const dossier = join(style, "gabarit", "compositions");
if (existsSync(dossier)) {
  const modeles = readdirSync(dossier).filter((f) => f.endsWith(".html")).map((f) => f.replace(/\.html$/, ""));
  const inconnus = animations.filter((s) => !modeles.includes(s.modele));
  if (inconnus.length) {
    ecarts++;
    console.log(`\nÀ REVOIR  Scènes sans modèle du gabarit : ${inconnus.map((s) => s.id).join(", ")}`);
  }
}
process.exit(ecarts ? 1 : 0);
