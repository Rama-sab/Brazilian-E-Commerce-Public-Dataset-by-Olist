# Model results summary

## Selection

- Primary metric: average precision (PR-AUC)
- Selected logistic-regression C: `0.01`
- Selected validation F1 threshold: `0.79`
- Preprocessing was fit on training only; test was evaluated once after choices were frozen.

## Test comparison

| Model | PR-AUC | ROC-AUC | Late precision | Late recall | Late F1 | Balanced accuracy | Accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prior baseline | 0.066 | 0.500 | 0.000 | 0.000 | 0.000 | 0.500 | 0.934 |
| Logistic regression | 0.125 | 0.692 | 0.106 | 0.226 | 0.145 | 0.546 | 0.823 |

The trained model beats the feature-free baseline on test PR-AUC. Accuracy is included for context but is not used to select the model because the target is imbalanced.
