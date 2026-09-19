# Olist MLOps Task 3 - From Notebooks to Production

This repository turns the frozen outputs of Task 2 into a production-style inference
service. It accepts the information available for a new order and returns `late` or
`on_time`, the probability of late delivery, and the registered model version.

Training remains in the six notebooks. Inference never calls `fit`: it uses the fitted
Notebook 05 preprocessor and the Notebook 06 logistic-regression bundle supplied with the
project. An automated parity test proves that the module output matches the saved notebook
predictions for the same test orders.

## Start the complete stack with one command

Prerequisite: install and start Docker Desktop. Then run:

```powershell
.\RUN_TASK3.bat
```

The launcher copies `.env.example` to the ignored `.env` file if needed, builds the image,
starts every service, waits for health checks, registers the frozen model, assigns the
`champion` alias and `Production` stage tag, and starts the API. Change the classroom
passwords in `.env` before using the stack outside a local demonstration.

| Service | URL | Purpose |
|---|---|---|
| FastAPI | <http://localhost:8000/docs> | Interactive API documentation and examples |
| MLflow | <http://localhost:5000> | Runs, metrics, artifacts, registry version and alias |
| MinIO | <http://localhost:9001> | Container-reachable S3 artifact storage |
| Prometheus | <http://localhost:9090> | Request, latency, error and drift metrics |
| PostgreSQL | `localhost:5432` | MLflow metadata and durable prediction logs |

The equivalent cross-platform command is:

```bash
docker compose --env-file .env.example up -d --build --wait
```

Stop the stack without deleting its data:

```bash
docker compose down
```

## Try the API

Health and model metadata:

```powershell
curl.exe http://localhost:8000/health
curl.exe http://localhost:8000/v1/model
```

Single prediction using the supplied example:

```powershell
curl.exe -X POST http://localhost:8000/v1/predict `
  -H "Content-Type: application/json" `
  --data-binary "@models/seed/example_order.json"
```

The response has this contract:

```json
{
  "request_id": "generated-uuid",
  "order_id": "b3b54427f53d13f6063ef7007bf7d371",
  "prediction": "on_time",
  "probability": 0.5451138144592078,
  "model_version": "1",
  "validation_status": "passed"
}
```

Batch route:

```http
POST /v1/predict/batch
Content-Type: application/json

{"orders": [{...}, {...}]}
```

The maximum batch size is configured by `service.batch_max_size`. FastAPI/Pydantic rejects
wrong or missing fields, and Great Expectations rejects values outside the configured
ranges or allowed categories before the model is called.

## Run from the command line

Create a Python 3.12 environment and install the exact pinned development dependencies:

```powershell
py -3.12 -m venv .venv-task3
.\.venv-task3\Scripts\Activate.ps1
python -m pip install -r requirements/dev.txt
python -m pip install -e . --no-deps
```

Use the local release artifacts for an offline command-line check:

```powershell
$env:MODEL_LOADER = "local"
python -m olist_mlops.cli --file models/seed/example_order.json
```

Production uses `MODEL_LOADER=registry`; the API then resolves
`models:/olist-late-delivery@champion` from MLflow rather than loading a notebook folder.

## Run all checks with one command

After installing the development requirements:

```powershell
.\scripts\test.ps1
```

Or run the same gates individually:

```powershell
$env:MODEL_LOADER = "local"
$env:PREDICTION_STORE_BACKEND = "jsonl"
ruff check .
ruff format --check .
pytest
```

Tests cover feature engineering, allowed missing values, Great Expectations failures,
schema/range/category/null/leakage data rules, model loading, output shape, exact notebook
parity, API routes, batch prediction, monitoring, and durable prediction logging. A failing
test returns a non-zero status and stops both the local script and GitHub Actions pipeline.

## Repository structure

```text
app/                 FastAPI routes, lifecycle and exception handling
config/              Service parameters, feature/data contract and Prometheus scrape config
data/                Original Olist data; versioned by DVC, not baked into the API image
models/seed/         Small frozen release bundle used only to bootstrap MLflow on a clean machine
notebooks/            The six Task 2 training notebooks; excluded from the service image
src/olist_mlops/     Config, features, GX validation, inference, registry, storage and metrics
tests/                Unit, data, model-parity and API integration tests
requirements/         Separately pinned runtime and development dependencies
monitoring/           Prometheus alert rules
docs/                 Architecture, validation, versioning and operations decisions
.github/workflows/    Push/PR quality gates plus image build and GHCR push on main
```

The API image copies only `app`, `src`, `config`, packaging metadata and runtime
requirements. It deliberately excludes raw data, artifacts, notebooks, tests and secrets.

## Configuration

All service behavior is in `config/settings.yaml` and `config/feature_contract.yaml`.
Environment placeholders make the same code usable locally and in containers.

| Setting | Reason |
|---|---|
| `model.loader`, `tracking_uri`, `name`, `alias` | Select registry loading and the deployable version without changing code |
| `model.local_*_path` | Explicit test/bootstrap paths for the frozen fitted objects |
| `validation.failure_policy` | Documents that invalid orders are rejected with HTTP 422 |
| `prediction_store.*` | Select PostgreSQL in production or JSONL in isolated tests |
| `logging.*` | Level, format, rotation size and destinations |
| `monitoring.*` | Rolling window, reference rate and alert thresholds |
| feature lists/ranges/categories/nullability | Reproduce Notebook 05 and define the incoming data contract |

Secrets and connection strings are passed through environment variables. `.env` is ignored;
only safe example names and local demonstration values are committed.

## Data and artifact traceability

DVC pointers track `data/raw` and `artifacts`. The configured `minio` remote points at the
stack's S3-compatible storage and contains no committed credentials. After the stack is up:

```powershell
$env:AWS_ACCESS_KEY_ID = (Select-String MINIO_ROOT_USER .env).Line.Split('=')[1]
$env:AWS_SECRET_ACCESS_KEY = (Select-String MINIO_ROOT_PASSWORD .env).Line.Split('=')[1]
dvc push
```

MLflow records the frozen model parameters, validation/test metrics, feature list and result
summary, stores model files in MinIO, creates a registry version, tags its stage as
`Production`, and assigns the `champion` alias. The registration step does not train or fit
anything.

## Observability and later evaluation

Every accepted or rejected prediction is logged with input, output/error, latency and model
version. Production records are stored in PostgreSQL table `prediction_logs`; the schema
reserves `actual_delivery_timestamp` and `actual_late` for evaluation after ground truth
arrives. `/metrics` exposes HTTP counts/latency, prediction classes/probabilities, validation
errors, rolling late ratio and a distribution-drift score.

See [architecture](docs/architecture.md), [validation and failure behavior](docs/validation.md),
[data/model versioning](docs/versioning.md), and [monitoring decisions](docs/monitoring.md).
The [assignment checklist](docs/assignment-checklist.md) maps every brief requirement to
its implementation and verification evidence.
Earlier work remains documented in [Task 2](TASK2_README.md) and the Task 1 files.
