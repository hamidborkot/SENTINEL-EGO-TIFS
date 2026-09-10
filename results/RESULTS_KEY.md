# CIPHER-TIFS — Results Column Definitions

This file defines every column used across all result CSVs. Refer here when reading any file in `results/`.

---

## Common Columns (all CSVs)

| Column | Type | Description |
|---|---|---|
| `dataset` | string | CERT version: `r4.2`, `r5.2`, or `r6.2` |
| `seed` | int / `multi` | Random seed used. `multi` = aggregate over 10 seeds |
| `notes` | string | Context, caveats, or special conditions |

---

## E1 — Primary Detection

| Column | Description |
|---|---|
| `method` | Model configuration (e.g., `CIPHER-FL-DP`) |
| `f1` | F1-score on held-out test set (time-split) |
| `auc` | ROC-AUC |
| `recall` | True Positive Rate (sensitivity) |
| `fpr` | False Positive Rate (1 - specificity) |
| `precision` | Precision |
| `epsilon` | DP privacy budget ε computed via Rényi DP accounting (α=10) |
| `sigma` | DP noise multiplier |
| `n_clients` | Number of federated clients |
| `fl_rounds` | Total FL communication rounds |
| `local_epochs` | Local training epochs per round |
| `split` | Data split method (`time` = 75th percentile cutoff) |
| `tail_avg_k` | Number of tail rounds averaged for final model |

---

## E2 — Ablation Study

| Column | Description |
|---|---|
| `feature_set` | One of: `Legacy-Only` (23), `+BDM` (25), `+BDM+PSE` (26), `Full-CIPHER` (27) |
| `n_features` | Number of features in this set |
| `f1` | F1-score for this seed/feature set combination |
| `split` | `time_75pct` — training on first 75% of timeline, test on last 25% |
| `classifier` | `GradientBoostingClassifier_n100` (n_estimators=100) |
| `wilcoxon_p` | Two-sided Wilcoxon signed-rank p-value vs Legacy-Only over 10 seeds |
| `significant_p005` | TRUE if p < 0.05 |
| `significant_p001` | TRUE if p < 0.01 |

---

## E3 — Privacy-Utility Sweep

| Column | Description |
|---|---|
| `sigma` | DP noise multiplier (8.0, 4.0, 2.0, 1.2, 0.8, or `No-DP`) |
| `epsilon` | Resulting ε value; `inf` for No-DP |
| `f1` | Detection F1 at this privacy level |
| `auc` | ROC-AUC at this privacy level |

---

## E8 — Membership Inference Attack

| Column | Description |
|---|---|
| `attack_type` | `confidence_mia` — logistic regression on model confidence scores |
| `feature_used` | `predicted_confidence` — model output probability |
| `mia_auc` | AUC of the MIA attack classifier. Near 0.5 = attacker at random guessing |
| `threshold` | Security threshold (0.53). Below = DP effective |
| `verdict` | Interpretation of MIA AUC |

---

## E9 — Byzantine Robustness

| Column | Description |
|---|---|
| `config` | `Clean`, `FedAvg+Attack`, or `Krum+Attack` |
| `aggregation` | `FedAvg` or `MultiKrum` |
| `n_byzantine` | Number of Byzantine clients (3 out of 10 = 30%) |
| `attack_type` | `sign_flip_scale` — θ_byz = θ_global − scale×(θ_local − θ_global) |
| `attack_scale` | Scale factor (2.0) |
| `f1_drop_pct` | Percentage F1 drop vs Clean baseline |
| `attack_mitigated_pct` | % of FedAvg attack damage neutralised by Krum |

---

## Feature Set Definitions

| Label | Features Included | Count |
|---|---|---|
| `Legacy-Only` | logon_count, after_hrs, unique_pcs, ah_ratio, usb_count, file_ops, rm_copies, rm_reads, rm_ratio, email_sent, ext_email, avg_mail_size, ext_ratio, http_count, risky_count, risky_ratio, role_changes, dept_changes, O, C, E, A, N | 23 |
| `+BDM` | Legacy + pbi_drift, pbi_alert | 25 |
| `+BDM+PSE` | +BDM + aif_score | 26 |
| `Full-CIPHER` | +BDM+PSE + aif_alert | 27 |
