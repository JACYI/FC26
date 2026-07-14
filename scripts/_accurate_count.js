const fs = require("fs");

function countBracesAccurate(code) {
  let depth = 0;
  let inStr = false, strChar = null, inTmpl = false;
  let inLineComment = false, inBlockComment = false;

  for (let i = 0; i < code.length; i++) {
    const ch = code[i];
    const next = code[i + 1] || "";

    if (inLineComment) {
      if (ch === "\n") inLineComment = false;
      continue;
    }
    if (inBlockComment) {
      if (ch === "*" && next === "/") { inBlockComment = false; i++; }
      continue;
    }
    if (inStr) {
      if (ch === "\\" && next) { i++; continue; }
      if (ch === strChar) inStr = false;
      continue;
    }
    if (inTmpl) {
      if (ch === "\\" && next) { i++; continue; }
      if (ch === "`") { inTmpl = false; continue; }
      if (ch === "$" && next === "{") { depth++; i++; continue; }
      continue;
    }

    if (ch === "/" && next === "/") { inLineComment = true; i++; continue; }
    if (ch === "/" && next === "*") { inBlockComment = true; i++; continue; }
    if (ch === '"' || ch === "'") { inStr = true; strChar = ch; continue; }
    if (ch === "`") { inTmpl = true; continue; }
    if (ch === "{") depth++;
    if (ch === "}") depth--;
  }
  return depth;
}

// Check current file
const current = fs.readFileSync("fc26_fsu_mod/【FSU】EAFC FUT WEB 增强器-26.09.yyh.js", "utf-8");
const iifeStart = current.indexOf("(function");
const iife = current.slice(iifeStart);

console.log("Current IIFE body (accurate):", countBracesAccurate(iife));

// Check original via git
const { execSync } = require("child_process");
try {
  const orig = execSync("git show fac9dd2:fc26_fsu_mod/【FSU】EAFC FUT WEB 增强器-26.09.yyh.js", { encoding: "utf-8" });
  const origIifeStart = orig.indexOf("(function");
  const origIife = orig.slice(origIifeStart);
  console.log("fac9dd2 IIFE body (accurate):", countBracesAccurate(origIife));
} catch(e) {
  console.log("Could not check original:", e.message);
}
