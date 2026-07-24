/**
 * EA FC 26 SBC Daily Task Automation — Index
 *
 * src/           — Reusable library modules
 * src/sbc/       — SBC automation modules
 * scripts/       — Runnable automation scripts
 * scripts/archive/ — Historical/debug scripts (not actively maintained)
 * data/          — Cached data (players, etc.)
 * fc26_fsu_mod/  — FSU plugin mod files
 *
 * Usage:
 *   cd D:\Workspace\FC26
 *   python scripts/<name>.py
 */

const scripts = [
  // ── Main daily tasks ──
  { name: "daily_sbc", file: "scripts/daily_sbc.py", desc: "Run all repeatable SBCs daily (main entry)" },
  { name: "bsg_upgrade", file: "scripts/bsg_upgrade.py", desc: "Bronze/Silver/Gold Upgrade daily (3 tiers)" },
  { name: "bsg_cdp", file: "scripts/bsg_cdp.py", desc: "Bronze & Silver via state machine OODA loop" },

  // ── Login & navigation ──
  { name: "login", file: "scripts/login.py", desc: "Launch Chrome (if not running) and log into EA FC 26 Web App" },
  { name: "set_language", file: "scripts/set_language.py", desc: "Switch Web App language to Simplified Chinese" },
  { name: "switch_lang", file: "scripts/switch_lang.py", desc: "Toggle language. Usage: python scripts/switch_lang.py <English|简体中文>" },

  // ── Status checks ──
  { name: "check_daily_status", file: "scripts/check_daily_status.py", desc: "Check daily SBC status with PageMachine login → report file" },
  { name: "check_sbc_status", file: "scripts/check_sbc_status.py", desc: "Quick read-only SBC status check (logged in assumed)" },
  { name: "check_sbc", file: "scripts/check_sbc.py", desc: "Login (inline) + scan all Upgrades SBCs" },
  { name: "check_sbc_rareflags", file: "scripts/check_sbc_rareflags.py", desc: "Read SBC requirements to determine rareflag values" },
  { name: "check_state", file: "scripts/check_state.py", desc: "Quick page state detection via CDP shell" },

  // ── Utilities ──
  { name: "explore_app", file: "scripts/explore_app.py", desc: "Read-only exploration of SBC, Club, Transfers pages" },
  { name: "explore_sbc_tabs", file: "scripts/explore_sbc_tabs.py", desc: "Read-only SBC sub-tab exploration" },
  { name: "do_submit", file: "scripts/do_submit.py", desc: "Quick submit + claim on current squad builder page" },
  { name: "cdp_shell", file: "scripts/cdp_shell.py", desc: "Raw CDP WebSocket client (library for check_state)" },
  { name: "check_braces", file: "scripts/check_braces.py", desc: "Check FSU JS brace balance (development tool)" },
];

const modules = [
  { name: "page_machine", file: "src/page_machine.py", desc: "OODA state machine: poll → detect → act → verify" },
  { name: "page_states", file: "src/page_states.py", desc: "9 page state detectors (Loading → LoginPage → ... → LoggedIn)" },
  { name: "utils", file: "src/utils.py", desc: "CDP connection, page state detection, navigation helpers" },
  { name: "login", file: "src/login.py", desc: "Connect, navigate, login, FSU check utilities" },
  { name: "language", file: "src/language.py", desc: "Language detection and switching" },
  { name: "models", file: "src/sbc/models.py", desc: "Data models: Player, SBC, Requirement, SquadSlot" },
  { name: "scanner", file: "src/sbc/scanner.py", desc: "Scan SBC page → parse requirements → list available SBCs" },
  { name: "club", file: "src/sbc/club.py", desc: "Scan Club > Players → filter by OVR/position/league/nation/rarity" },
  { name: "builder", file: "src/sbc/builder.py", desc: "Squad building algorithm (constraint satisfaction, FSU fallback)" },
  { name: "executor", file: "src/sbc/executor.py", desc: "State-aware flow orchestration: check→recover→act→verify" },
  { name: "machine", file: "src/sbc/machine.py", desc: "SBC-specific OODA state machine" },
  { name: "states", file: "src/sbc/states.py", desc: "SBC state definitions" },
  { name: "transitions", file: "src/sbc/transitions.py", desc: "SBC state transitions" },
  { name: "actions", file: "src/sbc/actions.py", desc: "SBC action handlers" },
  { name: "config", file: "src/sbc/config.py", desc: "FSU config management" },
  { name: "logger", file: "src/sbc/logger.py", desc: "SBC-specific logging" },
  { name: "validator", file: "src/sbc/validator.py", desc: "SBC requirement validation" },
];

const archive = [
  "scripts/archive/ — Historical/debug scripts from early development",
  "  _*.py, _*.js — One-off debugging and inspection tools",
  "  bronze_silver_daily.py, bs_only.py, bs_quick.py — Superseded BSG variants",
  "  run_daily.py — Older entry point (superseded by daily_sbc.py)",
  "  test_*.py — One-time test scripts",
  "  full_sbc_vc.py — Debug variant using CDP VC push",
];

module.exports = { scripts, modules, archive };
