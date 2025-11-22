# Development Setup Guide

## Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis (optional, for background tasks)
- GitHub App credentials
- ngrok or similar tunneling tool for local webhook testing

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd autoqa
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables

Create a `.env` file in the project root:

```env
GITHUB_APP_ID=12345
GITHUB_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/autoqa
REDIS_URL=redis://localhost:6379/0
LLM_PROVIDER=none
LLM_API_KEY=
AUTO_MERGE_ENABLED=false
PORT=8000
DEBUG=true
```

### 5. Setup Database

#### Option A: Docker Compose (Recommended)

```bash
docker-compose up -d postgres redis
```

Wait for services to be healthy, then run migrations:

```bash
alembic upgrade head
```

#### Option B: Local PostgreSQL

Create a database:

```sql
CREATE DATABASE autoqa;
```

Run migrations:

```bash
alembic upgrade head
```

## Running the Application

### Development Server

```bash
uvicorn src.app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

### With ngrok (for webhook testing)

1. Start the application:

```bash
uvicorn src.app.main:app --reload --port 8000
```

2. In another terminal, start ngrok:

```bash
ngrok http 8000
```

3. Copy the ngrok HTTPS URL (e.g., `https://abc123.ngrok.io`)

4. Configure GitHub App webhook:
   - Go to your GitHub App settings
   - Set webhook URL to: `https://abc123.ngrok.io/webhooks/github`
   - Set webhook secret to match `GITHUB_WEBHOOK_SECRET` in `.env`
   - Subscribe to events:
     - `issues`
     - `pull_request`
     - `workflow_run`

## GitHub App Setup

### 1. Create a GitHub App

1. Go to GitHub Settings > Developer settings > GitHub Apps
2. Click "New GitHub App"
3. Fill in app details:
   - Name: AutoQA
   - Homepage URL: Your repository URL
   - Webhook URL: Your ngrok URL or production URL
   - Webhook secret: Generate a secret and add to `.env`

### 2. Set Permissions

- **Issues**: Read & Write
- **Pull Requests**: Read & Write
- **Checks**: Write
- **Actions**: Read
- **Contents**: Read (only if pushing test branches)

### 3. Generate Private Key

1. Click "Generate a private key"
2. Download the `.pem` file
3. Copy the key content (including `-----BEGIN PRIVATE KEY-----` and `-----END PRIVATE KEY-----`)
4. Add to `.env` as `GITHUB_PRIVATE_KEY` (use `\n` for newlines in .env)

### 4. Get App ID

1. Note the App ID from the app settings page
2. Add to `.env` as `GITHUB_APP_ID`

### 5. Install the App

1. Click "Install App"
2. Select the repository or organization
3. Note the Installation ID (from webhook payload or API)

## Testing

### Unit Tests

```bash
pytest tests/
```

### Test Webhook Locally

Use the provided script:

```bash
python scripts/generate_sample_webhook.py
```

Or use curl:

```bash
curl -X POST http://localhost:8000/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: issues" \
  -H "X-Hub-Signature-256: sha256=<calculated_signature>" \
  -d @test_webhook_payload.json
```

### Manual Testing

1. Create a test issue with acceptance criteria in a repository where the app is installed
2. Check that a checklist comment is posted
3. Create a PR referencing the issue
4. Check that test manifest is generated
5. Trigger a workflow run that produces JUnit XML
6. Verify that compliance report is posted

## Database Migrations

### Create Migration

```bash
alembic revision --autogenerate -m "Description"
```

### Apply Migrations

```bash
alembic upgrade head
```

### Rollback Migration

```bash
alembic downgrade -1
```

## Development Workflow

1. Make changes to code
2. Run tests: `pytest`
3. Run linter: `ruff check src/`
4. Format code: `black src/`
5. Commit changes
6. Push to repository

## Troubleshooting

### Database Connection Issues

- Check `DATABASE_URL` is correct
- Ensure PostgreSQL is running
- Check firewall/network settings

### GitHub API Errors

- Verify `GITHUB_APP_ID` and `GITHUB_PRIVATE_KEY` are correct
- Check app permissions are set correctly
- Verify app is installed on the repository

### Webhook Verification Fails

- Ensure `GITHUB_WEBHOOK_SECRET` matches the webhook secret in GitHub App settings
- Check that request body is not being modified (e.g., by middleware)
- Verify signature calculation matches GitHub's implementation

### LLM Provider Issues

- If using Groq: Verify API key is set in `LLM_API_KEY`
- Check provider name matches: `none`, `groq`, or `openai`
- Verify API quota/limits if requests fail

## Next Steps

- Review [GitHub Permissions Guide](github_permissions.md)
- Review [CI Contract](ci_contract.md)
- Check [Runbook](runbook.md) for operational procedures

