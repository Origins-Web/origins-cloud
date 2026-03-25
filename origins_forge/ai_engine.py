import time
from typing import Any
from google import genai
from google.genai import errors
from rich.console import Console

console = Console()

def retry_generate(client: genai.Client, model_id: str, contents: str) -> Any:
    """Handles 429 errors by waiting and retrying to stay within Free Tier limits."""
    for attempt in range(5):
        try:
            return client.models.generate_content(model=model_id, contents=contents)
        except errors.ClientError as e:
            if "429" in str(e):
                wait_time = 12 * (attempt + 1)
                console.print(f"[yellow]⚠️  AI Engine Busy. Cooling down ({wait_time}s)...[/yellow]")
                time.sleep(wait_time)
            else:
                raise e
    raise Exception("Max retries exceeded. AI quota is fully exhausted.")