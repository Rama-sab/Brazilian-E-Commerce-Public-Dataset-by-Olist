# Olist MLOps Task 2 - From Tables to Notebooks

This is the single README for Task 2. It combines the original run guide and
technical report into one reproducible description of the six-notebook
workflow. The project predicts whether an Olist order will arrive late (`1`) or
on time (`0`).

## Task 2 objective

Task 1 created the local data and PostgreSQL foundation. Task 2 turns those
tables into a notebook-based machine-learning workflow in which every notebook:

1. performs one clearly defined job;
2. reads artifacts created by the previous notebook; and
3. saves artifacts required by the next notebook.

The target definition remains consistent with Task 1:

```text
late = 1 when order_delivered_customer_date > order_estimated_delivery_date
late = 0 otherwise
```

Only delivered orders with both actual and estimated delivery timestamps are
labelable. This produces 96,470 labeled orders: 7,826 late (8.11%) and 88,644
on time (91.89%).

## Notebook workflow and artifact contract

| Notebook | One job | Main artifacts |
|---|---|---|
| `01_read_and_join.ipynb` | Audit all nine tables, aggregate one-to-many tables, and create one row per order | `01_ml_table.csv.gz`, join audit and summary |
| `02_create_labels.ipynb` | Create and manually verify the late/on-time target | `02_labeled_table.csv.gz`, label distribution and examples |
| `03_split_data.ipynb` | Split chronologically before detailed analysis | `03_train.csv.gz`, `03_validation.csv.gz`, `03_test.csv.gz` |
| `04_eda_training_only.ipynb` | Perform detailed EDA using only the training split | Seven charts, profiles, findings, and feature decisions |
| `05_feature_engineering.ipynb` | Fit preprocessing on train only and transform every split | Sparse matrices, labels, order IDs, transformer, feature list |
| `06_train_tune_evaluate.ipynb` | Compare a baseline, tune on validation, and evaluate test once | Final model, predictions, threshold search, result summaries |

## Notebook 1 - Read and join

The notebook reads `customers`, `geolocation`, `order_items`,
`order_payments`, `order_reviews`, `orders`, `products`, `sellers`, and
`product_category_translation`. For each table it records the row meaning,
shape, key, duplicate-key count, and sample rows.

The important join rule is **aggregate before joining**:

- Items are summarized into order-level counts, seller/category modes, price
  and freight totals, and product-property summaries.
- Payments are summarized into order-level payment counts, total value,
  installments, and payment type.
- Geolocation observations are summarized to median coordinates by ZIP prefix.
- Reviews are audited but excluded from prediction features because reviews are
  created after delivery.

The result contains 99,441 rows, 99,441 unique order IDs, and 41 columns.
Assertions prevent accidental row multiplication.

## Notebook 2 - Create and verify labels

Notebook 2 keeps only labelable delivered orders and applies the Task 1
timestamp rule. It independently checks six real examples: three late and
three on time.

| Delivery class | Orders | Percentage |
|---|---:|---:|
| Late | 7,826 | 8.11% |
| On time | 88,644 | 91.89% |

The majority/minority ratio is approximately 11.33:1. Accuracy alone is
therefore misleading.

## Notebook 3 - Chronological split

Rows are sorted by `order_purchase_timestamp`, with `order_id` as a stable
tie-breaker, and split 70% / 15% / 15%.

| Split | Rows | Date range | Late rate |
|---|---:|---|---:|
| Train | 67,529 | 2016-09-15 to 2018-04-15 | 9.03% |
| Validation | 14,470 | 2018-04-15 to 2018-06-21 | 5.34% |
| Test | 14,471 | 2018-06-21 to 2018-08-29 | 6.61% |

This split simulates deployment: train on past orders and predict future
orders. The three order-ID sets are disjoint and their date boundaries are
asserted.

## Notebook 4 - Training-only EDA

Notebook 4 opens only the training artifact. It investigates data roles,
dtypes, shape, memory, missingness, distributions, skew, IQR outliers,
categorical cardinality, rare categories, target relationships, correlations,
seasonality, weekday/weekend effects, fixed-date holidays, states, ZIP prefixes,
and customer-seller distance.

Main findings:

- The training late rate is 9.03%, so PR-AUC and late-class metrics are more
  useful than raw accuracy.
- Product category/name/description features have the highest present
  missingness at about 1.8%.
- Customer-seller distance has the strongest non-outcome numerical correlation
  with `late` at about 0.086.
- Price, freight, payment totals, sizes, weight, counts, promised lead time,
  and distance are skewed; legitimate values are not deleted only because they
  cross an IQR fence.
