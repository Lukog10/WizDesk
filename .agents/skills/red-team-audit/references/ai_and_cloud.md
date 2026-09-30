# AI, Cloud, and Supply Chain Attack Surfaces

This reference defines attack vectors for AI/LLM systems, agentic architectures, cloud deployments, and software supply chains.

## 1. LLM, Prompt Injection, and Agentic Pipelines
- Direct Prompt Injection: search for untrusted user inputs concatenated directly into system instructions without delimiter fences or schema isolation.
- Indirect Prompt Injection: audit RAG pipelines, web scrapers, email parsers, and document converters that feed external content into prompts.
- Tool-calling and Action Gates:
  - Audit function calling tools: any tool that mutates state, executes code, writes to databases, or transfers funds must require human confirmation or strict authorization checks.
  - Parameter tampering: ensure tools validate arguments against strict types and bounds; do not trust model-generated arguments.
- Model Context Protocol (MCP) Servers:
  - Audit scopes granted to MCP servers: flag arbitrary filesystem write access, uncontrolled shell execution, or unrestricted network egress.
  - Verify origin and integrity of installed MCP packages.

## 2. Cloud and Infrastructure Security
- Cloud storage buckets: inspect S3, GCS, or Azure Blob storage definitions; ensure public access blocks are enforced and objects are private by default.
- IAM and Service Accounts: verify least-privilege policies; ensure cloud credentials are not baked into container images or repository manifests.
- Serverless and Edge: audit cold start handlers and shared state for data leakage between distinct tenant invocations.

## 3. Supply Chain and Dependencies
- Audit package manifests (`package.json`, `pyproject.toml`, `requirements.txt`, `Cargo.toml`, `go.mod`):
  - Check for typosquatting packages (misspellings of popular libraries).
  - Verify unpinned dependencies: flag bare `>=` or wildcard versions that can pull malicious upstream releases.
  - Require lockfiles (`package-lock.json`, `requirements.lock`, `Cargo.lock`) and enforce cryptographic hash checking (`--require-hashes`).
- Inspect install hooks and lifecycle scripts (`postinstall`, `build.rs`, `setup.py`): verify third-party packages do not execute unauthorized shell scripts during installation.

## 4. Logging, Error Exposure, and Telemetry
- Inspect logging statements (`console.log`, `logging.info`, `logger.debug`): verify raw request payloads, auth tokens, passwords, private keys, and user PII are never recorded.
- Audit error handlers: ensure production error responses do not leak internal stack traces, database schema details, or environment variables to clients.
- Verify exclusion of sensitive files in builds: ensure `.env`, `.git`, `.DS_Store`, and internal documentation are excluded from production artifacts.
