/**
 * EA FC 26 SBC Daily Task Automation — Index
 *
 * src/           — Reusable library modules
 * src/sbc/       — SBC automation modules
 * scripts/       — Runnable automation scripts
 * data/          — Cached data (players, etc.)
 *
 * Usage:
 *   cd D:\Workspace\FC26
 *   python scripts/<name>.py
 */

const scripts = [
  { name: "daily_sbc", file: "scripts/daily_sbc.py", desc: "Main entry: run all repeatable SBCs daily" },
  { name: "login", file: "scripts/login.py", desc: "Launch Chrome (if not running) and log into EA FC 26 Web App" },
  { name: "set_language", file: "scripts/set_language.py", desc: "Switch Web App language to Simplified Chinese" },
  { name: "switch_lang", file: "scripts/switch_lang.py", desc: "Toggle language. Usage: python scripts/switch_lang.py <English|简体中文>" },
  { name: "explore_app", file: "scripts/explore_app.py", desc: "Read-only exploration of SBC, Club, Transfers pages" },
  { name: "explore_sbc_tabs", file: "scripts/explore_sbc_tabs.py", desc: "Read-only SBC sub-tab exploration" },
];

const modules = [
  { name: "utils", file: "src/utils.py", desc: "CDP connection, page state detection, navigation helpers" },
  { name: "models", file: "src/sbc/models.py", desc: "Data models: Player, SBC, Requirement, SquadSlot" },
  { name: "scanner", file: "src/sbc/scanner.py", desc: "Scan SBC page → parse requirements → list available SBCs" },
  { name: "club", file: "src/sbc/club.py", desc: "Scan Club > Players → filter by OVR/position/league/nation/rarity" },
  { name: "builder", file: "src/sbc/builder.py", desc: "Squad building algorithm (constraint satisfaction, FSU fallback)" },
  { name: "executor", file: "src/sbc/executor.py", desc: "State-aware flow orchestration: check→recover→act→verify" },
];

module.exports = { scripts, modules };