- State, category, payment type, calendar, holiday, and distance groupings show
  different late rates and remain candidate signals.

## Notebook 5 - Feature engineering

Only information available at prediction time is used. Reviews, actual
delivery, carrier hand-off, delay, order status, identifiers, raw ZIP prefixes,
and the target never enter the feature matrix.

The saved `ColumnTransformer` applies:

- median imputation and standard scaling to numerical features;
- most-frequent imputation and one-hot encoding to categorical features;
- unknown-category handling and rare-category grouping; and
- fitting on training data only, followed by transformation of validation and
  test data.

The final SciPy CSR matrices contain 142 features. The transformer, feature
names, matrices, labels, and order IDs are saved for reproducible reuse.

## Notebook 6 - Train, tune, and evaluate

The feature-free baseline is `DummyClassifier(strategy="prior")`. The trained
model is a class-weighted logistic regression. Regularization strength is
selected using validation PR-AUC; the classification threshold is selected
using validation late-class F1.

- Selected `C`: `0.01`
- Selected threshold: `0.79`
- Primary metric: average precision (PR-AUC)

The test set is loaded only after preprocessing, model, and threshold choices
are frozen.

| Model | PR-AUC | ROC-AUC | Late precision | Late recall | Late F1 | Balanced accuracy | Accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prior baseline | 0.066 | 0.500 | 0.000 | 0.000 | 0.000 | 0.500 | 0.934 |
| Logistic regression | 0.125 | 0.692 | 0.106 | 0.226 | 0.145 | 0.546 | 0.823 |

The model beats the baseline on the primary metric. Its lower raw accuracy is
expected: the majority-only baseline misses every late order, while the model
identifies 22.6% of late test orders.

## Leakage and evaluation guardrails

- Detailed EDA reads training data only.
- Preprocessing is fitted on training data only.
- Actual delivery, carrier, review, delay, status, target, and identifier
  columns are excluded from features.
- Validation data selects model strength and threshold.
- Test matrices and labels are evaluated once, at the end.
- PR-AUC is the primary metric because late orders are the minority.

## Input behavior

Notebook 1 first tries the Task 1 PostgreSQL database. It supports `PGHOST`,
`PGPORT`, `PGDATABASE`, `PGUSER`, and `PGPASSWORD`, plus the equivalent
`POSTGRES_*` variables. Defaults match Task 1: `olist_db`, `olist_user`,
`olist_pass`, port `5432`.

If PostgreSQL is unavailable, the notebook loads all nine CSVs. It checks:

1. `OLIST_DATA_DIR`, if explicitly set;
2. `data/raw/`; and
3. `data/` for compatibility with the original Task 1 layout.

## Run from a clean start - Windows PowerShell

Open PowerShell in the extracted project folder:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-task2.txt
.\RUN_TASK2.bat --clean
```

## Run from a clean start - Git Bash

Use forward slashes in Git Bash:

```bash
py -m venv .venv
./.venv/Scripts/python.exe -m pip install --upgrade pip
./.venv/Scripts/python.exe -m pip install -r requirements-task2.txt
./.venv/Scripts/python.exe tools/execute_task2_notebooks.py --clean
```

If pip reports an invalid PostgreSQL certificate path, clear the stale
certificate variables for the current Git Bash session and retry:

```bash
unset SSL_CERT_FILE REQUESTS_CA_BUNDLE CURL_CA_BUNDLE PIP_CERT
```

`--clean` deletes only this project's resolved `artifacts/` directory before
rebuilding it. The runner is a notebook execution helper, not a production ML
pipeline.

## Successful execution

The latest clean run used Python 3.13 and completed all six notebooks without
cell errors. The expected final line is:

```text
All six notebooks completed successfully.
```

Inspect these outputs after execution:

- `artifacts/execution_log.json`
- `artifacts/04_eda_findings.md`
- `artifacts/05_matrix_summary.json`
- `artifacts/06_results_summary.md`
- `Task2_Report.docx`

## Completion checklist

- [x] Six numbered notebooks, one job each.
- [x] Clean sequential execution with no error outputs.
- [x] Every notebook reads the previous artifact and saves its own artifacts.
- [x] Chronological split explained and verified.
- [x] Detailed EDA performed on training only.
- [x] Preprocessing fitted on training only and saved.
- [x] Baseline compared with the trained model.
- [x] Test set evaluated once at the end.
- [x] Charts, findings, feature list, transformer, model, predictions, and
  summaries saved.
