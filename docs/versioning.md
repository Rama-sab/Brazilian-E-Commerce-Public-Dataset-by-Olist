# Data, artifact and model versioning

## DVC

`data/raw.dvc` and `artifacts.dvc` identify the exact raw dataset and Task 2 artifacts by
content hash. The versioned `.dvc/config` names an S3-compatible MinIO remote but does not
contain access keys. Credentials come from the ignored `.env` file through the standard AWS
environment variables.

Typical lifecycle:

```powershell
dvc status
dvc push
git add data/raw.dvc artifacts.dvc .gitignore
git commit -m "Version Olist data and Task 2 artifacts"
```

After cloning a repository whose remote is populated, `dvc pull` restores the same content.
The production API image does not contain these folders.

## MLflow

`python -m olist_mlops.register_model` logs:

- selected logistic-regression `C` and decision threshold;
- validation and test metrics from Notebook 06;
- the feature list and result summary;
- the fitted preprocessor and frozen model bundle as one inference PyFunc model.

The command creates a version of `olist-late-delivery`, adds the `Production` stage tag, and
sets the `champion` alias. The API uses the alias URI and reports the resolved immutable
version in every response and prediction-log row. Registration contains no `fit` call.

