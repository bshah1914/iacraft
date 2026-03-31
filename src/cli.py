"""CLI interface for message-to-iaac with detailed logging."""

import os
import sys
import time
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from dotenv import load_dotenv

from .config import (
    PipelineConfig,
    SUPPORTED_CLOUDS,
    SUPPORTED_IAC_TOOLS,
    SUPPORTED_PROVIDERS,
    DEFAULT_REGIONS,
    DEFAULT_MODELS,
    DEFAULT_OLLAMA_URL,
)
from .engine import PipelineEngine

console = Console()

BANNER = r"""
  ___        ____            __ _
 |_ _|__ _  / ___|_ __ __ _ / _| |_
  | |/ _` || |   | '__/ _` | |_| __|
  | | (_| || |___| | | (_| |  _| |_
 |___\__,_| \____|_|  \__,_|_|  \__|

  Craft Cloud Infrastructure from Natural Language
"""

STEP_NAMES = {
    0: "Initializing",
    1: "Requirement Analysis",
    2: "Service Abstraction",
    3: "Cloud-Agnostic Architecture",
    4: "Cloud Service Mapping",
    5: "IaC Code Generation",
    6: "Architecture Diagram",
    7: "Security Controls",
    8: "Compliance Mapping",
    9: "Cost Estimation",
    10: "Validation Plan",
    11: "Auto-Fix Loop",
}

STEP_ICONS = {
    "analyzing": "🔍",
    "building": "🏗️",
    "mapping": "🗺️",
    "generating": "⚡",
    "creating": "📊",
    "defining": "🔐",
    "estimating": "💰",
    "running": "🔄",
    "complete": "✅",
    "failed": "❌",
    "starting": "🚀",
}

_step_start_times = {}


def get_icon(message: str) -> str:
    """Get icon based on message content."""
    msg = message.lower()
    for key, icon in STEP_ICONS.items():
        if key in msg:
            return icon
    return "📋"


def status_callback(step: int, message: str):
    """Detailed, rich-formatted status callback."""
    now = time.time()

    if step == 0:
        _step_start_times.clear()
        _step_start_times[0] = now
        console.print()
        console.print(f"  🚀 [bold cyan]{message}[/]")
        console.print(f"  {'─' * 60}")
        return

    # Track timing
    if "..." in message:
        _step_start_times[step] = now

    # Calculate elapsed for completed steps
    elapsed_str = ""
    if step in _step_start_times and "..." not in message:
        elapsed = now - _step_start_times[step]
        elapsed_str = f" [dim]({elapsed:.1f}s)[/]"

    # Determine icon and style
    icon = get_icon(message)
    step_name = STEP_NAMES.get(step, f"Step {step}")

    if "FAIL" in message:
        console.print(f"  ❌ [bold red]Step {step}/11 — {step_name}[/]{elapsed_str}")
        console.print(f"     [red]{message}[/]")
    elif "complete" in message.lower() or "created" in message.lower() or "defined" in message.lower() or "analyzed" in message.lower() or "mapped" in message.lower() or "generated" in message.lower() or "estimation" in message.lower():
        console.print(f"  ✅ [green]Step {step}/11 — {step_name}[/]{elapsed_str}")
        console.print(f"     [dim]{message}[/]")
    elif "..." in message:
        console.print(f"  {icon} [yellow]Step {step}/11 — {step_name}[/]")
        console.print(f"     [dim]{message}[/]")
    else:
        console.print(f"  {icon} [white]Step {step}/11[/] {message}{elapsed_str}")


@click.group()
@click.version_option(version="2.0.0", prog_name="iacraft")
def cli():
    """Convert natural language to Infrastructure as Code."""
    pass


