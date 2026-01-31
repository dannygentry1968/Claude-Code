"""FastAPI web interface for the AI Article Generator."""

import asyncio
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, Form, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .ai_writer import AIArticleWriter, GeneratedArticle
from .config import Config, get_config
from .google_docs import GoogleDocsClient, GoogleDocResult
from .research import WebResearcher, ResearchResult

# Create FastAPI app
app = FastAPI(
    title="AI Article Generator",
    description="Generate education articles with AI and save to Google Docs",
    version="0.1.0",
)

# Templates directory
TEMPLATES_DIR = Path(__file__).parent / "templates"
TEMPLATES_DIR.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# In-memory job storage (for production, use Redis or a database)
jobs: dict[str, dict] = {}


def get_google_client(config: Config) -> GoogleDocsClient:
    """Get authenticated Google Docs client."""
    client = GoogleDocsClient(
        credentials_file=config.google_credentials_file,
        token_file=config.google_token_file,
        folder_id=config.google_drive_folder_id or None,
    )
    client.authenticate()
    return client


async def generate_article_task(
    job_id: str,
    topic: str,
    audience: str,
    article_type: str,
    max_sources: int,
    skip_research: bool,
    config: Config,
):
    """Background task to generate an article."""
    try:
        jobs[job_id]["status"] = "researching"
        jobs[job_id]["message"] = "Researching topic..."

        research_results: list[ResearchResult] = []

        if not skip_research:
            researcher = WebResearcher(max_sources=max_sources)
            queries = [
                f"{topic} education",
                f"{topic} teaching strategies",
            ]
            research_results = await researcher.research_topic(topic, queries[:1])

            total_sources = sum(len(r.sources) for r in research_results)
            jobs[job_id]["message"] = f"Found {total_sources} sources. Writing article..."

        jobs[job_id]["status"] = "writing"
        jobs[job_id]["message"] = "AI is writing the article..."

        writer = AIArticleWriter(
            api_key=config.anthropic_api_key,
            model=config.default_model,
            min_words=config.article_min_words,
            max_words=config.article_max_words,
        )

        article = writer.write_article(
            topic=topic,
            research_results=research_results,
        )

        jobs[job_id]["status"] = "saving"
        jobs[job_id]["message"] = "Saving to Google Docs..."

        # Save to Google Docs
        docs_client = get_google_client(config)

        content = article.content
        if config.include_sources and article.sources:
            content += "\n\n## Sources\n\n"
            for source in article.sources:
                content += f"- {source}\n"

        result = docs_client.create_document(article.title, content)

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["message"] = "Article created successfully!"
        jobs[job_id]["result"] = {
            "title": article.title,
            "word_count": article.word_count,
            "doc_url": result.doc_url,
            "doc_id": result.doc_id,
            "sources_count": len(article.sources),
        }

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["message"] = str(e)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with article generation form."""
    config = get_config()

    # Check configuration status
    config_errors = config.validate()
    google_authenticated = config.google_token_file.exists()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "config_errors": config_errors,
            "google_authenticated": google_authenticated,
            "recent_jobs": list(jobs.values())[-5:],
        },
    )


@app.post("/generate")
async def generate_article(
    background_tasks: BackgroundTasks,
    topic: str = Form(...),
    audience: str = Form("educators and teachers"),
    article_type: str = Form("informative"),
    max_sources: int = Form(5),
    skip_research: bool = Form(False),
):
    """Start article generation."""
    config = get_config()

    # Validate config
    errors = config.validate()
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    # Create job
    job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(jobs)}"
    jobs[job_id] = {
        "id": job_id,
        "topic": topic,
        "status": "pending",
        "message": "Starting...",
        "created_at": datetime.now().isoformat(),
        "result": None,
    }

    # Start background task
    background_tasks.add_task(
        generate_article_task,
        job_id,
        topic,
        audience,
        article_type,
        max_sources,
        skip_research,
        config,
    )

    return RedirectResponse(url=f"/job/{job_id}", status_code=303)


@app.get("/job/{job_id}", response_class=HTMLResponse)
async def job_status(request: Request, job_id: str):
    """Job status page."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return templates.TemplateResponse(
        "job.html",
        {
            "request": request,
            "job": jobs[job_id],
        },
    )


@app.get("/api/job/{job_id}")
async def job_status_api(job_id: str):
    """Job status API endpoint for polling."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@app.get("/history", response_class=HTMLResponse)
async def history(request: Request):
    """View generation history."""
    sorted_jobs = sorted(
        jobs.values(),
        key=lambda x: x.get("created_at", ""),
        reverse=True,
    )
    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "jobs": sorted_jobs,
        },
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    config = get_config()
    return {
        "status": "healthy",
        "config_valid": len(config.validate()) == 0,
        "google_authenticated": config.google_token_file.exists(),
    }


def create_app() -> FastAPI:
    """Create and configure the FastAPI app."""
    # Create templates directory if it doesn't exist
    TEMPLATES_DIR.mkdir(exist_ok=True)
    return app
