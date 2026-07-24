const fs = require("fs");
const code = fs.readFileSync("fc26_fsu_mod/【FSU】EAFC FUT WEB 增强器-26.09.yyh.js", "utf-8");
const lines = code.split("\n");

// Test each section independently by extracting it and checking brace balance
// Define section boundaries (line numbers, 1-indexed)
const sections = [
  { name: "Sec1", start: 3576, end: 3643 },
  { name: "Sec2", start: 5354, end: 5423 },
  { name: "Sec3", start: 5590, end: 5659 },
  { name: "Sec4", start: 14198, end: 14270 }
];

for (const sec of sections) {
  let open = 0, close = 0;
  for (let i = sec.start - 1; i < Math.min(sec.end, lines.length); i++) {
    for (const ch of lines[i]) {
      if (ch === "{") open++;
      if (ch === "}") close++;
    }
  }
  console.log(`${sec.name}: {: ${open}, }: ${close}, net: ${open - close}`);
}

// Also check specific close braces count at end of each section
console.log("\n--- Detailed closing check ---");
for (const sec of sections) {
  const endLines = lines.slice(sec.end - 5, sec.end);
  let onlyBraces = endLines.filter(l => l.trim().match(/^[}\s]+$/));
  console.log(`${sec.name} closing lines (near ${sec.end}): ${endLines.map(l => l.trim()).filter(l => l === "}" || l.startsWith("}else")).join(", ")}`);
  console.log(`  Final 5 lines braces: ${endLines.map(l => ({b: l.trim(), o: (l.match(/\{/g)||[]).length, c: (l.match(/\}/g)||[]).length}))}`);
}
