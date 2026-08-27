# Training-only EDA findings

- The training split contains **67,529 orders** from 2016-09-15 through 2018-04-15.
- The late rate is **9.03%**, an approximately **10.1:1** majority/minority imbalance. Accuracy alone is therefore unsuitable.
- Highest missingness among present columns: product_category_mode (1.8%), product_description_length_mean (1.8%), product_name_length_mean (1.8%). Missing values will be imputed by transformers fit on training data only.
- The strongest non-outcome numerical correlation with `late` is **customer_seller_distance_km** (0.086); relationships are not assumed to be linear from correlation alone.
- Prices, freight, payment totals, product size/weight, item counts, promised lead time, and customer-seller distance are skewed and can contain legitimate high-value orders. Median imputation plus scaling is safer than deleting outliers without business evidence.
- Customer/seller state, product category, payment type, date seasonality, weekday/weekend, fixed-holiday, and distance groups show different late rates and are retained as candidate signals.
- IDs, raw ZIP prefixes, and city are excluded to avoid memorization/high cardinality. Reviews and actual delivery/carrier/delay fields are future information and are excluded for leakage control.
- First model: a class-weighted logistic regression. Primary validation metric: PR-AUC, with late-class precision, recall, F1, ROC-AUC, and balanced accuracy reported as supporting metrics.
