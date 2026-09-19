# Monitoring and alert decisions

The API exposes `/metrics` in Prometheus format. The main series are:

| Metric | Use |
|---|---|
| `olist_http_requests_total` | traffic and HTTP error-rate calculation |
| `olist_http_request_latency_seconds` | latency histogram and p95 calculation |
| `olist_predictions_total` | late/on-time distribution over time |
| `olist_late_probability` | probability distribution changes |
| `olist_prediction_errors_total` | schema and Great Expectations rejection counts |
| `olist_prediction_rolling_late_ratio` | current rolling class balance |
| `olist_prediction_drift_absolute_rate_difference` | absolute difference from the Task 2 reference late rate |

`monitoring/alerts.yml` documents and implements three initial alerts:

- critical when HTTP 5xx rate is above 5% for 10 minutes;
- warning when p95 latency is above 500 ms for 10 minutes;
- warning when the rolling late-prediction rate differs from the reference by more than 0.12
  for 30 minutes.

These are starting thresholds, not universal truths. Revisit them after observing real traffic
volume, service-level objectives and seasonal delivery behavior. Class-distribution drift is
an operational warning, not proof that input drift caused degradation.

Prediction rows are retained in PostgreSQL. When actual delivery dates arrive, populate
`actual_delivery_timestamp` and `actual_late`, join by `order_id`, and calculate precision,
recall, PR-AUC, calibration and performance by time/state/category for each `model_version`.

