import json
import platform
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import questionary
import requests
import typer
from google import genai
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import track
from rich.prompt import Prompt, Confirm
from rich.table import Table

# --- LOCAL IMPORTS ---
from .config import (
    APP_NAME, CURRENT_VERSION, PROJECTS_DIR, CACHE_DIR, CONFIG_FILE,
    CONFIG_DIR, VERSION_URL, load_config, save_config
)
from .utils import run_cmd, get_project_type
from .git_ops import sync_logic, ship_to_github
from .ai_engine import retry_generate

app = typer.Typer(help=f"{APP_NAME} v{CURRENT_VERSION}", add_completion=False)
console = Console()
CLI_ROOT = Path(__file__).parent.resolve()

@app.command()
def config(
    reset: bool = typer.Option(False, "--reset", help="Clear all saved settings."),
    show: bool = typer.Option(False, "--show", help="Show current configuration.")
):
    """⚙️  Manage Origins Forge configuration."""
    if reset:
        if Confirm.ask("[bold red]Reset all settings?[/bold red]"):
            if CONFIG_FILE.exists():
                CONFIG_FILE.unlink()
            console.print("[green]Settings wiped.[/green]")
        return

    if show:
        cfg = load_config()
        table = Table(title="Origins Forge Config")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_row("Projects Dir", str(PROJECTS_DIR))
        
        key = cfg.get("gemini_key", "Not Set")
        masked = f"{key[:8]}****" if len(key) > 8 else key
        table.add_row("Gemini API Key", masked)
        
        gh_token = cfg.get("github_token", "Not Set")
        gh_masked = f"{gh_token[:8]}****" if len(gh_token) > 8 else gh_token
        table.add_row("GitHub Token", gh_masked)
        
        console.print(table)

@app.command()
def sync():
    """🌍 Sync with Origins HQ to download latest blueprints."""
    console.print("[bold blue]🌍 Syncing with Origins HQ...[/bold blue]")
    templates = sync_logic()
    table = Table(title=f"Synced {len(templates)} Blueprints")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Type", style="magenta")
    for key, val in templates.items():
        table.add_row(key, val.get('name', 'Unknown'), val.get('type', 'Unknown'))
    console.print(table)

