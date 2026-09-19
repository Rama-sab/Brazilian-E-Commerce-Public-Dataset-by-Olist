# Validation and failure behavior

The configured policy is **reject**. Invalid data returns HTTP 422 and is never passed to the
preprocessor or classifier.

Validation happens in two complementary layers:

1. Pydantic enforces the request shape, scalar types, finite numbers, required fields,
   `extra=forbid`, and business relationships such as estimated delivery after purchase.
2. Great Expectations validates the feature frame against `config/feature_contract.yaml`:
   numeric ranges, allowed categories, required non-null values and promised lead time.

Optional training features may be null because the saved Notebook 05 imputer was explicitly
fit to handle them. Required purchase, order-count, price, freight, geography/category and
payment-mode inputs may not be null. Unknown one-hot categories could technically be ignored
by scikit-learn, but this service rejects categories outside the documented contract so data
quality failures remain visible.

## Deliberate failure demonstrations

Unknown category:

```powershell
$body = Get-Content models/seed/example_order.json -Raw | ConvertFrom-Json
$body.payment_type_mode = "cryptocurrency"
$body | ConvertTo-Json | curl.exe -X POST http://localhost:8000/v1/predict `
  -H "Content-Type: application/json" --data-binary "@-"
```

The response is 422 and includes the failing GX expectation and `policy: reject`.

Failing test:

```powershell
pytest tests/test_model.py -k notebook_predictions
```

Changing the expected saved probability causes pytest to exit non-zero, which stops
`scripts/test.ps1` and the CI job. Restore the expected value after the demonstration.

All validation rejections are counted in Prometheus and stored in the prediction log with the
payload, reason, latency and model version.

