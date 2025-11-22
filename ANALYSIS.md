Nice — below is a **developer-ready implementation script / spec** for the AutoQA backend so *Cursor* (or any developer) can build it. It’s a precise, file-by-file plan with function interfaces, data models, deployment files, CI contract, and implementation notes — intentionally detailed but **not** full implementation code. Use it as a blueprint to implement quickly.

# # AutoQA — Implementation Script (developer blueprint)

---

## 1 — High level summary (one line)

Build a FastAPI GitHub App backend that receives GitHub webhooks, generates/ stores issue checklists, generates tests from PR diffs (heuristics first), triggers/consumes CI results, maps results to checklists, posts reports, and optionally auto-merges PRs.

---

## 2 — Project layout (finalized)

```
autoqa/
├── README.md
├── LICENSE
├── .gitignore
├── requirements.txt
├── .env.example
├── render.yaml
├── Dockerfile
├── docker-compose.yml      # for local dev (postgres + redis)
├── infra/
│   └── github_app_manifest.yaml
├── docs/
│   ├── ci_contract.md
│   ├── dev_setup.md
│   ├── github_permissions.md
│   └── runbook.md
├── scripts/
│   ├── dev_ngrok.sh
│   └── generate_sample_webhook.py
├── src/
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── logging_config.py
│       ├── deps.py
│       ├── models/
│       │   ├── base.py
│       │   ├── issue_record.py
│       │   ├── pr_record.py
│       │   └── test_result.py
│       ├── schemas/
│       │   ├── issue.py
│       │   ├── pr.py
│       │   └── report.py
│       ├── api/
│       │   └── webhooks.py
│       ├── services/
│       │   ├── github_service.py
│       │   ├── checklist_service.py
│       │   ├── testgen_service.py
│       │   ├── ci_mapper.py
│       │   └── merge_service.py
│       ├── adapters/
│       │   ├── llm_adapter.py
│       │   ├── db_adapter.py
│       │   └── storage_adapter.py
│       ├── utils/
│       │   ├── parser.py
│       │   ├── diff_utils.py
│       │   └── security.py
│       ├── workers/
│       │   ├── queue.py
│       │   └── tasks.py
│       └── exceptions.py
└── .github/
    └── workflows/
        ├── run-tests-on-pr.yml
        └── scaffolded-ci.yml
```

---

## 3 — Important files & their responsibilities (detailed)

### `src/app/main.py`

* Create and expose `app: FastAPI`.
* Include middleware: request logging, exception handling.
* Register routes from `api.webhooks`.
* Startup / shutdown events:

  * Init DB connection
  * Init GitHub App auth helper
  * Start worker if applicable (or rely on separate worker process)

**Contract:** must expose `app` so Render/uvicorn can import: `uvicorn src.app.main:app --host 0.0.0.0 --port $PORT`

---

### `src/app/config.py`

* Read environment variables via `pydantic-settings` or `python-dotenv`.
* Required envs:

  * `GITHUB_APP_ID`
  * `GITHUB_PRIVATE_KEY` (PEM, multi-line)
  * `GITHUB_WEBHOOK_SECRET`
  * `DATABASE_URL`
  * `REDIS_URL` (if using queue)
  * `LLM_PROVIDER` (`none` / `groq` / `openai`)
  * `LLM_API_KEY`
  * `AUTO_MERGE_ENABLED` (bool)
  * `PORT` (for Render)
* Provide typed `Settings` object.

---

### `src/app/logging_config.py`

* Configure structured logging (timestamp, level, request id).
* Ensure logs go to stdout (Render reads them).

---

### `src/app/api/webhooks.py`

* Single router for GitHub webhooks.
* Endpoint path: **`POST /webhooks/github`**.
* Responsibilities:

  1. Validate HMAC signature (via `utils/security.py`).
  2. Parse `X-GitHub-Event` header and JSON payload.
  3. De-duplicate events (use delivery id or store a short-term cache).
  4. Enqueue or trigger appropriate handlers:

     * `issues` → `services.checklist_service.handle_issue_event(payload)`
     * `pull_request` → `services.testgen_service.handle_pr_event(payload)`
     * `workflow_run` / `check_suite` → `services.ci_mapper.handle_workflow_run(payload)`
