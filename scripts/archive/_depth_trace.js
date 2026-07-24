const fs = require("fs");
const lines = fs.readFileSync("fc26_fsu_mod/【FSU】EAFC FUT WEB 增强器-26.09.yyh.js", "utf-8").split("\n");

let depth = 0;
let inStr = false, strChar = null, inTmpl = false;

const sectionStarts = [3573, 3644, 5351, 5420, 5587, 5655, 14195, 14268, 16210];

for (let i = 0; i < lines.length; i++) {
  const line = lines[i];
  for (let j = 0; j < line.length; j++) {
    const ch = line[j];
    const next = line[j+1] || "";
    if (inStr) {
      if (ch === "\\" && next) { j++; continue; }
      if (ch === strChar) inStr = false;
      continue;
    }
    if (inTmpl) {
      if (ch === "\\" && next) { j++; continue; }
      if (ch === "`") { inTmpl = false; continue; }
      if (ch === "$" && next === "{") { depth++; j++; continue; }
      continue;
    }
    if (ch === "/" && next === "/") break;
    if (ch === "/" && next === "*") {
      j += 2;
      while (j < line.length && !(line[j] === "*" && line[j+1] === "/")) j++;
      j++;
      continue;
    }
    if (ch === '"' || ch === "'") { inStr = true; strChar = ch; continue; }
    if (ch === "`") { inTmpl = true; continue; }
    if (ch === "{") depth++;
    if (ch === "}") depth--;
  }

  const n = i + 1;
  if (sectionStarts.includes(n)) {
    console.log("Line " + n + ": depth=" + depth);
  }
}

console.log("Final depth:", depth);
