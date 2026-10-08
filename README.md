# Resume.ai - HelloFOSS

**Rizzume** is an AI-assisted resume reviewer developed by the AI Community at IIT Bombay. It parses uploaded resumes, classifies career domains, scores projects/work experience/achievements/layout, and produces improvement suggestions.

## HelloFOSS
See [HELLOFOSS.md](HELLOFOSS.md) for the ten reviewed contribution topics and [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow.

## Stack
Python, FastAPI, SQLAlchemy, PostgreSQL, PyTorch/Transformers, Gemini/Cerebras clients, Azure Blob Storage, Next.js, React, TypeScript, Docker, optional Redis.

## Release contents
This is a standalone, fresh-history snapshot of the original AI Community project, not a fork containing the original commit graph. Original development attribution remains with the AI Community at IIT Bombay and the upstream contributors.

Numeric layout features, aggregate statistics and the two reviewed numeric layout-model artifacts are retained. Original document filenames/student identifiers have been removed from numeric fixtures. Personal resume screenshots, resume-derived project-text datasets and personal demo samples are not distributed. No credential values or runtime account databases are included.

## Setup
1. Install Docker Desktop, Python 3.12 and Node.js compatible with the frontend lockfile.
2. Copy `.env.example` to an **untracked** `.env` and supply your own private values. All database URLs, signing secrets, provider keys and storage/email values are blank in the template. Do not copy production credentials into a contribution.
3. Supply separately approved classifier files (weights, tokenizer, label mappings) using `CLASSIFIER_MODEL_PATH`. Docker no longer downloads the original opaque model archive. Mount your reviewed assets as runtime configuration, outside the repository and build context.
4. Configure the main/project/work-experience/POR databases and Azure storage integrations. Never commit those databases or stored vectors derived from new uploads.
5. Build with `docker compose build`. The inherited Compose configuration exposes services on its internal network; add a development override with a localhost-bound frontend port before browser use.

Full deployment needs those external integrations and approved classifier assets. A complete live-provider application startup was not exercised during this release preparation; the contributor setup improvements are an explicit HelloFOSS task.

## Local checks
```bash
python tools/check_release.py .
python -m unittest discover -s tools/tests -v
```
These checks use standard-library tests, numeric fixture validation and source checks without real provider calls. For independent credential checks, run Gitleaks with `.gitleaks.toml`, 100% redaction and `--log-opts=--all` before publishing changes.

## Runtime data
Keep `.env`, uploads, account databases, cloud credentials and private model sources outside Git. Configuration/public OAuth client IDs are not substitutes for a private signing key. Production deployments should disable sensitive logging and review access controls.

## Licensing
No repository license was present in the reviewed upstream snapshot. The maintainers need to choose and document the intended license; this release does not invent a license for upstream code or retained artifacts.