* Return 200 quickly (enqueue long tasks).

**Notes:** idempotency: if event already processed, return 200 but log.

---

### `src/app/utils/security.py`

* `verify_github_signature(secret: str, signature_header: str, body: bytes) -> bool`

  * Implementation steps:

    1. Compute HMAC SHA256 of `body` with `secret` (binary).
    2. Compare constant-time with header `sha256=...`.
* `generate_jwt_for_app()` and `get_installation_token(installation_id)` helpers (or in `github/auth.py`).

---

### `src/app/services/github_service.py`

* Async wrapper around GitHub REST API using `httpx` (async) or `gidgethub`.
* Capabilities:

  * `get_installation_token(installation_id) -> str`
  * `get_pr_diff(owner, repo, pr_number) -> str` (unified diff)
  * `get_pr_files(owner, repo, pr_number) -> List[FileMeta]`
  * `post_issue_comment(owner, repo, issue_number, body)`
  * `post_pr_comment(owner, repo, pr_number, body)`
  * `create_check_run(owner, repo, name, head_sha)`
  * `upload_artifact(...)` (if needed)
  * `merge_pr(owner, repo, pr_number, merge_method="squash")`
* Handle rate-limits and retries.

---

### `src/app/services/checklist_service.py` (Interface + behavior)

**Purpose:** Accept an `issue` payload, generate a structured checklist (YAML/JSON), store and publish it.

**Functions:**

* `async def handle_issue_event(event: dict) -> IssueRecord`

  * Steps:

    1. Extract issue body, issue number, repo
    2. Try to parse Acceptance Criteria via `utils.parser.extract_acceptance_criteria(body)`
    3. If LLM enabled, call `adapters.llm_adapter.parse_issue_to_checklist(text)` and merge with heuristics
    4. Normalize checklist: list of items `{id, description, required: bool, tags: []}`
    5. Persist IssueRecord via `adapters.db_adapter.save_issue(record)`
    6. Post a comment on the issue with the checklist YAML and a marker label `autoqa:checked`
    7. Return IssueRecord

**Checklist structure (example):**

```json
[
  {"id": "C1", "description":"Add validation for email field", "required": true},
  {"id": "C2", "description":"Add unit tests for signup", "required": false}
]
```

---

### `src/app/services/testgen_service.py`

**Purpose:** For PR events, fetch PR diff, obtain linked issue checklist, produce test manifests or test files (heuristics), and trigger CI run.

**Functions:**

* `async def handle_pr_event(event: dict) -> PRRecord`

  * Steps:

    1. Extract PR metadata: number, head_sha, body, installation_id, repo
    2. Determine related issue number (parse PR body for `#123`, GitHub linked issue, or branch name)

       * Put logic in `utils.parser.find_linked_issue(pr_body, pr_labels, commit_message, branch_name)`
    3. Fetch PR diff and changed file list via `github_service.get_pr_files(...)`
    4. Fetch checklist from DB or issue comment
    5. Generate a **test manifest** object using `testgen_service.generate_test_manifest(diff, checklist)`

       * **Manifest entries**: `{test_id, test_name, target_file, framework, template_id, checklist_ids}`
    6. Store PRRecord with manifest
    7. Trigger GitHub Action via:

       * Option A: `github_service.trigger_workflow_dispatch(repo, workflow_id, inputs={"manifest": manifest_url_or_embedded})`
       * Option B: Push test files to a `autoqa-tests/<pr>` branch (less preferred)
    8. Return PRRecord

