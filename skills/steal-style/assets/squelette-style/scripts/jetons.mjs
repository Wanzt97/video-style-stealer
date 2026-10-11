// Les valeurs du style vivent à un seul endroit : le bloc JSON de FICHE.md, section « Les valeurs pour le gabarit ».
//   node scripts/jetons.mjs                      écrit gabarit/lib/jetons.js depuis la fiche
//   node scripts/jetons.mjs --verifier [projet]  vérifie qu'un projet porte bien les valeurs de la fiche
// La fiche fait foi : on ne corrige jamais jetons.js à la main.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const style = fileURLToPath(new URL("..", import.meta.url));
const args = process.argv.slice(2);
const verifier = args.includes("--verifier");
const projet = resolve(args.find((a) => !a.startsWith("--")) || join(style, "gabarit"));

export function valeursDeLaFiche(dossier = style) {
  const fiche = readFileSync(join(dossier, "FICHE.md"), "utf8");
  const titre = fiche.search(/^## .*valeurs pour le gabarit/im);
  const bloc = titre < 0 ? null : fiche.slice(titre).match(/```json\n([\s\S]*?)```/);
  if (!bloc) throw new Error("FICHE.md : section « Les valeurs pour le gabarit » ou son bloc JSON introuvable.");
  return JSON.parse(bloc[1]);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const attendu = valeursDeLaFiche();
  const cible = join(projet, "lib", "jetons.js");
  if (!verifier) {
    mkdirSync(join(projet, "lib"), { recursive: true });
    writeFileSync(cible,
      "// Fabriqué par scripts/jetons.mjs depuis FICHE.md. Ne pas modifier à la main.\n" +
      `window.JETONS = ${JSON.stringify(attendu, null, 2)};\n`);
    console.log(`Écrit : ${cible}`);
  } else {
    const texte = readFileSync(cible, "utf8");
    const reel = JSON.parse(texte.slice(texte.indexOf("{"), texte.lastIndexOf("}") + 1));
    const ecarts = [];
    (function comparer(f, m, chemin) {
      for (const cle of new Set([...Object.keys(f || {}), ...Object.keys(m || {})])) {
        const ou = chemin ? `${chemin}.${cle}` : cle;
        const a = f?.[cle], b = m?.[cle];
        if (a && b && typeof a === "object" && typeof b === "object" && !Array.isArray(a)) comparer(a, b, ou);
        else if (JSON.stringify(a) !== JSON.stringify(b)) ecarts.push(`${ou} : fiche ${JSON.stringify(a)}, projet ${JSON.stringify(b)}`);
      }
    })(attendu, reel, "");
    if (ecarts.length) {
      console.error(`${ecarts.length} écart(s) entre la fiche et ${cible} :\n- ${ecarts.join("\n- ")}\nRelancer : node scripts/jetons.mjs ${args.find((a) => !a.startsWith("--")) || ""}`);
      process.exit(1);
    }
    console.log("Le projet et la fiche disent la même chose.");
  }
}
