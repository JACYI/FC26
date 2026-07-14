const fs = require('fs');
const code = fs.readFileSync('fc26_fsu_mod/【FSU】EAFC FUT WEB 增强器-26.09.yyh.js', 'utf-8');

// Split into lines for easier reference
const lines = code.split('\n');

// Find the line where "Unexpected token 'else'" is
// Try parsing with acorn for better error location
try {
    require('acorn').parse(code, { ecmaVersion: 2020 });
    console.log("No syntax error");
} catch(e) {
    console.log("Error:", e.message);
    if (e.loc) {
        console.log("Line:", e.loc.line, "Column:", e.loc.column);
        // Show surrounding lines
        const start = Math.max(0, e.loc.line - 5);
        const end = Math.min(lines.length, e.loc.line + 3);
        for (let i = start; i < end; i++) {
            const marker = (i === e.loc.line - 1) ? '>>>' : '   ';
            console.log(marker + ' ' + (i + 1) + ': ' + lines[i]);
        }
    }
}
