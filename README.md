# AutoQA

**Automated Quality Assurance for GitHub**

AutoQA is a GitHub Application that revolutionizes the way AI can be used in Quality Assurance. It automatically generates issue checklists, reviews PRs against those checklists, generates unit tests, and creates comprehensive reports.

## Features

- ✅ **Automatic Checklist Generation**: Extracts acceptance criteria from issues and generates structured checklists
- 🔍 **PR Code Review**: Automatically reviews PR code against issue checklists
- 🧪 **Test Generation**: Generates unit test cases based on PR changes and checklist requirements
- 📊 **Compliance Reports**: Creates detailed reports mapping test results to checklist items
- 🤖 **AI-Powered**: Uses LLM (Groq/OpenAI) for intelligent parsing and generation
- 🔄 **CI Integration**: Integrates with GitHub Actions to run generated tests and report results

## Architecture

```
GitHub → Webhook → FastAPI → Services → Database
                           ↓
                      LLM Adapter
                           ↓
                      GitHub API
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis (optional, for background tasks)
- GitHub App credentials

### Installation

1. **Clone the repository**

```bash
git clone <repository-url>
cd autoqa
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Configure environment**

Create a `.env` file:

```env
GITHUB_APP_ID=your_app_id
GITHUB_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
GITHUB_WEBHOOK_SECRET=your_webhook_secret
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/autoqa
LLM_PROVIDER=groq  # or 'none', 'openai'
LLM_API_KEY=your_api_key
AUTO_MERGE_ENABLED=false
```

4. **Setup database**

```bash
# Using Docker Compose
docker-compose up -d postgres

# Run migrations
alembic upgrade head
```

5. **Run the application**

```bash
uvicorn src.app.main:app --reload --port 8000
```

For webhook testing with ngrok:

```bash
./scripts/dev_ngrok.sh
```

## How It Works

### 1. Issue → Checklist

When an issue is opened:
- AutoQA parses the issue description
- Extracts acceptance criteria (heuristic + LLM)
- Generates a structured checklist
- Posts the checklist as a comment on the issue
- Stores the checklist in the database

### 2. PR → Test Manifest

When a PR is opened:
- AutoQA finds the linked issue
- Fetches the PR diff and changed files
- Generates a test manifest mapping tests to checklist items
- Stores the manifest in the database

### 3. CI → Report

When a CI workflow completes:
- AutoQA downloads test artifacts (JUnit XML)
- Parses test results
- Maps test results to checklist items
- Generates a compliance report
- Posts the report as a PR comment

## Configuration

### GitHub App Setup

1. Create a GitHub App (see [docs/github_permissions.md](docs/github_permissions.md))
2. Set webhook URL to your deployment URL
3. Configure permissions:
   - Issues: Read & Write
   - Pull Requests: Read & Write
   - Checks: Write
   - Actions: Read
   - Contents: Read
4. Install the app on your repositories

### LLM Configuration

Set `LLM_PROVIDER` to:
- `none`: Use heuristic parsing only (no API calls)
- `groq`: Use Groq API (requires `LLM_API_KEY`)
- `openai`: Use OpenAI API (requires `LLM_API_KEY`)

## Development

See [docs/dev_setup.md](docs/dev_setup.md) for detailed development setup instructions.

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/
ruff check src/
```

## Deployment

### Render

The project includes a `render.yaml` for easy deployment on Render. See [Render Deployment Guide](docs/render_deployment.md) for detailed instructions.

Quick steps:
1. Connect your GitHub repository to Render
2. Render will detect `render.yaml` and deploy automatically
3. Set environment variables in Render dashboard
4. Configure GitHub App webhook URL (see [Webhook Setup Guide](docs/webhook_setup.md))

### Docker

```bash
docker build -t autoqa .
docker run -p 8000:8000 --env-file .env autoqa
```

## Documentation

- [Development Setup](docs/dev_setup.md)
- [Render Deployment](docs/render_deployment.md)
- [Webhook Setup](docs/webhook_setup.md)
- [GitHub Permissions](docs/github_permissions.md)
- [CI Contract](docs/ci_contract.md)
- [Runbook](docs/runbook.md)

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues and questions, please open an issue on GitHub.