* `generate_test_manifest` (algorithmic description):

  * For each changed file:

    * If file is `.py` → propose pytest stub with name `test_<module>_<function>_autoqa`
    * Map functions / changed lines to test targets using `utils.diff_utils.extract_changed_symbols(diff)`
  * For each checklist item that mentions keywords (e.g., "email", "validation") associate tests to checklist IDs.

**Manifest format (JSON)**

```json
{
  "pr_number": 12,
  "head_sha": "abcd1234",
  "tests": [
    {"test_id":"T1","name":"test_signup_email_validation","framework":"pytest","target":"src/auth.py","checklist":["C1"]}
  ]
}
```

---

### `src/app/services/ci_mapper.py`

**Purpose:** Receive CI workflow_run/check_suite events, download test reports, parse them, map test results to checklist items, compute compliance score, and post report as PR comment.

**Functions:**

* `async def handle_workflow_run(event: dict) -> ReportResult`

  * Steps:

    1. Extract run id, artifact URLs, head_sha, repo, pr_number
    2. Download artifacts (JUnit XML or JSON) using GitHub API
    3. Parse test results via `utils.junit_parser.parse_junit(xml_bytes)` → list of test results
    4. Map tests to manifest entries stored in DB; then map test results to checklist items
    5. Compute compliance: number of required checklist items passed / total required
    6. Persist TestResult rows and Report
    7. Post a PR comment summarizing:

       * Checklist table with checkboxes, pass/fail
       * Links to logs/artifacts
       * Next steps for maintainers
    8. If `AUTO_MERGE_ENABLED` and all required items pass → call `merge_service.attempt_merge(pr)`

**Mapping rule examples:**

* match test name to manifest test name
* if test or manifest contains explicit checklist IDs, use them
* fallback: fuzzy match test name <> checklist description keywords

---

### `src/app/services/merge_service.py`

**Purpose:** Safe auto-merge based on policy.

**Functions:**

* `async def attempt_merge(pr_record: PRRecord) -> MergeResult`

  * Steps:

    1. Check repo branch protection via `github_service.get_branch_protection(...)`
    2. Ensure required checks passed and no outstanding reviews (or configured exemptions)
    3. If OK, call `github_service.merge_pr(...)`
    4. Record audit log

**Important:** Default should be safe: require explicit `AUTO_MERGE_ENABLED=true` per repository or org.

---

### `src/app/adapters/llm_adapter.py`

* Provide interface:

  * `async def parse_issue_to_checklist(text: str) -> List[ChecklistItem]`
  * `async def generate_tests_from_diff(diff_text: str, checklist: List) -> Manifest`
  * `async def generate_report_summary(...) -> str`
* Implementation notes:

  * Provide provider-agnostic interface. Implement `GroqClient` or `OpenAIClient` behind it.
  * Cache outputs for identical inputs (to avoid repeat cost).

---

### `src/app/adapters/db_adapter.py`

* `async def save_issue(issue_record: IssueRecord) -> IssueRecord`
* `async def get_issue_by_repo_and_number(repo, number) -> IssueRecord`
* `async def save_pr(pr_record) -> PRRecord`
* `async def save_test_results(list_of_results)`
* Should wrap SQLAlchemy async session; keep SQL isolated.

---

### `src/app/utils/parser.py`

* `extract_acceptance_criteria(issue_body: str) -> List[str]`
  Implementation: parse markdown sections, `Acceptance Criteria` header, bullet detection, regex capture.
* `find_linked_issue(pr_body, labels, branch_name, commits) -> Optional[int]`
  Implementation: regex for `#\d+`, check `linked_issues` via GitHub GraphQL if needed.

---

### `src/app/utils/diff_utils.py`

* `extract_changed_symbols(diff_text: str) -> List[SymbolChange]`

  * Use line ranges and simple regex to find `def ` / `class ` or function names in many languages.
* `get_changed_file_types(file_list) -> Dict[file, type]`

---

### `src/app/utils/junit_parser.py`

* `parse_junit(xml_bytes) -> List[TestResultModel]`

  * Use `xml.etree` or `defusedxml` to parse safely.
  * Normalize statuses: `passed/failed/skipped`, durations, and failure messages.

