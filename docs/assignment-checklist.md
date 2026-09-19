# Task 3 submission checklist

This checklist maps each requirement from the supplied Task 3 brief to its implementation
and verification evidence.

| Requirement | Implementation | Verification |
|---|---|---|
| Clean repository and configuration | `app/`, `config/`, `data/`, `models/`, `notebooks/`, `src/`, `tests/`, split pinned requirements, environment interpolation | `ruff check .`; `ruff format --check .` |
| Refactored, parity-safe inference | `features.py`, `model.py`; fitted Task 2 preprocessor and classifier are loaded and never refitted | `tests/test_features.py`; exact probability parity in `tests/test_model.py` |
| Logging and error handling | Console plus rotating file logging; accepted and rejected requests record input, output/error, latency, and version | API integration tests; `storage.py`; `logging_utils.py` |
| DVC and Great Expectations | `data/raw.dvc`, `artifacts.dvc`, credential-free MinIO remote, GX ranges/categories/null rules, reject policy | `dvc status`; `tests/test_data_contract.py`; `tests/test_validation.py` |
| MLflow tracking and registry | Parameters, metrics, evidence and packaged model are logged; version gets `Production` tag and `champion` alias | Local SQLite registry smoke test; Compose uses PostgreSQL plus MinIO |
| Automated tests | Unit, data, model parity and API integration coverage | `scripts/test.ps1`; 16 tests |
| FastAPI service | Health, model metadata, single prediction, batch prediction, typed schemas and OpenAPI docs | `tests/test_api.py`; `/docs` |
| Docker and Compose | Small API image; PostgreSQL, MinIO, MLflow, registration job, API and Prometheus services | `docker compose --env-file .env.example config --quiet`; `RUN_TASK3.bat` |
| CI/CD and pre-commit | Ruff, formatting, tests and coverage gate image build; main pushes to GHCR | `.github/workflows/ci.yml`; `.pre-commit-config.yaml` |
| Monitoring and feedback | Prometheus counts/latency/errors/class distribution/drift, PostgreSQL prediction history, alert rules and ground-truth columns | `/metrics`; `monitoring/alerts.yml`; `docs/monitoring.md` |

The Docker Compose structure was validated on the delivery machine. Building or starting
the containers requires Docker Desktop to be running.
