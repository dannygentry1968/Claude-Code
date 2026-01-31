# AI Article Generator

An AI-powered tool for researching and generating education articles, with automatic saving to Google Docs.

## Features

- **Web Research**: Automatically researches your topic using web search
- **AI Writing**: Uses Claude AI to draft well-structured education articles
- **Google Docs Integration**: Saves articles directly to Google Drive as Google Docs
- **Customizable**: Configure article length, style, target audience, and more
- **Source Citations**: Automatically includes research sources in articles

## Installation

### Prerequisites

- Python 3.11 or higher
- An Anthropic API key ([get one here](https://console.anthropic.com/))
- Google Cloud project with Docs and Drive APIs enabled

### Install from source

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-article-generator.git
cd ai-article-generator

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install -e .
```

## Setup

### 1. Configure API Keys

Run the interactive setup wizard:

```bash
article-gen setup
```

Or manually create a `.env` file:

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 2. Set up Google Cloud

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Google Docs API
   - Google Drive API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
5. Select "Desktop application" as the application type
6. Download the credentials JSON file
7. Save it as `credentials.json` in your project directory

### 3. Authenticate with Google

```bash
article-gen auth
```

This will open a browser window for you to authorize the application.

## Usage

### Generate an Article

```bash
# Basic usage - generates and saves to Google Docs
article-gen generate "Benefits of Project-Based Learning"

# Specify target audience
article-gen generate "Classroom Management Strategies" --audience "new teachers"

# Choose article type
article-gen generate "STEM Education Trends" --type "analysis"

# Save to local file instead of Google Docs
article-gen generate "Digital Literacy" --save-local article.md

# Preview without saving (dry run)
article-gen generate "Inclusive Education" --dry-run

# Skip research phase (generate from AI knowledge only)
article-gen generate "Homework Best Practices" --skip-research
```

### Research Only

Research a topic without generating an article:

```bash
# Basic research
article-gen research "Gamification in Education"

# Save research to file
article-gen research "SEL Programs" --output research.txt

# Limit number of sources
article-gen research "Differentiated Instruction" --sources 3
```

### List Recent Documents

```bash
# List your recent Google Docs
article-gen list-docs

# Limit results
article-gen list-docs --limit 5
```

## Command Reference

| Command | Description |
|---------|-------------|
| `setup` | Interactive configuration wizard |
| `auth` | Authenticate with Google APIs |
| `generate` | Research and generate an article |
| `research` | Research a topic (no article generation) |
| `list-docs` | List recent Google Docs |
| `version` | Show version information |

### Generate Options

| Option | Short | Description |
|--------|-------|-------------|
| `--audience` | `-a` | Target audience (default: "educators and teachers") |
| `--type` | `-t` | Article type: informative, how-to, analysis, opinion |
| `--sources` | `-s` | Max research sources (default: 5) |
| `--skip-research` | | Generate without web research |
| `--save-local` | `-o` | Save to local file instead of Google Docs |
| `--dry-run` | | Preview article without saving |

## Configuration

Environment variables (set in `.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key | Required |
| `ANTHROPIC_MODEL` | Claude model to use | `claude-sonnet-4-20250514` |
| `GOOGLE_CREDENTIALS_FILE` | Path to OAuth credentials | `credentials.json` |
| `GOOGLE_TOKEN_FILE` | Path to store auth token | `token.json` |
| `GOOGLE_DRIVE_FOLDER_ID` | Folder to save articles | Root Drive |
| `ARTICLE_MIN_WORDS` | Minimum article length | 800 |
| `ARTICLE_MAX_WORDS` | Maximum article length | 2000 |
| `MAX_RESEARCH_SOURCES` | Sources per research query | 5 |

## Examples

### Generate a How-To Article

```bash
article-gen generate "How to Implement Flipped Classroom" \
  --type "how-to" \
  --audience "high school teachers" \
  --sources 8
```

### Quick Article (No Research)

```bash
article-gen generate "Importance of Reading Aloud" \
  --skip-research \
  --save-local quick-article.md
```

### Research and Review Before Generating

```bash
# First, research the topic
article-gen research "Assessment Strategies" --output research.txt

# Review research.txt, then generate
article-gen generate "Assessment Strategies"
```

## Development

### Install dev dependencies

```bash
pip install -e ".[dev]"
```

### Run tests

```bash
pytest
```

### Format code

```bash
black src/
ruff check src/ --fix
```

## License

MIT License - see LICENSE file for details.