---

### `src/app/workers/queue.py` & `tasks.py`

* Implement a small worker:

  * Option A (recommended): use Redis + RQ for simple background jobs.
  * Option B: use `async background tasks` via FastAPI `BackgroundTasks` for small loads.
* `tasks.py` functions:

  * `task_generate_checklist(issue_payload)`
  * `task_generate_tests(pr_payload)`
  * `task_process_workflow_run(workflow_payload)`
* Run worker as separate process in production (e.g., `uvicorn` for API, `rq worker` for tasks).

---

## 4 — Database schema (Postgres SQL — simplified)

```sql
CREATE TABLE issues (
  id SERIAL PRIMARY KEY,
  repo TEXT NOT NULL,
  issue_number INTEGER NOT NULL,
  checklist JSONB NOT NULL,
  status TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE pull_requests (
  id SERIAL PRIMARY KEY,
  repo TEXT NOT NULL,
  pr_number INTEGER NOT NULL,
  issue_id INTEGER REFERENCES issues(id),
  head_sha TEXT,
  test_manifest JSONB,
  validation_status TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE test_results (
  id SERIAL PRIMARY KEY,
  pr_id INTEGER REFERENCES pull_requests(id),
  test_id TEXT,
  name TEXT,
  status TEXT,
  log_url TEXT,
  checklist_ids JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE reports (
  id SERIAL PRIMARY KEY,
  pr_id INTEGER REFERENCES pull_requests(id),
  report_content TEXT,
  summary TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

Add indices on repo/pr_number and repo/issue_number.

---

## 5 — CI contract (docs/ci_contract.md) — exact expectations

* GitHub Action that runs generated tests must produce artifact `autoqa-test-report.xml` in JUnit XML format in workflow artifacts root.
* Artifact path: `artifacts/autoqa/autoqa-test-report.xml`
* If using multiple frameworks, normalize outputs to a single JUnit XML (or JSON) with fields:

  * `<testsuite name="autoqa" tests="N" failures="F" time="T">`
  * Each `<testcase classname="..." name="testname">` and `<failure>` if failing.
* The `ci_mapper` will fetch the artifact using the Actions API and parse it.

---

## 6 — requirements.txt (recommended)

```
fastapi>=0.95
uvicorn[standard]>=0.22
httpx>=0.24
sqlalchemy[asyncio]>=2.0
asyncpg>=0.27
alembic>=1.11
pydantic>=2.0
pydantic-settings>=2.0
pyjwt[crypto]>=2.8
cryptography>=40.0
defusedxml>=0.7.1
python-dotenv>=1.0
jinja2>=3.1           # for templating test stubs
aiofiles>=23.1
```

(Optionally for queue/workers)

```
redis>=4.5
rq>=1.2
```

(LLM SDKs optional)

```
groq-sdk>=x.y.z  # replace with actual package name if using Groq
openai>=0.27.0   # if supporting OpenAI
```

---

## 7 — `render.yaml` (example)

```yaml
services:
  - type: web
    name: autoqa-backend
    env: python
    plan: free
    buildCommand: "pip install -r requirements.txt"
    startCommand: "uvicorn src.app.main:app --host 0.0.0.0 --port $PORT"
    envVars:
      - key: PORT
        value: "10000"
      - key: GITHUB_WEBHOOK_SECRET
        value: "<set in dashboard>"
      - key: DATABASE_URL
        value: "<set in dashboard>"
