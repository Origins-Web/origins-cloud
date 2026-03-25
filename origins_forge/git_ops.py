import json
import requests
from pathlib import Path
from github import Github
from rich.console import Console

from .config import MANIFEST_URL, MANIFEST_FILE, load_config
from .utils import run_cmd

console = Console()

def sync_logic() -> dict:
    """Fetch the latest templates manifest from GitHub."""
    try:
        response = requests.get(MANIFEST_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        MANIFEST_FILE.write_text(json.dumps(data, indent=2))
        return data
    except requests.RequestException:
        if MANIFEST_FILE.exists():
            return json.loads(MANIFEST_FILE.read_text())
        return {}

def ship_to_github(target_dir: Path, repo_name: str) -> None:
    """Automates local git init and remote push to GitHub."""
    gh_token = load_config().get("github_token")
    if not gh_token:
        console.print("[yellow]GitHub token not found. Run 'origins config' to set it. Skipping remote push.[/yellow]")
        return

    try:
        with console.status("[bold blue]Creating GitHub repository...[/bold blue]"):
            g = Github(gh_token)
            user = g.get_user()
            repo = user.create_repo(repo_name, private=True)
        
        with console.status("[bold green]Pushing code to GitHub...[/bold green]"):
            run_cmd(["git", "init"], cwd=target_dir)
            run_cmd(["git", "add", "."], cwd=target_dir)
            run_cmd(["git", "commit", "-m", "🚀 Initial build by Origins Forge"], cwd=target_dir)
            run_cmd(["git", "branch", "-M", "main"], cwd=target_dir)
            
            remote_url = repo.clone_url.replace("https://", f"https://{gh_token}@")
            run_cmd(["git", "remote", "add", "origin", remote_url], cwd=target_dir)
            run_cmd(["git", "push", "-u", "origin", "main"], cwd=target_dir)

        console.print(f"\n[bold green]✅ Project successfully shipped![/bold green]")
        console.print(f"🔗 View it here: [link={repo.html_url}]{repo.html_url}[/link]\n")

    except Exception as e:
        console.print(f"[bold red]❌ GitHub Sync Failed:[/bold red] {e}")