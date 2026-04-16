#!/usr/bin/env python3
"""
UAF CLI — Unified Automation Framework Interactive CLI
Orchestrates Claude Code agents for automated testing pipelines.

Usage:
    python uaf_cli.py
    ./uaf
"""

# ── Dependency bootstrap (must run before other imports) ──────────────────
import subprocess
import sys

def _bootstrap():
    missing = []
    for pkg in ("questionary", "rich"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Installing required packages: {', '.join(missing)} ...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install"] + missing,
            stdout=subprocess.DEVNULL,
        )

_bootstrap()

# ── Standard library ──────────────────────────────────────────────────────
import json
import os
import shutil
import textwrap
from pathlib import Path

# ── Third-party ───────────────────────────────────────────────────────────
import questionary
from questionary import Choice, Separator
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

# ── Constants ─────────────────────────────────────────────────────────────
VERSION = "1.0.0"
PROJECT_DIR = Path(__file__).parent.resolve()
CONFIG_DIR  = Path.home() / ".uaf"
CONFIG_FILE = CONFIG_DIR / "config.json"

console = Console()

# ── Default configuration ─────────────────────────────────────────────────
DEFAULT_CONFIG: dict = {
    "project_dir": str(PROJECT_DIR),
    "crawling": {
        "github_url":      "",
        "swagger_url":     "",
        "confluence_urls": [],
        "output_dir":      str(PROJECT_DIR),
    },
    "app_validation": {
        "app_url":         "",
        "test_email":      "",
        "test_password":   "",
        "playwright_mode": "headed",
        "output_dir":      str(PROJECT_DIR),
    },
    "jira": {
        "site":            "",
        "project_key":     "KAN",
        "spec_md_path":    str(PROJECT_DIR / "spec.md"),
        "app_report_path": str(PROJECT_DIR / "app_validation_report.md"),
    },
    "test_cases": {
        "project_key":           "KAN",
        "story_number":          "",
        "automation_github_url": "",
    },
    "test_validator": {
        "project_key":  "KAN",
        "story_number": "",
    },
}

# ── Config helpers ────────────────────────────────────────────────────────

def load_config() -> dict:
    """Load config from ~/.uaf/config.json, merging with defaults."""
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    with open(CONFIG_FILE) as f:
        stored = json.load(f)
    merged = json.loads(json.dumps(DEFAULT_CONFIG))       # deep copy
    for section, value in stored.items():
        if isinstance(value, dict) and section in merged and isinstance(merged[section], dict):
            merged[section].update(value)
        else:
            merged[section] = value
    return merged


