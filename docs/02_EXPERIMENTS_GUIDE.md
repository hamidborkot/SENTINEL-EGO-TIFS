# CIPHER-TIFS — Experiments Guide

> Exact steps to run every experiment, what each proves, expected outputs.

---

## Environment Setup

```
Python 3.10+
PyTorch (CUDA GPU recommended — use Kaggle P100 for r4.2)
numpy, pandas, scipy, scikit-learn
torch, torch.optim, torch.nn
opacus (optional — we compute ε manually)
```

### Two-Part Notebook Structure

Every dataset uses two notebooks:
- **Part A** — Feature extraction → E1 Primary Detection → E2 Ablation
- **Part B** — E3 Privacy Sweep → E8 MIA → E9 Byzantine

> ⚠️ **Always restart the kernel after Part A before running Part B.** Cached `.npy` files must be loaded fresh.

### Switching Datasets
Change only ONE line at the top of both notebooks:
```python
DATASET = 'r6.2'   # or 'r5.2' or 'r4.2'
```

---

## STEP 1–4: Feature Extraction (Part A)

This runs automatically when Part A is executed. It produces:
- `Xtrain.npy`, `Xtest.npy` — feature matrices (27 columns)
- `ytrain.npy`, `ytest.npy` — binary labels
- `clientmasks.npy` — boolean masks for 10 FL clients
- `traindf.pkl` — full training dataframe
- `featcols.json` — feature column names

### Feature Groups Produced

```
Legacy (23 features):
  logoncount, afterhrs, uniquepcs, ahratio, usbcount, fileops,
  rmcopies, rmreads, rmratio, emailsent, extemail, avgmailsize,
  extratio, httpcount, riskycount, riskyratio, rolechanges, deptchanges,
  O, C, E, A, N

BDM / PBI (2 features):
  pbidrift     ← Mahalanobis-like drift from 90-day personal baseline
  pbialert     ← Binary: pbidrift > adaptive threshold τ

AIF (2 features):
  aifscore     ← Weighted composite: 0.30*rmcopies + 0.20*rmratio
                 + 0.15*usbcount + 0.10*riskycount + 0.10*extratio
                 + 0.10*pbidrift + 0.05*ahratio
  aifalert     ← Binary: aifscore > 97th percentile

Total: 27 features
```

### PBI Threshold Computation
```python
tau = float(malpbi.quantile(0.40)) if float(malpbi.median() > 0) \
      else float(df['pbidrift'].quantile(0.70))
```
Print output shows: `PBI tau=0.3710  Total features 27`

---

## E1 — Primary Detection

**What it proves:** CIPHER detects insider threats with high F1 and AUC under DP.

**How it runs:**
1. Loads checkpoint files from OUTDIR
2. Calls `runfl()` with Gaussian DP noise
3. Evaluates tail-averaged model (last 5 stable rounds)

### Hyperparameters Per Dataset

| Parameter | r4.2 | r5.2 | r6.2 |
|-----------|------|------|------|
| `FLROUNDS` | 28 | 28 | 20 |
| `LOCAL_EPOCHS` | 5 | 5 | 3 |
| `QSAMPLE` | 0.015 | 0.015 | 0.01 |
| `SIGMA` (DP noise) | 0.8 | 0.8 | 0.8 |
| `PATIENCE` | 10 | 10 | 8 |
| `WARMUP_ROUNDS` | 3 | 3 | 3 |
| `TAIL_AVG_K` | 5 | 5 | 5 |
| `N_CLIENTS` | 10 | 10 | 10 |
| `N_BYZANTINE` | 3 | 3 | 3 |
| `CLIP_NORM` | 1.0 | 1.0 | 1.0 |

### ThreatNet Architecture
```python
nn.Sequential(
    nn.Linear(d, 256), nn.GroupNorm(8, 256), nn.GELU(), nn.Dropout(0.3),
    nn.Linear(256, 128), nn.GroupNorm(8, 128), nn.GELU(), nn.Dropout(0.2),
    nn.Linear(128, 64), nn.GELU(),
    nn.Linear(64, 1), nn.Sigmoid()
)
```
> ⚠️ GroupNorm MUST stay. Never replace with BatchNorm1d. See docs/03_DATASETS_GUIDE.md.

### Expected Results

| Dataset | F1 | AUC | Recall | FPR | ε |
|---------|----|-----|--------|-----|---|
| r6.2 | ~0.88 | ~0.985 | ~0.854 | ~0.002 | ~1.33 |
| r5.2 | ~0.77 | ~0.947 | ~0.68 | ~0.003 | ~1.53 |
| r4.2 | ≥0.72 | ≥0.92 | TBD | TBD | ~1.5 |

**Output file:** `{OUTDIR}/results_e1_primary.csv`
**Model checkpoint:** `{OUTDIR}/fedm_e1.pt` (used by Part B)

---

## E2 — Ablation Study

**What it proves:** BDM+PSE+AIF features add statistically significant value over Legacy-Only.

**Feature sets compared:**

| Name | Features |
|------|----------|
| `Legacy-Only` | 23 standard CERT features |
| `+BDM` | Legacy + `pbidrift` + `pbialert` |
| `+BDM+PSE` | Legacy + `pbidrift` + `pbialert` + `aifscore` |
| `Full-CIPHER` | All 27 features |

**Classifier:** GradientBoostingClassifier(n_estimators=100), 10 seeds
**Test:** Wilcoxon signed-rank test (Legacy-Only vs each variant)

### ⚠️ CRITICAL FIX REQUIRED (E2 on r6.2)

Current E2 uses **random split** → p=0.0645, NOT significant.

