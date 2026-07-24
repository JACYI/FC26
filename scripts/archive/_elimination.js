const fs = require("fs");
const { execSync } = require("child_process");
const path = require("path");

const ORIG = path.join(__dirname, "..", "fc26_fsu_mod", "【FSU】EAFC FUT WEB 增强器-26.09.yyh.js");
const code = fs.readFileSync(ORIG, "utf-8");
const lines = code.split("\n");

function checkSyntax(content) {
  const tmpfile = path.join(__dirname, "_temp_test.js");
  fs.writeFileSync(tmpfile, content, "utf-8");
  try {
    execSync('node --check "' + tmpfile + '"', {
      encoding: "utf8",
      stdio: "pipe",
      shell: true
    });
    fs.unlinkSync(tmpfile);
    return true;
  } catch(e) {
    const msg = (e.stdout || e.stderr || e.message || "").toString();
    fs.unlinkSync(tmpfile);
    return false;
  }
}

console.log("Current (sec4 fixed):", checkSyntax(code) ? "OK" : "FAIL");

// Test reverting section 3
// Strategy: remove lines 5590-5659 and replace with just //placeholder
// Then add the original pattern at the end
const sec3Simple = [
  '                                //batch btn',
  '                                let batchCount = Math.floor(fastCount / 3);',
  '                                if (batchCount >= 1) {',
  '                                    var _bBtn = events.createButton(',
  '                                        new UTCurrencyButtonControl(),',
  '                                        fy(["fastsbc.batchbtn", batchCount]),',
  '                                        () => {',
  '                                            if (info.base.fastsbctips) {',
  '                                                info.run._lastAction = "batch";',
  '                                                info.run._fastBatchInfo = { total: 3, current: 0 };',
  '                                                events.isSBCCache(i._fsu.subSet.setId, sId)',
  '                                            } else {',
  '                                                events.popup(',
  '                                                    fy("fastsbc.popupt"),',
  '                                                    fy("fastsbc.popupm"),',
  '                                                    (t) => {',
  '                                                        if (t === 2) {',
  '                                                            info.base.fastsbctips = true;',
  '                                                            info.run._lastAction = "batch";',
  '                                                            info.run._fastBatchInfo = { total: 3, current: 0 };',
  '                                                            events.isSBCCache(i._fsu.subSet.setId, sId)',
  '                                                        }',
  '                                                    }',
  '                                                )',
  '                                            }',
  '                                        },',
  '                                    "call-to-action mini fsu-challengefastbtn"',
  '                                )',
  '                                _bBtn.getRootElement().style.fontSize = "75%";',
  '                                _bBtn.getRootElement().style.padding = "2px 6px";',
  '                                _bBtn.__currencyLabel.innerHTML = events.getFastSbcSubText(fast)',
  '                                i._fsu.fastBtn.getRootElement().after(_bBtn.getRootElement());',
  '                            }'
];

const test3 = lines.slice();
test3.splice(5589, 5660 - 5589, ...sec3Simple);
console.log("Revert Sec3:", checkSyntax(test3.join("\n")) ? "OK" : "FAIL");

// Test reverting section 1
const sec1Simple = [
  '                            //batch btn',
  '                            let batchCount = Math.floor(qs / 3);',
  '                            if (batchCount >= 1) {',
  '                                var _bBtn = events.createButton(',
  '                                    new UTButtonControl(),',
  '                                    fy(["fastsbc.batchbtn", batchCount]),',
  '                                    () => {',
  '                                        if (info.base.fastsbctips) {',
  '                                            info.run._lastAction = "batch";',
  '                                            info.run._fastBatchInfo = { total: 3, current: 0 };',
  '                                            events.isSBCCache(sId, cId)',
  '                                        } else {',
  '                                            events.popup(',
  '                                                fy("fastsbc.popupt"),',
  '                                                fy("fastsbc.popupm"),',
  '                                                (t) => {',
  '                                                    if (t === 2) {',
  '                                                        info.base.fastsbctips = true;',
  '                                                        info.run._lastAction = "batch";',
  '                                                        info.run._fastBatchInfo = { total: 3, current: 0 };',
  '                                                        events.isSBCCache(sId, cId)',
  '                                                    }',
  '                                                }',
  '                                            )',
  '                                        }',
  '                                    },',
  '                                "call-to-action mini fsu-challengefastbtn"',
  '                            )',
  '                            _bBtn.getRootElement().style.fontSize = "75%";',
  '                            _bBtn.getRootElement().style.padding = "2px 6px";',
  '                            this._fsu.quicklyBtn.getRootElement().after(_bBtn.getRootElement());',
  '                            }'
];

const test1 = lines.slice();
test1.splice(3576 - 1, 3643 - 3576 + 1, ...sec1Simple);
console.log("Revert Sec1:", checkSyntax(test1.join("\n")) ? "OK" : "FAIL");

// Test reverting section 2
const sec2Simple = [
  '                        //batch btn',
  '                        let batchCount = Math.floor(_totalFC / 3);',
  '                        if (batchCount >= 1) {',
  '                            e._fsuBatchBtn = events.createButton(',
  '                                new UTCurrencyButtonControl(),',
  '                                fy(["fastsbc.batchbtn", batchCount]),',
  '                                () => {',
  '                                    if (info.base.fastsbctips) {',
  '                                        info.run._lastAction = "batch";',
  '                                        info.run._fastBatchInfo = { total: 3, current: 0 };',
  '                                        events.isSBCCache(fastSid, fastCid)',
  '                                    } else {',
  '                                        events.popup(',
  '                                            fy("fastsbc.popupt"),',
  '                                            fy("fastsbc.popupm"),',
  '                                            (t) => {',
  '                                                if (t === 2) {',
  '                                                    info.base.fastsbctips = true;',
  '                                                    info.run._lastAction = "batch";',
  '                                                    info.run._fastBatchInfo = { total: 3, current: 0 };',
  '                                                    events.isSBCCache(fastSid, fastCid)',
  '                                                }',
  '                                            }',
  '                                        )',
  '                                    }',
  '                                },',
  '                            "call-to-action mini fsu-challengefastbtn"',
  '                        )',
  '                        e._fsuBatchBtn.getRootElement().style.fontSize = "75%";',
  '                        e._fsuBatchBtn.getRootElement().style.padding = "2px 6px";',
  '                        e._fsuBatchBtn.__currencyLabel.innerHTML = events.getFastSbcSubText(info.base.fastsbc[" + "${fastCid}#${fastSid}" + "])',
  '                        }'
];

// Fix the template literal in sec2
sec2Simple[sec2Simple.length - 2] = '                        e._fsuBatchBtn.__currencyLabel.innerHTML = events.getFastSbcSubText(info.base.fastsbc[`${fastCid}#${fastSid}`])';

const test2 = lines.slice();
test2.splice(5354 - 1, 5423 - 5354 + 1, ...sec2Simple);
console.log("Revert Sec2:", checkSyntax(test2.join("\n")) ? "OK" : "FAIL");