@app.command()
def clone(template_id: str = typer.Argument(None)):
    """🏗️  Clone proprietary blueprints with automated git scrubbing."""
    templates = sync_logic()
    if not template_id:
        for k, v in templates.items():
            console.print(f" • [cyan]{k}[/cyan]: {v.get('description', 'No description')}")
        template_id = Prompt.ask("Select Template ID")

    if template_id not in templates:
        console.print("[red]Error: Template ID not found.[/red]")
        raise typer.Exit()

    repo_data = templates[template_id]
    client = Prompt.ask("Client Name")
    slug = client.lower().replace(" ", "_")
    
    target_dir = PROJECTS_DIR / slug
    cached_path = CACHE_DIR / template_id

    if not cached_path.exists():
        console.print(f"[dim]Downloading {template_id} to global cache...[/dim]")
        run_cmd(["git", "clone", repo_data['url'], str(cached_path)])
    
    if target_dir.exists():
        console.print(f"[red]Error: Project {slug} already exists in {PROJECTS_DIR}[/red]")
        raise typer.Exit()

    shutil.copytree(cached_path, target_dir, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git"))
    
    config_data = {"client": client, "template": repo_data['name'], "type": repo_data['type']}
    (target_dir / "origins.config.json").write_text(json.dumps(config_data, indent=2))

    console.print(Panel(
        f"Project Created Successfully!\n\n"
        f"📍 Location: [bold cyan]{target_dir}[/bold cyan]\n"
        f"🚀 Run: [white]cd {target_dir} && origins setup[/white]", 
        title="Origins Forge", 
        border_style="green"
    ))

@app.command()
def build(
    prompt: str = typer.Argument(None, help="Describe the app you want to build"),
    wizard: bool = typer.Option(False, "--wizard", "-w", help="Launch interactive setup"),
    swarm: bool = typer.Option(False, "--swarm", "-s", help="Use parallel AI agents")
):
    """🚀 Origins Build: High-speed app generation with Quota Management."""
    config = load_config()
    gemini_key = config.get("gemini_key")
    if not gemini_key:
        gemini_key = Prompt.ask("🔑 Enter Gemini API Key", password=True)
        save_config("gemini_key", gemini_key)
        
    client = genai.Client(api_key=gemini_key)

    if wizard:
        answers = questionary.form(
            name=questionary.text("Project Name (slug):", default="origins-app"),
            stack=questionary.select("Framework:", choices=["FastAPI", "Next.js", "Flask"]),
            db=questionary.select("Database:", choices=["PostgreSQL", "MongoDB", "SQLite"]),
            features=questionary.checkbox("Include Features:", choices=["Docker", "Auth", "CI/CD"]),
        ).ask()
        project_name = answers['name']
        final_prompt = f"Build a {answers['stack']} app with {answers['db']}. Features: {', '.join(answers['features'])}"
    else:
        final_prompt = prompt or Prompt.ask("What would you like to build today?")
        project_name = Prompt.ask("Project Name", default="origins-ai-app")

    target_dir = PROJECTS_DIR / project_name
    target_dir.mkdir(parents=True, exist_ok=True)
    model_id = 'gemini-3-flash-preview'

    if swarm:
        console.print(Panel("🐝 [bold magenta]Swarm Mode[/bold magenta]\nDeploying parallel agents...", border_style="magenta"))
        tasks = {
            "api/main.py": f"Core API entry point for {final_prompt}",
            "requirements.txt": f"Dependencies for {final_prompt}",
            "README.md": f"Professional documentation for {final_prompt}",
            ".gitignore": "Standard python and env gitignore"
        }

        def run_agent(file_path: str, task_prompt: str):
            full_path = target_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            res = retry_generate(client, model_id, task_prompt)
            clean_code = res.text.strip().removeprefix("```python").removeprefix("```").removesuffix("```").strip()
            full_path.write_text(clean_code)

        with ThreadPoolExecutor(max_workers=2) as executor:
            executor.map(lambda p: run_agent(p[0], p[1]), tasks.items())
    else:
        with console.status("[bold cyan]Architecting...[/bold cyan]"):
            struct_res = retry_generate(client, model_id, f"Return ONLY a JSON list of file paths for: {final_prompt}")
            clean_json = struct_res.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            files = json.loads(clean_json)

        for f_path in track(files, description="Writing files..."):
            full_path = target_dir / f_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            code_res = retry_generate(client, model_id, f"Write code for {f_path} in {final_prompt}. Return ONLY code.")
            clean_code = code_res.text.strip().removeprefix("```python").removeprefix("```").removesuffix("```").strip()
            full_path.write_text(clean_code)

    console.print(Panel(f"✅ Build Complete: {target_dir}", title="Origins Factory", border_style="green"))

    if Confirm.ask("Push to GitHub?"):
        ship_to_github(target_dir, project_name)

@app.command()
def ask(question: str):
    """🧠 Query the Origins AI (Gemini 3 Flash)"""
    cfg = load_config()
    api_key = cfg.get("gemini_key")
    
    if not api_key:
        api_key = Prompt.ask("🔑 Enter Gemini API Key", password=True)
        save_config("gemini_key", api_key)

    try:
        client = genai.Client(api_key=api_key)
        with console.status("[bold green]Gemini 3 is thinking...[/bold green]"):
            response = client.models.generate_content(
                model='gemini-3-flash-preview', 
                contents=question
            )
            console.print(Panel(
                Markdown(response.text), 
                title="Origins AI", 
                border_style="cyan"
            ))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@app.command()
def get(item: str = typer.Argument(..., help="Item to install (git, node, python, docker)")):
    """📥 Universal Downloader: Auto-detects OS and installs dependencies."""
    registry = {
        "git": {"brew": "git", "winget": "Git.Git", "apt": "git"},
        "node": {"brew": "node", "winget": "OpenJS.NodeJS", "apt": "nodejs"},
        "python": {"brew": "python@3.12", "winget": "Python.Python.3.12", "apt": "python3"},
        "docker": {"brew": "docker", "winget": "Docker.DockerDesktop", "apt": "docker.io"},
    }

    item = item.lower()
    os_type = platform.system().lower()

    if item not in registry:
        console.print(f"[red]Item '{item}' not found in registry.[/red]")
        return

    commands = registry[item]

    try:
        if os_type == "darwin":
            with console.status(f"🍎 [bold]MacOS:[/bold] Installing {item} via Brew..."):
                run_cmd(["brew", "install", commands["brew"]])
        elif os_type == "windows":
            with console.status(f"🪟 [bold]Windows:[/bold] Installing {item} via Winget..."):
                run_cmd(["winget", "install", "--id", commands["winget"], "--silent", "--accept-source-agreements"])
        elif os_type == "linux":
            with console.status(f"🐧 [bold]Linux:[/bold] Installing {item} via APT..."):
                run_cmd(["sudo", "apt-get", "update"])
                run_cmd(["sudo", "apt-get", "install", "-y", commands["apt"]])

        console.print(f"✅ [bold green]{item.upper()} installed successfully on {os_type.capitalize()}![/bold green]")
    except Exception:
        console.print(f"[bold red]❌ Installation failed:[/bold red] Ensure your system package manager is configured.")

@app.command()
def setup():
    """🚀 Automatically detects project type, installs dependencies, and starts localhost."""
    console.print("✨ [bold]ORIGINS SMART SETUP[/bold] ✨")
    cwd = Path.cwd()
    
    if (cwd / "package.json").exists():
        console.print("📦 [cyan]Detected Node.js Project...[/cyan]")
        with console.status("[bold green]Installing dependencies via npm...[/bold green]"):
            run_cmd("npm install", shell=True, capture=False)
        console.print("🌐 [bold blue]Starting local server...[/bold blue]")
        subprocess.run("npm run dev", shell=True)
        
    elif (cwd / "requirements.txt").exists() or (cwd / "main.py").exists():
        console.print("🐍 [yellow]Detected Python Project...[/yellow]")
        venv_dir = cwd / "venv"
        
        if not venv_dir.exists():
            console.print("📁 Creating virtual environment...")
            run_cmd([sys.executable, "-m", "venv", "venv"])

        is_win = platform.system() == "Windows"
        pip_path = venv_dir / "Scripts" / "pip" if is_win else venv_dir / "bin" / "pip"
        python_path = venv_dir / "Scripts" / "python" if is_win else venv_dir / "bin" / "python"

        if (cwd / "requirements.txt").exists():
            with console.status("[bold green]Installing dependencies...[/bold green]"):
                run_cmd([str(pip_path), "install", "-r", "requirements.txt"], capture=False)
        
        console.print("🌐 [bold blue]Starting FastAPI server...[/bold blue]")
        subprocess.run([str(python_path), "-m", "uvicorn", "main:app", "--reload"])
    else:
        console.print("[red]❌ No project type detected. Missing package.json or requirements.txt.[/red]")

@app.command()
def start():
    """🚀 Quick Start: Launch local server based on project type."""
    ptype = get_project_type()
    if ptype == "web":
        subprocess.run("npm run dev", shell=True)
    elif ptype == "ai":
        subprocess.run("uvicorn main:app --reload", shell=True)
    else:
        console.print("[red]Unknown project type. Cannot start.[/red]")

@app.command()
def list():
    """📂 List all Origins Forge projects."""
    if not PROJECTS_DIR.exists():
        console.print("[yellow]No projects directory found.[/yellow]")
        return
        
    projects = [d.name for d in PROJECTS_DIR.iterdir() if d.is_dir()]
    table = Table(title="Origins Forge Projects")
    table.add_column("Project Name", style="cyan")
    for p in projects: 
        table.add_row(p)
    console.print(table)

@app.command()
def where():
    """📍 Locate all Origins Engine directories and binaries."""
    table = Table(title="Origins Engine Location Map", show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan")
    table.add_column("Path", style="green")

    bin_path = shutil.which("origins") or "Not Found (Run within venv)"
    table.add_row("Executable Binary", bin_path)
    table.add_row("Global Config", str(CONFIG_FILE))
    table.add_row("Software Factory", str(PROJECTS_DIR))
    table.add_row("Source Code", str(CLI_ROOT))

    console.print(table)
    console.print(f"\n[dim]To open the config folder, run:[/dim] [bold]open {CONFIG_DIR}[/bold]")

@app.command()
def version():
    """🔢 Check current version and look for updates."""
    console.print(f"[bold]Origins Forge v{CURRENT_VERSION}[/bold]")
    try:
        response = requests.get(VERSION_URL, timeout=3)
        if response.status_code == 200:
            latest_version = response.text.strip()
            if latest_version != CURRENT_VERSION:
                console.print(Panel(
                    f"✨ [bold green]New Update Available: {latest_version}[/bold green]\n"
                    f"Run [bold cyan]origins update[/bold cyan] to get the latest features.",
                    border_style="orange1"
                ))
            else:
                console.print("[green]✅ You are running the latest version.[/green]")
    except requests.RequestException:
        console.print("[yellow]⚠️  Could not reach update server. Check your connection.[/yellow]")

if __name__ == "__main__":
    app()