@cli.command()
@click.argument("message", nargs=-1, required=True)
@click.option("--cloud", "-c", type=click.Choice(SUPPORTED_CLOUDS), default="aws", help="Cloud provider")
@click.option("--iac", "-i", type=click.Choice(SUPPORTED_IAC_TOOLS), default="terraform", help="IaC tool")
@click.option("--region", "-r", default=None, help="Cloud region (auto-detected if not set)")
@click.option("--output", "-o", default="output", help="Output directory")
@click.option("--provider", "-p", type=click.Choice(SUPPORTED_PROVIDERS), default="groq", help="LLM provider")
@click.option("--model", "-m", default=None, help="Model name (auto-detected per provider if not set)")
@click.option("--ollama-url", default=None, help=f"Ollama server URL (default: {DEFAULT_OLLAMA_URL})")
@click.option("--simulate/--no-simulate", default=False, help="Run code simulator after generation")
def generate(message, cloud, iac, region, output, provider, model, ollama_url, simulate):
    """Generate infrastructure from a natural language message.

    Examples:

        # Using Groq (default, FREE, ultra-fast)
        m2iac generate "Deploy a 3-tier web app with PostgreSQL"

        # With code simulator
        m2iac generate --simulate "EC2 instance with ALB"

        # Azure + Gemini
        m2iac generate --provider gemini --cloud azure "Web app with SQL"
    """
    load_dotenv()

    user_message = " ".join(message)
    effective_model = model or DEFAULT_MODELS[provider]
    effective_region = region or DEFAULT_REGIONS[cloud]

    console.print(Panel(BANNER, style="bold blue", expand=False))

    # Configuration summary
    config_table = Table(show_header=False, box=None, padding=(0, 2))
    config_table.add_column(style="cyan bold")
    config_table.add_column(style="white")
    config_table.add_row("Input", user_message)
    config_table.add_row("Provider", f"{provider} ({effective_model})")
    config_table.add_row("Cloud", f"{cloud.upper()} / {effective_region}")
    config_table.add_row("IaC Tool", iac)
    config_table.add_row("Output", f"{output}/")
    console.print(Panel(config_table, title="[bold]Configuration[/]", expand=False))

    # Validate provider-specific requirements
    key_map = {"claude": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY"}
    if provider in key_map and not os.getenv(key_map[provider]):
        console.print(f"[bold red]Error:[/] {key_map[provider]} not set.")
        console.print(f"[dim]Tip: Use --provider groq (free) or --provider ollama (local)[/]")
        sys.exit(1)

    try:
        start_time = time.time()

        config = PipelineConfig(
            user_message=user_message,
            cloud=cloud,
            iac_tool=iac,
            region=region,
            output_dir=output,
            provider=provider,
            model=model,
            ollama_url=ollama_url,
        )

        engine = PipelineEngine(config, on_status=status_callback)
        results = engine.run()

        elapsed = time.time() - start_time

        # Results summary
        console.print()
        errors = results.get("errors", [])
        if errors:
            console.print(Panel(f"[bold yellow]Pipeline Done with {len(errors)} warning(s)[/]", expand=False))
        else:
            console.print(Panel("[bold green]Pipeline Complete — All Steps Passed[/]", expand=False))

        # Stats
        stats_table = Table(show_header=False, box=None, padding=(0, 2))
        stats_table.add_column(style="cyan")
        stats_table.add_column(style="white")
        stats_table.add_row("Total Time", f"{elapsed:.1f}s")
        stats_table.add_row("IaC Files", str(len(results.get("iac_files", []))))
        stats_table.add_row("Services Mapped", str(len(results.get("mapping", {}).get("mappings", []))))

        analysis = results.get("analysis", {})
        if analysis.get("app_type"):
            stats_table.add_row("App Type", analysis["app_type"])
        if analysis.get("availability"):
            stats_table.add_row("Availability", analysis["availability"])
        console.print(Panel(stats_table, title="[bold]Summary[/]", expand=False))

        # File tree
        tree = Tree(f"📁 [bold]{output}/[/]")
        tf_branch = tree.add("📁 terraform/")
        for f in results.get("iac_files", []):
            name = os.path.basename(str(f))
            tf_branch.add(f"📄 {name}")
        arch_branch = tree.add("📁 architecture/")
        for name in ["architecture.json", "cloud-mapping.md", "diagram.mmd", "security-controls.md", "compliance.md", "cost-estimate.md"]:
            arch_branch.add(f"📄 {name}")
        val_branch = tree.add("📁 validation/")
        val_branch.add("📄 validation-plan.md")
        val_branch.add("📄 auto-fix-report.md")
        tree.add("📄 REPORT.md")
        console.print(Panel(tree, title="[bold]Generated Files[/]", expand=False))

        # Next steps
        console.print(Panel(
            f"[bold]Next steps:[/]\n"
            f"  1. cd {output}/terraform\n"
            f"  2. terraform init\n"
            f"  3. terraform plan\n"
            f"  4. terraform apply\n\n"
            f"  [dim]Or run simulator: python main.py simulate -o {output}[/]",
            expand=False,
        ))

        # Run simulator if requested
        if simulate:
            _run_simulator(output, provider, model, ollama_url)

    except Exception as e:
        console.print(f"\n[bold red]Error:[/] {e}")
        if "--verbose" in sys.argv:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.option("--output", "-o", default="output", help="Output directory")
@click.option("--provider", "-p", type=click.Choice(SUPPORTED_PROVIDERS), default="groq", help="LLM provider for auto-fix")
@click.option("--model", "-m", default=None, help="Model name")
@click.option("--ollama-url", default=None, help="Ollama server URL")
def simulate(output, provider, model, ollama_url):
    """Run the code simulator on generated Terraform code.

    Validates using terraform fmt, validate, and checkov.
    Auto-fixes errors using the LLM. Up to 5 rounds.
    """
    load_dotenv()
    _run_simulator(output, provider, model, ollama_url)


def _run_simulator(output, provider, model, ollama_url):
    """Shared simulator logic for generate --simulate and simulate command."""
    from .llm_client import LLMClient
    from .file_writer import FileWriter
    from .validator import CodeSimulator, TerraformValidator

    terraform_dir = os.path.join(output, "terraform")
    if not os.path.exists(terraform_dir):
        console.print("[bold red]Error:[/] No terraform files found. Run generate first.")
        sys.exit(1)

    console.print(Panel("[bold cyan]Code Simulator[/]", expand=False))

    # Show available tools
    validator = TerraformValidator(terraform_dir)
    tools = validator.get_available_tools()
    for tool, available in tools.items():
        icon = "✅" if available else "❌"
        console.print(f"  {icon} {tool}")
    console.print()

    def sim_status(msg):
        if "PASS" in msg:
            console.print(f"    [green]{msg}[/]")
        elif "FAIL" in msg or "error" in msg.lower():
            console.print(f"    [red]{msg}[/]")
        elif "Round" in msg:
            console.print(f"\n  🔄 [bold yellow]{msg}[/]")
        elif "Auto-fix" in msg or "Fixes" in msg:
            console.print(f"    [cyan]{msg}[/]")
        elif "passed" in msg.lower():
            console.print(f"    [bold green]{msg}[/]")
        else:
            console.print(f"    [dim]{msg}[/]")

    try:
        llm = LLMClient(provider=provider, model=model, ollama_url=ollama_url)
        writer = FileWriter(output)
        sim = CodeSimulator(terraform_dir, llm, writer, on_status=sim_status)
        report = sim.run()

        # Summary
        console.print()
        if report.final_passed:
            console.print(Panel("[bold green]All Validations Passed[/]", expand=False))
        else:
            console.print(Panel(f"[bold yellow]{report.total_errors_found - report.total_errors_fixed} issues remaining[/]", expand=False))

        stats = Table(show_header=False, box=None, padding=(0, 2))
        stats.add_column(style="cyan")
        stats.add_column(style="white")
        stats.add_row("Rounds", str(len(report.rounds)))
        stats.add_row("Errors Found", str(report.total_errors_found))
        stats.add_row("Errors Fixed", str(report.total_errors_fixed))
        stats.add_row("Status", "[green]PASSED[/]" if report.final_passed else "[red]ISSUES REMAINING[/]")
        console.print(stats)

    except Exception as e:
        console.print(f"[bold red]Simulator Error:[/] {e}")


@cli.command()
@click.argument("message", nargs=-1, required=True)
@click.option("--cloud", "-c", type=click.Choice(SUPPORTED_CLOUDS), default="aws", help="Cloud provider")
@click.option("--provider", "-p", type=click.Choice(SUPPORTED_PROVIDERS), default="groq", help="LLM provider")
@click.option("--model", "-m", default=None, help="Model name")
@click.option("--ollama-url", default=None, help="Ollama server URL")
def analyze(message, cloud, provider, model, ollama_url):
    """Analyze a requirement without generating full IaC.

    Quick mode - only runs Step 1 (Requirement Analysis).
    """
    load_dotenv()
    user_message = " ".join(message)
    effective_model = model or DEFAULT_MODELS[provider]

    console.print(f"\n[bold]Analyzing:[/] {user_message}")
    console.print(f"[dim]Provider: {provider} | Model: {effective_model}[/]\n")

    key_map = {"claude": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY"}
    if provider in key_map and not os.getenv(key_map[provider]):
        console.print(f"[bold red]Error:[/] {key_map[provider]} not set.")
        sys.exit(1)

    from .llm_client import LLMClient
    from .prompts.system_prompts import MASTER_SYSTEM_PROMPT, get_step1_prompt

    try:
        llm = LLMClient(provider=provider, model=model, ollama_url=ollama_url)
        prompt = get_step1_prompt(cloud, DEFAULT_REGIONS[cloud], "terraform")
        prompt += f"\n\nUser requirement:\n{user_message}"

        analysis = llm.generate_json(MASTER_SYSTEM_PROMPT, prompt)

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="cyan bold")
        table.add_column(style="white")
        for key, value in analysis.items():
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            table.add_row(key, str(value))
        console.print(Panel(table, title="[bold]Requirement Analysis[/]", expand=False))

    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        sys.exit(1)


@cli.command()
def providers():
    """Show supported cloud providers, IaC tools, and LLM backends."""
    table = Table(title="Supported Configurations")
    table.add_column("Type", style="cyan")
    table.add_column("Options", style="green")
    table.add_column("Default", style="yellow")

    table.add_row("LLM Providers", ", ".join(SUPPORTED_PROVIDERS), "groq")
    table.add_row("Groq Models", "llama-3.3-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b-32768", DEFAULT_MODELS["groq"])
    table.add_row("Gemini Models", "gemini-2.0-flash, gemini-1.5-flash", DEFAULT_MODELS["gemini"])
    table.add_row("OpenAI Models", "gpt-4o-mini, gpt-4o", DEFAULT_MODELS["openai"])
    table.add_row("Ollama Models", "qwen2.5-coder:7b, llama3:8b, codellama", DEFAULT_MODELS["ollama"])
    table.add_row("Claude Models", "claude-sonnet-4-6, claude-opus-4-6", DEFAULT_MODELS["claude"])
    table.add_row("Cloud Providers", ", ".join(SUPPORTED_CLOUDS), "aws")
    table.add_row("IaC Tools", ", ".join(SUPPORTED_IAC_TOOLS), "terraform")

    console.print(table)


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=15000, type=int, help="Port to run on")
def dashboard(host, port):
    """Launch the web dashboard UI on port 15000."""
    import uvicorn
    import subprocess
    load_dotenv()

    # Kill old process on same port
    try:
        result = subprocess.run(
            f'netstat -ano | findstr ":{port} " | findstr "LISTEN"',
            capture_output=True, text=True, shell=True,
        )
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                pid = line.strip().split()[-1]
                if pid and pid != "0":
                    subprocess.run(f"taskkill /f /pid {pid}", shell=True, capture_output=True)
    except Exception:
        pass

    console.print(Panel(BANNER, style="bold blue", expand=False))
    console.print(f"  [bold cyan]Dashboard:[/] [green]http://localhost:{port}[/]\n")
    uvicorn.run("src.dashboard.app:app", host=host, port=port)


def main():
    """Entry point."""
    cli()


if __name__ == "__main__":
    main()