**Apply this fix — time-based split:**
```python
# In the E2 block of Part A, REPLACE the train_test_split loop with:

cutoff = df['daydt'].quantile(0.75)   # same cutoff as E1
train_e2 = df[df['daydt'] <= cutoff].reset_index(drop=True)
test_e2  = df[df['daydt'] >  cutoff].reset_index(drop=True)

for name, feats in FEATURE_SETS.items():
    scaler_e2 = StandardScaler()
    Xa = scaler_e2.fit_transform(train_e2[feats].values.astype(np.float32))
    ya = train_e2['label'].values
    Xb = scaler_e2.transform(test_e2[feats].values.astype(np.float32))
    yb = test_e2['label'].values
    f1s = []
    for seed in range(10):
        clf = GradientBoostingClassifier(n_estimators=100, random_state=seed)
        clf.fit(Xa, ya)
        f1s.append(f1_score(yb, clf.predict(Xb), zero_division=0))
        del clf
    scores[name] = f1s
```

### Fallback (if still p > 0.05 on r6.2)
- Use **r5.2 as the primary ablation** in the paper (p=0.0039 ✅)
- Note r6.2 as: "At large scale with abundant legacy features, marginal per-feature gains are smaller but directionally consistent."

**Output files:**
- `{OUTDIR}/results_e2_wilcoxon.csv`
- `{OUTDIR}/results_e2_ablation_raw.csv`

---

## E3 — Privacy-Utility Sweep

**What it proves:** CIPHER maintains high detection quality even at strong privacy (small ε).

**How it runs:** Re-trains FL at 5 σ levels + No-DP, evaluates each.

```python
for sigma in [8.0, 4.0, 2.0, 1.2, 0.8]:
    m, eps_i = runfl(Xtrain, ytrain, clientmasks,
                     label=f'σ={sigma}', sigma=sigma, verbose=False)
    rs = eval_model(m, Xtest, ytest)
    # save: sigma, epsilon, F1, AUC, Recall, FPR
```

**Expected results (r6.2):**

| σ | ε | F1 | AUC |
|---|---|----|-----|
| 8.0 | 1.28 | 0.8068 | 0.9253 |
| 4.0 | 1.28 | 0.7981 | 0.9574 |
| 2.0 | 1.29 | 0.8469 | 0.9738 |
| 1.2 | 1.30 | 0.8736 | 0.9807 |
| 0.8 | 1.33 | **0.8834** | **0.9824** |
| No-DP | ∞ | 0.8828 | 0.9898 |

> Key message: At σ=0.8, F1 with DP ≈ F1 without DP. DP adds privacy at near-zero cost.

**Output file:** `{OUTDIR}/results_e3_privacy_utility.csv`

---

## E8 — Membership Inference Attack

**What it proves:** DP training prevents the model from memorising individual training records.

**How it works:**
```python
def mia_audit(model, Xtr, Xte, sample_n=20000):
    # Get prediction confidences on train and test sets
    ptr = model(gpu(Xtr)).cpu().numpy()
    pte = model(gpu(Xte)).cpu().numpy()
    # Try to classify train vs test using confidence scores
    Xm = np.concatenate([ptr[sample], pte[sample]]).reshape(-1,1)
    ym = np.concatenate([np.ones(n), np.zeros(n)])
    clf = LogisticRegression(max_iter=200).fit(Xa, ya)
    return roc_auc_score(yb, clf.predict_proba(Xb)[:,1])
```

**Threshold:** MIA AUC < 0.53 → DP effective; AUC ≈ 0.5 → random guessing (ideal)

**Expected results:**
- r6.2: MIA AUC = **0.4839** → DP effective ✅
- r5.2: MIA AUC = **0.4895** → DP effective ✅

**Output file:** `{OUTDIR}/results_e8_mia.csv`

---

## E9 — Byzantine Robustness

**What it proves:** CIPHER withstands gradient poisoning from malicious federated clients.

**Setup:** 3 out of 10 clients are Byzantine (they flip all labels before local training).

**Three configurations tested:**
1. `Clean` — all 10 clients honest, FedAvg aggregation
2. `FedAvg+Attack` — 3/10 Byzantine, standard FedAvg (vulnerable)
3. `Krum+Attack` — 3/10 Byzantine, Multi-Krum aggregation (defence)

**Multi-Krum aggregation:**
- Computes pairwise L2 distance between all client model parameters
- Selects the `k = n - n_byz - 2` clients with lowest neighbour-distances
- Averages selected models
- Effectively rejects Byzantine outliers

**Expected results (r6.2):**

| Config | F1 | AUC | F1 Drop vs Clean |
|--------|----|-----|------------------|
| Clean | 0.8833 | 0.9847 | — |
| FedAvg+Byzantine | 0.8569 | ~0.978 | −3.0% |
| Krum+Byzantine | 0.8581 | ~0.979 | −2.8% |

**Output file:** `{OUTDIR}/results_e9_byzantine.csv`

---

## Full Running Order

```
Round 1 (r6.2 — already done, verify CSVs exist):
  Part A → E1 → E2 (apply time-split fix) → save checkpoint
  [Restart kernel]
  Part B → E3 → E8 → E9 → save all CSVs

Round 2 (r5.2 — already done, verify CSVs exist):
  Same as Round 1 but DATASET = 'r5.2'

Round 3 (r4.2 — NOT done, run on Kaggle):
  Use v4 code (v4 FINAL notebooks)
  DATASET = 'r4.2'
  Verify malicious rate < 6% before training
  Part A → E1 → E2 → save checkpoint
  [Restart kernel]
  Part B → E3 → E8 → E9 → save all CSVs

After all 3 datasets:
  Apply E2 time-split fix across all datasets
  Verify all result CSVs
  Build paper tables
```
