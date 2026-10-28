# Public-data ML baseline

## Download
Download `creditcard.csv` from https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud and place it at `backend/data/raw/creditcard.csv`.

## Install
Activate the backend virtual environment and run:
```powershell
python -m pip install -r requirements.txt
```

## Train and evaluate
From the `backend` directory:
```powershell
python train_public_dataset.py
```

Optional threshold:
```powershell
python train_public_dataset.py --threshold 0.25
```

Artifacts:
- `backend/models/creditcard_baseline.joblib`
- `backend/models/creditcard_baseline_metrics.json`

## Metrics
- Precision: among flagged transactions, fraction actually fraudulent.
- Recall: fraction of fraudulent transactions detected.
- F1: harmonic mean of precision and recall.
- Average precision (PR-AUC-style summary): especially useful for rare positive classes.
- ROC-AUC: ranking discrimination; interpret together with precision/recall because fraud is rare.
- Confusion matrix: true negatives, false positives, false negatives, true positives.

The chosen threshold is a demo operating point, not a universal business decision. Tune it against the cost of false positives, missed fraud, manual-review capacity, and validation data.

## Important limitation
This is a reproducible stratified random split for an initial benchmark. The dataset covers only two days and has PCA-transformed features, so this does not prove that the model generalizes to live transactions. For stronger evaluation, add temporal validation, calibration, threshold selection on validation data, and compare multiple baselines.

This model is intentionally saved separately from the demo API model. It expects `Time`, `V1`...`V28`, and `Amount`, whereas the current API accepts simulated business features such as `device_new` and `transactions_last_hour`. Do not wire one model into the other schema.
