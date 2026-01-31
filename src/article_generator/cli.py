"""Command-line interface for the AI Article Generator."""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .ai_writer import AIArticleWriter, GeneratedArticle
from .config import Config, get_config, set_config
from .google_docs import GoogleDocsClient
from .research import WebResearcher

app = typer.Typer(
    name="article-gen",
    help="AI-powered education article research and generation tool.",
    add_completion=False,
)
console = Console()


def validate_config(config: Config) -> bool:
    """Validate configuration and show errors."""
    errors = config.validate()
    if errors:
        console.print("[red]Configuration errors:[/red]")
        for error in errors:
            console.print(f"  [red]•[/red] {error}")
        console.print("\nRun [cyan]article-gen setup[/cyan] to configure the application.")
        return False
    return True


@app.command()
def setup(
    env_file: Path = typer.Option(
        Path(".env"),
        "--env-file",
        "-e",
        help="Path to .env file to create/update",
    ),
):
    """Interactive setup wizard for configuring the application."""
    console.print(Panel("AI Article Generator Setup", style="bold blue"))

    config_values = {}

    # Anthropic API Key
    console.print("\n[bold]1. Anthropic API Key[/bold]")
    console.print("Get your API key from: https://console.anthropic.com/")
    api_key = Prompt.ask("Enter your Anthropic API key", password=True)
    config_values["ANTHROPIC_API_KEY"] = api_key

    # Google credentials
    console.print("\n[bold]2. Google Cloud Setup[/bold]")
    console.print(
        "You need OAuth2 credentials from Google Cloud Console.\n"
        "1. Go to https://console.cloud.google.com/\n"
        "2. Create a project or select an existing one\n"
        "3. Enable the Google Docs API and Google Drive API\n"
        "4. Create OAuth2 credentials (Desktop application)\n"
        "5. Download the credentials JSON file"
    )

    creds_path = Prompt.ask(
        "Path to Google credentials JSON file",
        default="credentials.json",
    )
    config_values["GOOGLE_CREDENTIALS_FILE"] = creds_path

    # Optional: Drive folder
    console.print("\n[bold]3. Google Drive Folder (Optional)[/bold]")
    if Confirm.ask("Do you want to save articles to a specific folder?", default=False):
        folder_id = Prompt.ask(
            "Enter the Google Drive folder ID\n"
            "(The ID is in the folder URL: drive.google.com/drive/folders/[FOLDER_ID])"
        )
        config_values["GOOGLE_DRIVE_FOLDER_ID"] = folder_id

    # Article settings
    console.print("\n[bold]4. Article Settings[/bold]")
    min_words = Prompt.ask("Minimum article word count", default="800")
    max_words = Prompt.ask("Maximum article word count", default="2000")
    config_values["ARTICLE_MIN_WORDS"] = min_words
    config_values["ARTICLE_MAX_WORDS"] = max_words

    # Write .env file
    env_content = "\n".join(f"{k}={v}" for k, v in config_values.items())
    env_file.write_text(env_content + "\n")

    console.print(f"\n[green]Configuration saved to {env_file}[/green]")
    console.print("\nNext steps:")
    console.print("1. Run [cyan]article-gen auth[/cyan] to authenticate with Google")
    console.print("2. Run [cyan]article-gen generate \"Your Topic\"[/cyan] to create an article")


