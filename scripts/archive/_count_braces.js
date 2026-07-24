const fs = require("fs");
const code = fs.readFileSync("fc26_fsu_mod/【FSU】EAFC FUT WEB 增强器-26.09.yyh.js", "utf-8");

// Count braces, string-aware
function countBraces(str) {
  let depth = 0;
  let inStr = false;
  let strChar = null;
  let inTmpl = false;

  for (let i = 0; i < str.length; i++) {
    const ch = str[i];
    const next = str[i+1] || "";

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
    if (ch === "/" && next === "/") {
      while (i < str.length && str[i] !== "\n") i++;
      continue;
    }
    if (ch === "/" && next === "*") {
      i += 2;
      while (i < str.length && !(str[i] === "*" && str[i+1] === "/")) i++;
      i++;
      continue;
    }
    if (ch === '"' || ch === "'") { inStr = true; strChar = ch; continue; }
    if (ch === "`") { inTmpl = true; continue; }
    if (ch === "{") depth++;
    if (ch === "}") depth--;
  }
  return depth;
}

console.log("Full file:", countBraces(code));

// Just IIFE body
const iifeStart = code.indexOf("(function");
const iifeBody = code.slice(iifeStart);
console.log("IIFE body:", countBraces(iifeBody));

// Also count without the IIFE wrapper
const functionMatch = code.match(/\(function\s*\(\)\s*\{/);
if (functionMatch) {
  const bodyStart = functionMatch.index + functionMatch[0].length;
  // Find the closing })(); or })();
  // Simple approach: try to find it
  console.log("IIFE function body start:", bodyStart);
}