```

Add additional envVars via Render dashboard for secrets: `GITHUB_APP_ID`, `GITHUB_PRIVATE_KEY`, `LLM_API_KEY`.

---

## 8 — .env.example (for local dev)

```
GITHUB_APP_ID=12345
GITHUB_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
GITHUB_WEBHOOK_SECRET=yourwebhooksecret
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/autoqa
REDIS_URL=redis://localhost:6379/0
LLM_PROVIDER=none
AUTO_MERGE_ENABLED=false
```

---

## 9 — Webhook verification algorithm (exact steps)

1. Obtain header: `X-Hub-Signature-256` (value `sha256=...`) and `X-GitHub-Delivery` (unique id).
2. Compute HMAC-SHA256: `hmac = HMAC(secret, body_bytes, sha256).hexdigest()`
3. Compare: constant-time compare `'sha256=' + hmac` vs header.
4. If mismatch → return 401 and log.

Implement in `utils/security.py` and call at top of `webhooks.py`.

---

## 10 — GitHub App Auth flow (exact steps)

1. Generate JWT for the App:

   * Header: `alg=RS256`
   * Payload: `{iat, exp (<= 10 minutes), iss=GITHUB_APP_ID}`
   * Sign using App private key (PEM) with `pyjwt`.
2. Exchange JWT for installation token:

   * `POST /app/installations/{installation_id}/access_tokens` with JWT auth.
   * Extract `token` and `expires_at`.
3. Use `token` in `Authorization: Bearer <token>` for further API calls.

Wrap caching logic so you reuse token until `expires_at`.

---

## 11 — Testing & local dev

* Use `scripts/dev_ngrok.sh` to run:

  * `uvicorn src.app.main:app --reload --port 8000`
  * `ngrok http 8000` (or Cloudflare tunnel)
* Install GitHub App pointing webhook to ngrok URL.
* Use `scripts/generate_sample_webhook.py` to POST sample payloads.
* Add unit tests for `utils.parser`, `utils.diff_utils`, `ci_mapper`.

---

## 12 — Security & operational notes

* Verify HMAC on every webhook.
* Least privilege GitHub App permissions:

  * Issues: read & write
  * Pull requests: read & write
  * Checks: write
  * Actions: read (if fetching workflow runs)
  * Contents: read (avoid write unless pushing test branches)
* Never commit `GITHUB_PRIVATE_KEY`.
* Log failures and post helpful comments on PRs when processing fails (e.g., “AutoQA failed to parse checklist — please ensure `Acceptance Criteria` present”).

---

## 13 — Prioritized implementation steps (sprint plan)

1. Project scaffold + `requirements.txt`, Dockerfile, `render.yaml`.
2. Implement `main.py` + `webhooks.py` + HMAC verification.
3. Implement `github_service.get_installation_token` and basic API wrappers.
4. Implement `checklist_service` heuristic parser + DB save + issue comment.
5. Implement `testgen_service` heuristic manifest generation.
6. Create sample GitHub Actions workflow to run tests and produce JUnit XML.
7. Implement `ci_mapper` to fetch artifacts and post PR report comments.
8. Implement `merge_service` safe merging (flag guarded).
9. Add `llm_adapter` as stub; later add GROQ/OpenAI integration.
10. Add worker process for long-running tasks and production hardening.

---

## 14 — Example developer notes for Cursor (explicit)

* Focus on small incremental runs: implement issue -> checklist end-to-end first (no tests generation). That yields early demo.
* Keep LLM calls behind feature flag `LLM_PROVIDER`. Start with `none`.
* Persist the checklist as both DB JSON and as an issue comment (for transparency).
* Keep the test manifest small and human-readable so maintainers can inspect.
* Make reports concise: checklist as GitHub checkbox list, then a short summary line: `Required items passed: X/Y`.
* Add unit tests for the parser and diff utilities — they’re the most brittle.

---

## 15 — Deliverables for first PR to repo

* `requirements.txt`, `render.yaml`, `.env.example`
* `src/app/main.py` minimal with health check and webhook route (HMAC verification)
* `src/app/services/github_service.py` with `get_installation_token()` and `post_issue_comment()` implemented
* `src/app/services/checklist_service.py` with `handle_issue_event()` using heuristics
* `docs/dev_setup.md` with instructions to run locally using ngrok and install test GitHub App
* Unit tests for `utils/parser.extract_acceptance_criteria`

---