@app.command()
def auth():
    """Authenticate with Google APIs."""
    config = get_config()

    if not config.anthropic_api_key:
        console.print("[red]Please run 'article-gen setup' first.[/red]")
        raise typer.Exit(1)

    console.print("Authenticating with Google APIs...")
    console.print("A browser window will open for authentication.\n")

    try:
        client = GoogleDocsClient(
            credentials_file=config.google_credentials_file,
            token_file=config.google_token_file,
            folder_id=config.google_drive_folder_id or None,
        )
        client.authenticate()
        console.print("[green]Successfully authenticated with Google![/green]")
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Authentication failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def generate(
    topic: str = typer.Argument(..., help="The topic for the education article"),
    audience: str = typer.Option(
        "educators and teachers",
        "--audience",
        "-a",
        help="Target audience for the article",
    ),
    article_type: str = typer.Option(
        "informative",
        "--type",
        "-t",
        help="Article type: informative, how-to, analysis, opinion",
    ),
    max_sources: int = typer.Option(
        5,
        "--sources",
        "-s",
        help="Maximum number of research sources to use",
    ),
    skip_research: bool = typer.Option(
        False,
        "--skip-research",
        help="Skip web research and generate from topic only",
    ),
    save_local: Path = typer.Option(
        None,
        "--save-local",
        "-o",
        help="Save article to a local file instead of Google Docs",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Generate article but don't save anywhere",
    ),
):
    """Generate an education article on a topic."""
    config = get_config()

    # Validate config
    if not config.anthropic_api_key:
        console.print("[red]Missing Anthropic API key. Run 'article-gen setup' first.[/red]")
        raise typer.Exit(1)

    console.print(Panel(f"Generating Article: {topic}", style="bold blue"))

    # Research phase
    research_results = []
    if not skip_research:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Researching topic...", total=None)

            researcher = WebResearcher(max_sources=max_sources)

            # Generate additional research queries
            queries = [
                f"{topic} education",
                f"{topic} teaching strategies",
                f"{topic} classroom",
            ]

            research_results = asyncio.run(
                researcher.research_topic(topic, queries[:2])
            )

            progress.update(task, description="Research complete!")

        # Show research summary
        total_sources = sum(len(r.sources) for r in research_results)
        console.print(f"\nFound [green]{total_sources}[/green] sources")
    else:
        console.print("[yellow]Skipping research phase[/yellow]")

    # Generate article
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Writing article...", total=None)

        writer = AIArticleWriter(
            api_key=config.anthropic_api_key,
            model=config.default_model,
            min_words=config.article_min_words,
            max_words=config.article_max_words,
        )

        progress.update(task, description="Generating outline...")
        article = writer.write_article(
            topic=topic,
            research_results=research_results,
        )

        progress.update(task, description="Article complete!")

    # Display article preview
    console.print("\n")
    console.print(Panel(f"[bold]{article.title}[/bold]\n\nWord count: {article.word_count}"))

    # Show first 500 chars as preview
    preview = article.content[:500] + "..." if len(article.content) > 500 else article.content
    console.print(preview)
    console.print("\n")

    if dry_run:
        console.print("[yellow]Dry run - article not saved[/yellow]")
        return

    # Save article
    if save_local:
        # Save to local file
        content = article.content
        if config.include_sources and article.sources:
            content += "\n\n## Sources\n\n"
            for source in article.sources:
                content += f"- {source}\n"

        save_local.write_text(content)
        console.print(f"[green]Article saved to {save_local}[/green]")
    else:
        # Save to Google Docs
        if not config.google_credentials_file.exists():
            console.print(
                "[red]Google credentials not found. "
                "Use --save-local or run 'article-gen setup'[/red]"
            )
            raise typer.Exit(1)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Saving to Google Docs...", total=None)

            try:
                docs_client = GoogleDocsClient(
                    credentials_file=config.google_credentials_file,
                    token_file=config.google_token_file,
                    folder_id=config.google_drive_folder_id or None,
                )
                docs_client.authenticate()

                # Prepare content with sources
                content = article.content
                if config.include_sources and article.sources:
                    content += "\n\n## Sources\n\n"
                    for source in article.sources:
                        content += f"- {source}\n"

                result = docs_client.create_document(article.title, content)

                progress.update(task, description="Saved!")

                console.print(f"\n[green]Article saved to Google Docs![/green]")
                console.print(f"[link={result.doc_url}]{result.doc_url}[/link]")

            except Exception as e:
                console.print(f"[red]Failed to save to Google Docs: {e}[/red]")
                raise typer.Exit(1)


@app.command()
def research(
    topic: str = typer.Argument(..., help="The topic to research"),
    max_sources: int = typer.Option(
        5,
        "--sources",
        "-s",
        help="Maximum number of sources to fetch",
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Save research to a file",
    ),
):
    """Research a topic without generating an article."""
    console.print(Panel(f"Researching: {topic}", style="bold blue"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Searching...", total=None)

        researcher = WebResearcher(max_sources=max_sources)
        results = asyncio.run(researcher.research_topic(topic))

        progress.update(task, description="Research complete!")

    # Display results
    for result in results:
        console.print(f"\n[bold]Query: {result.query}[/bold]")

        if result.error:
            console.print(f"[red]Error: {result.error}[/red]")
            continue

        table = Table(show_header=True, header_style="bold")
        table.add_column("Source", style="cyan", no_wrap=True)
        table.add_column("Title")
        table.add_column("Content Length")

        for source in result.sources:
            table.add_row(
                source.url[:50] + "..." if len(source.url) > 50 else source.url,
                source.title[:40] + "..." if len(source.title) > 40 else source.title,
                f"{len(source.content)} chars",
            )

        console.print(table)

    if output:
        content = "\n\n".join(r.to_context() for r in results)
        output.write_text(content)
        console.print(f"\n[green]Research saved to {output}[/green]")


@app.command()
def list_docs(
    limit: int = typer.Option(10, "--limit", "-l", help="Number of documents to list"),
):
    """List recent documents created by this application."""
    config = get_config()

    if not config.google_credentials_file.exists():
        console.print("[red]Google credentials not found. Run 'article-gen setup' first.[/red]")
        raise typer.Exit(1)

    try:
        docs_client = GoogleDocsClient(
            credentials_file=config.google_credentials_file,
            token_file=config.google_token_file,
        )
        docs_client.authenticate()

        documents = docs_client.list_recent_documents(limit=limit)

        if not documents:
            console.print("No documents found.")
            return

        table = Table(title="Recent Documents", show_header=True, header_style="bold")
        table.add_column("Title", style="cyan")
        table.add_column("Created")
        table.add_column("Link")

        for doc in documents:
            table.add_row(
                doc["name"],
                doc.get("createdTime", "")[:10],
                doc.get("webViewLink", ""),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def version():
    """Show version information."""
    from . import __version__

    console.print(f"AI Article Generator v{__version__}")


if __name__ == "__main__":
    app()
