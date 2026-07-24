const fs = require("fs");
const code = fs.readFileSync("fc26_fsu_mod/【FSU】EAFC FUT WEB 增强器-26.09.yyh.js", "utf-8");
const lines = code.split("\n");

// The problem is an extra { somewhere. Let's find it by tracking depth
// and finding where depth doesn't return to normal after a block.

let depth = 0;
let extraCandidates = [];
let lastHighDepth = 0;
let lastHighDepthLine = 0;

for (let i = 0; i < lines.length; i++) {
  const line = lines[i];
  const prevDepth = depth;

  for (const ch of line) {
    if (ch === "{") depth++;
    if (ch === "}") depth--;
  }

  // If a line has { but } never comes back to balance...
  // Track lines where depth increases and stays high

  if (depth > lastHighDepth + 3) {
    lastHighDepth = depth;
    lastHighDepthLine = i;
  }
}

// Find lines near the end of the file where depth is high
console.log("Final depth:", depth);
console.log("Total lines:", lines.length);

// Show depth for each line in the last 100 lines
console.log("\nLast 100 lines depth:");
for (let i = Math.max(0, lines.length - 100); i < lines.length; i++) {
  let lineDepth = depth;
  // Recalculate from just this line
  for (const ch of lines[i]) {
    if (ch === "{") depth++;
    if (ch === "}") depth--;
  }
  if (lines[i].includes("}") || lines[i].includes("{")) {
    console.log((i+1) + ": " + lines[i].trim().substring(0, 60));
  }
}

// Actually let me find ALL closing braces that are at "unusual" levels
// Create a balanced-ness map
const braceMap = [];
depth = 0;
for (let i = 0; i < lines.length; i++) {
  const prevD = depth;
  for (const ch of lines[i]) {
    if (ch === "{") depth++;
    if (ch === "}") depth--;
  }
  braceMap.push({ line: i+1, text: lines[i], startD: prevD, endD: depth });
}

// Find closing braces that drop to a lower depth than surrounding
// This might indicate an extra closing brace
let anomalies = [];
for (let i = 1; i < braceMap.length; i++) {
  const curr = braceMap[i];
  // Check for } that brings depth way down
  if (curr.startD - curr.endD > 3) {
    anomalies.push(curr);
  }
}

if (anomalies.length === 0) {
  console.log("\nNo large depth drops found");
}

// Instead, let me look for unmatched braces by section
// by checking each section's net depth change
function sectionNet(startLine, endLine) {
  let d = 0;
  for (let i = 0; i < endLine; i++) {
    if (i < startLine - 1) {
      for (const ch of lines[i]) {
        if (ch === "{") d++;
        if (ch === "}") d--;
      }
    }
  }
  const endD = d;
  d = 0;
  for (let i = 0; i < startLine - 1; i++) {
    for (const ch of lines[i]) {
      if (ch === "{") d++;
      if (ch === "}") d--;
    }
  }
  return { start: d, end: endD, delta: endD - d };
}

// Check key ranges
const ranges = [
  [3576, 3645, "Sec1"],
  [5354, 5423, "Sec2"],
  [5590, 5658, "Sec3"],
  [14198, 14270, "Sec4"],
];

let totalDelta = 0;
for (const [start, end, name] of ranges) {
  const {delta} = sectionNet(start, end);
  totalDelta += delta;
  console.log(`${name} L${start}-${end}: delta=${delta}`);
}
console.log("Total delta from all sections:", totalDelta);

// Now check range between sections
const allRanges = [
  [45, 3575, "IIFE_start-sec1"],
  [3576, 3645, "Sec1"],
  [3646, 5353, "sec1-sec2"],
  [5354, 5423, "Sec2"],
  [5424, 5589, "sec2-sec3"],
  [5590, 5658, "Sec3"],
  [5659, 14197, "sec3-sec4"],
  [14198, 14270, "Sec4"],
  [14271, lines.length, "sec4-end"],
];

for (const [start, end, name] of allRanges) {
  const d1 = sectionNet(lines.length+1, start); // depth BEFORE start
  const d2 = sectionNet(lines.length+1, end+1); // depth AFTER end
  // Hmm this won't work right. Let me use a different approach.
}

// Simpler: track depth at each range boundary
console.log("\nDepth at range boundaries:");
depth = 0;
for (let i = 0; i < lines.length; i++) {
  for (const ch of lines[i]) {
    if (ch === "{") depth++;
    if (ch === "}") depth--;
  }

  const markLines = [45, 3575, 3645, 5353, 5423, 5589, 5658, 14197, 14270, lines.length];
  if (markLines.includes(i+1)) {
    console.log(`Line ${i+1}: depth=${depth}`);
  }
}
