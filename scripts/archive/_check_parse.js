const fs = require('fs');
const code = fs.readFileSync('fc26_fsu_mod/【FSU】EAFC FUT WEB 增强器-26.09.yyh.js', 'utf-8');
const lines = code.split('\n');

// Find the IIFE start
let iifeLine = 0;
for (let i = 0; i < lines.length; i++) {
    if (lines[i].includes('(function') && lines[i].includes('{')) {
        iifeLine = i;
        break;
    }
}

if (iifeLine >= 0) {
    // Build a function body from the IIFE (remove the wrapper)
    const body = lines.slice(iifeLine).join('\n');
    // Remove trailing })();
    const trimmed = body.replace(/\}\)\(\);?\s*$/, '');

    // Try locating error by progressively truncating
    let lo = 0, hi = trimmed.length;
    let errPos = 0;

    try {
        new Function(trimmed);
        console.log('Body is valid');
    } catch (e) {
        console.log('Initial error: ' + e.message);

        // Binary search for error location
        while (lo < hi) {
            const mid = Math.floor((lo + hi) / 2);
            try {
                new Function(trimmed.substring(0, mid));
                lo = mid + 1;
            } catch {
                hi = mid;
            }
        }
        errPos = lo;

        // Find line number
        const prefix = trimmed.substring(0, errPos);
        const errLineInBody = prefix.split('\n').length;
        const errLineInFile = errLineInBody + iifeLine;

        console.log('Error at position ' + errPos + ', file line ~' + errLineInFile);

        // Show context
        for (let i = Math.max(0, errLineInFile - 3); i < Math.min(lines.length, errLineInFile + 3); i++) {
            const marker = i === errLineInFile - 1 ? '>>>' : '   ';
            console.log(marker + ' ' + (i+1) + ': ' + lines[i]);
        }
    }
}