def save_config(cfg: dict) -> None:
    """Persist config and restrict file permissions (credentials stored here)."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except OSError:
        pass  # Windows; skip


# ── Claude subprocess runner ──────────────────────────────────────────────

def _claude_available() -> bool:
    return shutil.which("claude") is not None


def run_claude(prompt: str, agent_label: str) -> int:
    """
    Invoke `claude -p <prompt>` as a subprocess.

    stdin/stdout/stderr are all inherited from this process so that:
    - Agent output streams live to the terminal.
    - HIL checkpoints (where Claude pauses and asks for approval) let the
      user type responses directly without any CLI mediation.

    Returns the process exit code.
    """
    if not _claude_available():
        console.print(
            "[bold red]Error:[/bold red] `claude` CLI not found in PATH.\n"
            "Install Claude Code from https://claude.ai/code and ensure it is in your PATH."
        )
        return 1

    cmd = ["claude", "-p", prompt, "--dangerously-skip-permissions"]

    console.print()
    console.print(Panel(
        f"[bold cyan]Launching:[/bold cyan] {agent_label}\n\n"
        "[dim]Output streams directly below.\n"
        "HIL checkpoints will appear inline — respond when prompted.[/dim]",
        border_style="cyan",
        expand=False,
    ))
    console.print(Rule("[dim]Agent Output[/dim]", style="dim"))

    proc = subprocess.Popen(cmd, cwd=str(PROJECT_DIR))
    try:
        exit_code = proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        proc.wait()
        console.print("\n[yellow]Agent interrupted by user (Ctrl+C).[/yellow]")
        return 130

    console.print(Rule("[dim]End of Agent Output[/dim]", style="dim"))
    console.print()
    if exit_code == 0:
        console.print(Panel(
            f"[bold green]Completed:[/bold green] {agent_label}",
            border_style="green",
            expand=False,
        ))
    else:
        console.print(Panel(
            f"[bold red]Agent exited with code {exit_code}:[/bold red] {agent_label}",
            border_style="red",
            expand=False,
        ))
    return exit_code


# ── Prompt builders ───────────────────────────────────────────────────────

def build_crawling_prompt(cfg: dict) -> str:
    c = cfg["crawling"]
    confluence_section = ""
    if c["confluence_urls"]:
        urls = "\n".join(f"  - {u}" for u in c["confluence_urls"])
        confluence_section = f"\nConfluence documentation URLs:\n{urls}"

    return textwrap.dedent(f"""
        Use the crawling-agent sub-agent to crawl the target application and produce spec.md.

        Runtime inputs (use these — they override any defaults in the agent definition):
        - GitHub repository URL:  {c['github_url']}
        - Swagger / API docs URL: {c['swagger_url']}{confluence_section}
        - Output spec.md to:      {c['output_dir']}/spec.md

        Follow the crawling-agent instructions completely to generate a comprehensive spec.md.
    """).strip()


def build_app_validation_prompt(cfg: dict) -> str:
    a = cfg["app_validation"]
    return textwrap.dedent(f"""
        Use the app-validation-agent sub-agent to validate the live application.

        Runtime inputs (use these — they override any defaults in the agent definition):
        - Live app URL:          {a['app_url']}
        - Test account email:    {a['test_email']}
        - Test account password: {a['test_password']}
        - Playwright mode:       {a['playwright_mode']}
        - Output directory:      {a['output_dir']}
        - Screenshots directory: {a['output_dir']}/screenshots
        - spec.md path:          {cfg['jira']['spec_md_path']}

        Follow the app-validation-agent instructions completely.
        Generate app_validation_report.md with all findings and screenshot references.
    """).strip()


def build_jira_prompt(cfg: dict) -> str:
    j = cfg["jira"]
    return textwrap.dedent(f"""
        Use the jira-agent sub-agent to draft Gherkin acceptance criteria for Jira stories.

        Runtime inputs (use these — they override any defaults in the agent definition):
        - Jira site:                     {j['site']}
        - Jira project key:              {j['project_key']}
        - spec.md path:                  {j['spec_md_path']}
        - app_validation_report.md path: {j['app_report_path']}

        Follow the jira-agent instructions completely, including:
        1. Fetch all Story-type issues from the {j['project_key']} project.
        2. Draft Gherkin Given/When/Then AC for each story.
        3. Present ALL proposed AC to me for review before writing anything to Jira (HIL checkpoint).
        4. Wait for my explicit approval before writing AC to Jira.
        5. Write approved AC to the Jira issue description fields.
    """).strip()


def build_test_cases_prompt(cfg: dict) -> str:
    t = cfg["test_cases"]
    automation_line = ""
    if t["automation_github_url"]:
        automation_line = f"\n- Automation framework GitHub URL: {t['automation_github_url']}"

    return textwrap.dedent(f"""
        Use the test-case-creation-agent sub-agent to generate test cases for a Jira story.

        Runtime inputs (use these — they override any defaults in the agent definition):
        - Jira project key:              {t['project_key']}
        - Story key:                     {t['project_key']}-{t['story_number']}{automation_line}
        - spec.md path:                  {cfg['jira']['spec_md_path']}
        - app_validation_report.md path: {cfg['jira']['app_report_path']}

        The story number has already been provided above as {t['project_key']}-{t['story_number']}.
        Skip Step 1 (asking the user for a story number) and proceed directly with this story.

        Follow the test-case-creation-agent instructions completely, including:
        1. Fetch story {t['project_key']}-{t['story_number']} from Jira.
        2. Generate structured test cases for each Gherkin scenario.
        3. Present the full test case table to me for review before creating any Jira subtask (HIL checkpoint).
        4. Wait for my explicit approval before creating the Jira subtask.
        5. Create the subtask and save a local copy to the output directory.
    """).strip()


def build_test_validator_prompt(cfg: dict) -> str:
    v = cfg["test_validator"]
    return textwrap.dedent(f"""
        Use the test-case-validator sub-agent to validate test cases for a Jira story.

        Runtime inputs (use these — they override any defaults in the agent definition):
        - Jira story key:                {v['project_key']}-{v['story_number']}
        - spec.md path:                  {cfg['jira']['spec_md_path']}
        - app_validation_report.md path: {cfg['jira']['app_report_path']}

        Follow the test-case-validator instructions completely, including:
        1. Fetch story {v['project_key']}-{v['story_number']} and its test case subtask from Jira.
        2. Validate all test cases against spec.md and app_validation_report.md.
        3. Identify gaps, contradictions, missing coverage, and stale data.
        4. Present the full Validation Report with suggested fixes to me (HIL checkpoint).
        5. Wait for my explicit approval before updating Jira.
        6. Apply approved fixes to the subtask and add a validation comment.
    """).strip()


# ── Input collection ──────────────────────────────────────────────────────

def _ask(prompt_fn):
    """Wrap questionary .ask() and exit cleanly on Ctrl+C (returns None)."""
    result = prompt_fn.ask()
    if result is None:
        console.print("\n[dim]Cancelled.[/dim]")
        raise SystemExit(0)
    return result


def collect_crawling_inputs(cfg: dict) -> dict:
    console.print(Panel(
        "[bold]Agent 1 — Crawling Agent[/bold]\n"
        "[dim]Crawls source code and API docs → generates spec.md[/dim]",
        border_style="blue", expand=False,
    ))
    c = cfg["crawling"]
    c["github_url"]      = _ask(questionary.text("GitHub repository URL:", default=c["github_url"]))
    c["swagger_url"]     = _ask(questionary.text("Swagger / OpenAPI docs URL:", default=c["swagger_url"]))
    confluence_raw       = _ask(questionary.text(
        "Confluence documentation URLs (comma-separated, or leave blank):",
        default=", ".join(c["confluence_urls"]) if c["confluence_urls"] else "",
    ))
    c["confluence_urls"] = [u.strip() for u in confluence_raw.split(",") if u.strip()]
    c["output_dir"]      = _ask(questionary.text("Output directory:", default=c["output_dir"]))
    cfg["crawling"]      = c
    return cfg


def collect_app_validation_inputs(cfg: dict) -> dict:
    console.print(Panel(
        "[bold]Agent 2 — App Validation Agent[/bold]\n"
        "[dim]Navigates the live app with a real browser → generates app_validation_report.md[/dim]",
        border_style="blue", expand=False,
    ))
    a = cfg["app_validation"]
    a["app_url"]          = _ask(questionary.text("Live application URL:", default=a["app_url"]))
    a["test_email"]       = _ask(questionary.text("Test account email:", default=a["test_email"]))
    a["test_password"]    = _ask(questionary.password("Test account password:"))
    a["playwright_mode"]  = _ask(questionary.select(
        "Playwright browser mode:",
        choices=["headed", "headless"],
        default=a["playwright_mode"],
    ))
    a["output_dir"]       = _ask(questionary.text("Output directory:", default=a["output_dir"]))
    cfg["app_validation"] = a
    return cfg


def collect_jira_inputs(cfg: dict) -> dict:
    console.print(Panel(
        "[bold]Agent 3 — Jira AC Agent[/bold]\n"
        "[dim]Drafts Gherkin AC for Jira stories — includes HIL checkpoint before writing[/dim]",
        border_style="blue", expand=False,
    ))
    j = cfg["jira"]
    j["site"]            = _ask(questionary.text("Jira site (e.g. mysite.atlassian.net):", default=j["site"]))
    j["project_key"]     = _ask(questionary.text("Jira project key:", default=j["project_key"]))
    j["spec_md_path"]    = _ask(questionary.text("Path to spec.md:", default=j["spec_md_path"]))
    j["app_report_path"] = _ask(questionary.text("Path to app_validation_report.md:", default=j["app_report_path"]))
    cfg["jira"]          = j
    return cfg


def collect_test_cases_inputs(cfg: dict) -> dict:
    console.print(Panel(
        "[bold]Agent 4 — Test Case Creation Agent[/bold]\n"
        "[dim]Generates structured test cases from Jira story AC — includes HIL checkpoint before Jira write[/dim]",
        border_style="blue", expand=False,
    ))
    t = cfg["test_cases"]
    t["project_key"]           = _ask(questionary.text("Jira project key:", default=t["project_key"]))
    t["story_number"]          = _ask(questionary.text(
        f"Story number (e.g. 72 for {t['project_key']}-72):",
        default=t["story_number"],
    ))
    t["automation_github_url"] = _ask(questionary.text(
        "Automation framework GitHub URL (optional — press Enter to skip):",
        default=t["automation_github_url"],
    ))
    cfg["test_cases"] = t
    return cfg


def collect_test_validator_inputs(cfg: dict) -> dict:
    console.print(Panel(
        "[bold]Agent 5 — Test Case Validator Agent[/bold]\n"
        "[dim]Validates test cases vs spec and app report — includes HIL checkpoint before Jira update[/dim]",
        border_style="blue", expand=False,
    ))
    v = cfg["test_validator"]
    v["project_key"]  = _ask(questionary.text("Jira project key:", default=v["project_key"]))
    v["story_number"] = _ask(questionary.text(
        f"Story number to validate (e.g. 59 for {v['project_key']}-59):",
        default=v["story_number"],
    ))
    cfg["test_validator"] = v
    return cfg


# ── Playwright mode sync ──────────────────────────────────────────────────

def sync_playwright_mode(mode: str) -> None:
    """Call the existing set-playwright-mode.sh to patch ~/.claude.json."""
    script = PROJECT_DIR / "scripts" / "set-playwright-mode.sh"
    if script.exists():
        result = subprocess.run([str(script), mode])
        if result.returncode == 0 and mode != DEFAULT_CONFIG["app_validation"]["playwright_mode"]:
            console.print(
                "[yellow]Playwright mode updated. "
                "Restart Claude Code for the change to take effect.[/yellow]"
            )
    else:
        console.print(f"[yellow]Warning: set-playwright-mode.sh not found at {script}[/yellow]")


# ── Individual agent runners ──────────────────────────────────────────────

def run_crawling(cfg: dict) -> int:
    cfg = collect_crawling_inputs(cfg)
    save_config(cfg)
    return run_claude(build_crawling_prompt(cfg), "crawling-agent")


def run_app_validation(cfg: dict) -> int:
    cfg = collect_app_validation_inputs(cfg)
    save_config(cfg)
    sync_playwright_mode(cfg["app_validation"]["playwright_mode"])
    return run_claude(build_app_validation_prompt(cfg), "app-validation-agent")


def run_jira(cfg: dict) -> int:
    cfg = collect_jira_inputs(cfg)
    save_config(cfg)
    return run_claude(build_jira_prompt(cfg), "jira-agent")


def run_test_cases(cfg: dict) -> int:
    cfg = collect_test_cases_inputs(cfg)
    save_config(cfg)
    return run_claude(build_test_cases_prompt(cfg), "test-case-creation-agent")


def run_test_validator(cfg: dict) -> int:
    cfg = collect_test_validator_inputs(cfg)
    save_config(cfg)
    return run_claude(build_test_validator_prompt(cfg), "test-case-validator-agent")


# ── Full pipeline ─────────────────────────────────────────────────────────

def run_full_pipeline(cfg: dict) -> None:
    """
    Collect inputs for all agents upfront, then run Agents 1–5 sequentially.
    Story numbers for Agents 4 and 5 are collected just before those agents
    run (the user may not know the story numbers until after Agent 3 completes).
    """
    console.print(Panel(
        "[bold yellow]Full Pipeline Mode[/bold yellow]\n\n"
        "Runs all 5 agents in sequence:\n"
        "  1. Crawling → 2. App Validation → 3. Jira AC → 4. Test Cases → 5. Validator\n\n"
        "[dim]Collect inputs for Agents 1–3 now. "
        "Story numbers for Agents 4–5 will be asked before those agents launch.[/dim]",
        border_style="yellow",
    ))
    console.print()

    # Collect inputs for agents 1–3 upfront
    cfg = collect_crawling_inputs(cfg)
    console.print()
    cfg = collect_app_validation_inputs(cfg)
    console.print()
    cfg = collect_jira_inputs(cfg)
    save_config(cfg)
    console.print()

    confirmed = _ask(questionary.confirm("All inputs collected. Start the pipeline?", default=True))
    if not confirmed:
        console.print("[dim]Pipeline cancelled.[/dim]")
        return

    results: dict[str, str] = {}

    # Agents 1–3
    sequential_agents = [
        ("Agent 1 — Crawling",        lambda: run_claude(build_crawling_prompt(cfg),        "crawling-agent")),
        ("Agent 2 — App Validation",  lambda: run_claude(build_app_validation_prompt(cfg),  "app-validation-agent")),
        ("Agent 3 — Jira AC [HIL]",   lambda: run_claude(build_jira_prompt(cfg),            "jira-agent")),
    ]
    for label, runner in sequential_agents:
        console.rule(f"[bold cyan]{label}[/bold cyan]")
        code = runner()
        results[label] = "PASS" if code == 0 else f"FAIL (exit {code})"
        if code not in (0, 130):
            cont = _ask(questionary.confirm(
                f"{label} finished with exit {code}. Continue to next agent?",
                default=False,
            ))
            if not cont:
                _print_pipeline_summary(results)
                return

    # Agent 4: collect story number now
    console.rule("[bold cyan]Agent 4 — Test Case Creation [HIL][/bold cyan]")
    cfg = collect_test_cases_inputs(cfg)
    save_config(cfg)
    sync_playwright_mode(cfg["app_validation"]["playwright_mode"])
    code = run_claude(build_test_cases_prompt(cfg), "test-case-creation-agent")
    results["Agent 4 — Test Cases [HIL]"] = "PASS" if code == 0 else f"FAIL (exit {code})"

    # Agent 5: offer to reuse same story number
    console.rule("[bold cyan]Agent 5 — Test Case Validator [HIL][/bold cyan]")
    story_key = f"{cfg['test_cases']['project_key']}-{cfg['test_cases']['story_number']}"
    same = _ask(questionary.confirm(
        f"Validate the same story ({story_key})?",
        default=True,
    ))
    if same:
        cfg["test_validator"]["project_key"]  = cfg["test_cases"]["project_key"]
        cfg["test_validator"]["story_number"] = cfg["test_cases"]["story_number"]
    else:
        cfg = collect_test_validator_inputs(cfg)
    save_config(cfg)
    code = run_claude(build_test_validator_prompt(cfg), "test-case-validator-agent")
    results["Agent 5 — Validator [HIL]"] = "PASS" if code == 0 else f"FAIL (exit {code})"

    _print_pipeline_summary(results)


def _print_pipeline_summary(results: dict) -> None:
    table = Table(title="Pipeline Run Summary", border_style="dim", show_header=True)
    table.add_column("Agent",  style="bold", min_width=35)
    table.add_column("Result", min_width=20)
    for agent, result in results.items():
        color = "green" if result == "PASS" else "red"
        table.add_row(agent, f"[{color}]{result}[/{color}]")
    console.print()
    console.print(table)


# ── Configure settings ────────────────────────────────────────────────────

def configure_settings(cfg: dict) -> dict:
    section = _ask(questionary.select(
        "Which settings would you like to configure?",
        choices=[
            Choice("Crawling Agent settings",          "crawling"),
            Choice("App Validation settings",           "app_validation"),
            Choice("Jira integration settings",         "jira"),
            Choice("Test Case Creation settings",       "test_cases"),
            Choice("Test Case Validator settings",      "test_validator"),
            Choice("Playwright mode only",              "playwright_only"),
            Choice("View current config",               "view"),
            Choice("← Back to main menu",              "back"),
        ],
    ))

    if section == "back":
        return cfg

    if section == "crawling":
        cfg = collect_crawling_inputs(cfg)
    elif section == "app_validation":
        cfg = collect_app_validation_inputs(cfg)
        sync_playwright_mode(cfg["app_validation"]["playwright_mode"])
    elif section == "jira":
        cfg = collect_jira_inputs(cfg)
    elif section == "test_cases":
        cfg = collect_test_cases_inputs(cfg)
    elif section == "test_validator":
        cfg = collect_test_validator_inputs(cfg)
    elif section == "playwright_only":
        mode = _ask(questionary.select(
            "Playwright mode:",
            choices=["headed", "headless"],
            default=cfg["app_validation"]["playwright_mode"],
        ))
        cfg["app_validation"]["playwright_mode"] = mode
        sync_playwright_mode(mode)
    elif section == "view":
        display = json.loads(json.dumps(cfg))
        if display.get("app_validation", {}).get("test_password"):
            display["app_validation"]["test_password"] = "***"
        console.print_json(json.dumps(display, indent=2))
        _ask(questionary.press_any_key_to_continue("Press any key to continue..."))
        return cfg

    save_config(cfg)
    console.print("[green]Settings saved.[/green]")
    return cfg


# ── View reports ──────────────────────────────────────────────────────────

def view_reports(cfg: dict) -> None:
    project_dir = Path(cfg["project_dir"])

    # Discover available report files
    candidates = {
        "spec.md":                  project_dir / "spec.md",
        "app_validation_report.md": project_dir / "app_validation_report.md",
        "jira_ac_report.md":        project_dir / "jira_ac_report.md",
    }
    for f in sorted(project_dir.glob("test_cases_*.md")):
        candidates[f.name] = f

    choices = []
    for name, path in candidates.items():
        if path.exists():
            choices.append(Choice(name, str(path)))

    if not choices:
        console.print("[yellow]No reports found. Run some agents first.[/yellow]")
        return

    choices.append(Choice("← Back", "back"))

    selected = _ask(questionary.select("Select a report to view:", choices=choices))
    if selected == "back":
        return

    content = Path(selected).read_text()
    with console.pager():
        console.print(Markdown(content))


# ── Banner ────────────────────────────────────────────────────────────────

def print_banner() -> None:
    console.print()
    console.print(Panel(
        "[bold cyan]UAF — Unified Automation Framework[/bold cyan]\n"
        "[dim]AI-powered test pipeline orchestrator  •  Powered by Claude Code  •  v"
        + VERSION + "[/dim]\n\n"
        f"[dim]Project : {PROJECT_DIR}[/dim]\n"
        f"[dim]Config  : {CONFIG_FILE}[/dim]",
        border_style="cyan",
        expand=False,
    ))
    console.print()

    if not _claude_available():
        console.print(Panel(
            "[bold red]Warning:[/bold red] `claude` CLI not found in PATH.\n"
            "Agents will not run until Claude Code is installed.\n"
            "Install from: https://claude.ai/code",
            border_style="red",
            expand=False,
        ))
        console.print()


# ── Main menu loop ────────────────────────────────────────────────────────

def main_menu(cfg: dict) -> None:
    while True:
        answer = _ask(questionary.select(
            "What would you like to do?",
            choices=[
                Separator("── Run Agents ──────────────────────────────────────"),
                Choice("1  Crawling Agent        GitHub + Swagger → spec.md",        "crawling"),
                Choice("2  App Validation Agent  Playwright → app_validation_report", "app_validation"),
                Choice("3  Jira AC Agent   [HIL] Gherkin AC → Jira stories",          "jira"),
                Choice("4  Test Case Creation    [HIL] AC → test steps → Jira subtask","test_cases"),
                Choice("5  Test Case Validator   [HIL] validate & fix Jira subtask",   "test_validator"),
                Choice("★  Run Full Pipeline     Agents 1–5 sequentially",             "full_pipeline"),
                Separator("── Utilities ───────────────────────────────────────"),
                Choice("   Configure Settings",  "configure"),
                Choice("   View Reports",        "view_reports"),
                Choice("   Exit",               "exit"),
            ],
        ))

        console.print()

        if answer == "exit":
            console.print("[dim]Goodbye.[/dim]")
            break
        elif answer == "crawling":
            run_crawling(cfg)
        elif answer == "app_validation":
            run_app_validation(cfg)
        elif answer == "jira":
            run_jira(cfg)
        elif answer == "test_cases":
            run_test_cases(cfg)
        elif answer == "test_validator":
            run_test_validator(cfg)
        elif answer == "full_pipeline":
            run_full_pipeline(cfg)
        elif answer == "configure":
            cfg = configure_settings(cfg)
        elif answer == "view_reports":
            view_reports(cfg)


# ── Entrypoint ────────────────────────────────────────────────────────────

def main() -> None:
    try:
        print_banner()
        cfg = load_config()
        main_menu(cfg)
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted. Goodbye.[/dim]")
        sys.exit(0)


if __name__ == "__main__":
    main()
