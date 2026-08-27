# Task 2 verification

Verified on 2026-08-24 with Python 3.12.13 from a clean `artifacts/`
directory. The final deliverable was built on the supplied Task 1 ZIP and run
with its nine CSV tables.

## Sequential execution

All six executed notebooks completed successfully with no error outputs:

1. `01_read_and_join.ipynb`
2. `02_create_labels.ipynb`
3. `03_split_data.ipynb`
4. `04_eda_training_only.ipynb`
5. `05_feature_engineering.ipynb`
6. `06_train_tune_evaluate.ipynb`

The machine-readable run record is `artifacts/execution_log.json`.

## Baseline consistency

- Task 1's PostgreSQL defaults are supported: `olist_db`, `olist_user`, and
  `olist_pass` on port 5432.
- Task 1's full timestamp label rule is preserved.
- Label counts match Task 1's captured SQL result exactly: 7,826 late and
  88,644 on time.
- All original Task 1 project files remain in the final package; Task 2 is
  added on top.

## Data and artifact checks

- Joined ML table: 99,441 rows, 99,441 unique order IDs, 41 columns.
- Labelable delivered orders: 96,470.
- Label distribution: 7,826 late and 88,644 on time (8.11% late,
  11.33:1 majority/minority ratio).
- Chronological split: 67,529 train, 14,470 validation, 14,471 test.
- The three order-ID sets are pairwise disjoint and date ordered.
- EDA reads training only and saves seven charts.
- Preprocessing is fit on training only and produces 142 transformed features.
- Forbidden future/outcome and identifier fields do not occur in the saved
  transformed feature names.
- Every sparse matrix contains finite values and has the expected row count.
- Saved preprocessor and model both reload and accept the saved matrices.
- The test file is loaded in Notebook 6 only after model and threshold choices
  are frozen.

## Final test result

| Model | PR-AUC | ROC-AUC | Late precision | Late recall | Late F1 | Balanced accuracy | Accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prior baseline | 0.066 | 0.500 | 0.000 | 0.000 | 0.000 | 0.500 | 0.934 |
| Class-weighted logistic regression | 0.125 | 0.692 | 0.106 | 0.226 | 0.145 | 0.546 | 0.823 |

The model beats the feature-free baseline on the primary metric. Accuracy is
not used for selection because the majority-only baseline already reaches
93.4% accuracy while identifying none of the late orders.

