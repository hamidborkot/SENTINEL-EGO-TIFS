# CIPHER-TIFS — How To Work Guide

> Step-by-step instructions for every session. Whether continuing work or starting a fresh thread, follow this guide.

---

## Starting Any Session (Checklist)

- [ ] Read `docs/00_MASTER_CONTEXT.md` — understand the full picture
- [ ] Read `docs/01_RESEARCH_PLAN.md` — know what is locked and what needs fixing
- [ ] Check `docs/02_EXPERIMENTS_GUIDE.md` before running any experiment
- [ ] Do NOT change the research direction
- [ ] Do NOT add new datasets
- [ ] Do NOT use BatchNorm1d (GroupNorm only)

---

## Priority 1 — Fix E2 Ablation (Do This First)

**Goal:** Get Wilcoxon p < 0.05 for Full-CIPHER vs Legacy-Only on r6.2.

**Exact Steps:**

1. Open Part A notebook for r6.2.
2. Find the E2 block (labelled `## E2 ABLATION`).
3. Locate the inner loop that calls `train_test_split(..., stratify=yfull, random_state=seed)`.
4. Replace the split logic with time-based split. See the exact code in `docs/02_EXPERIMENTS_GUIDE.md` E2 section.
5. Make sure `traindf` and `testdf` are in scope at the E2 block (they are computed in Step 4 — use them directly).
6. Re-run the E2 block only (no need to re-run feature extraction).
7. Check the Wilcoxon output:
   - p < 0.05 on `Legacy-Only vs Full-CIPHER` → ✅ Fix worked, save CSV
   - p > 0.05 → apply Option C (see `01_RESEARCH_PLAN.md`)
8. Save new CSV as: `results_e2_wilcoxon_timesplit.csv`

---

## Priority 2 — Run r4.2 on Kaggle

**Goal:** Get E1 F1 ≥ 0.72 on r4.2 with verified low malicious rate.

**Exact Steps:**

1. Upload **v4 Part A FINAL** and **v4 Part B** notebooks to Kaggle.
2. Upload the CERT r4.2 raw CSVs to Kaggle dataset (if not already there).
3. At the top of Part A, set: `DATASET = 'r4.2'`
4. Run the feature extraction (Steps 1–4).
5. **After Step 3, check the printed output:** You should see:
   ```
   Malicious rows: XXXXX / 300000 (Z%)
   ```
   Z must be **< 6%**. If Z > 6%, the AND-logic labelling is NOT working.
6. If Z > 6%: Debug the labelling block. Look for the section that applies AND-logic when malicious rate > 6%. Check that the condition `if mal_rate > 0.06:` is triggered.
7. Once malicious rate < 6%, continue with E1 training.
8. Check E1 output for F1 ≥ 0.72:
   - ≥ 0.72 → ✅ Continue to E2 and Part B
   - 0.65–0.72 → Try increasing `FLROUNDS = 35` and re-run E1 only
   - < 0.65 → Debug: check label distribution, check PBI threshold, check feature scaling
9. After Part A completes → save checkpoint → restart kernel → run Part B.

---

## Priority 3 — Verify All Result CSVs

Before writing the paper, confirm all the following files exist and contain valid numbers:

### r6.2 Results Checklist
- [ ] `results_e1_primary.csv` — E1 F1=0.88, AUC=0.985
- [ ] `results_e2_wilcoxon_timesplit.csv` — p < 0.05 for Full-CIPHER
- [ ] `results_e2_ablation_raw.csv` — 10-seed F1 scores for 4 feature sets
- [ ] `results_e3_privacy_utility.csv` — 5 sigma levels + No-DP
- [ ] `results_e8_mia.csv` — MIA AUC ≈ 0.48
- [ ] `results_e9_byzantine.csv` — 3 configs, F1 drop < 3%

### r5.2 Results Checklist
- [ ] `results_e1_primary.csv` — F1=0.77, AUC=0.947
- [ ] `results_e2_wilcoxon.csv` — p=0.0039 ✅
- [ ] `results_e3_privacy_utility.csv`
- [ ] `results_e8_mia.csv` — MIA AUC ≈ 0.49
- [ ] `results_e9_byzantine.csv`

### r4.2 Results Checklist
- [ ] `results_e1_primary.csv` — F1 ≥ 0.72
- [ ] `results_e2_wilcoxon.csv`
- [ ] `results_e3_privacy_utility.csv`
- [ ] `results_e8_mia.csv`
- [ ] `results_e9_byzantine.csv`

---

## Priority 4 — Build Paper Tables

Only start this after all result CSVs are confirmed.

### Table 1 — Primary Detection (E1)
```
Rows: r4.2, r5.2, r6.2
Cols: Method, F1, AUC, Recall, FPR, ε (DP Budget)
```

### Table 2 — Ablation Study (E2)
```
Rows: Legacy-Only, +BDM, +BDM+PSE, Full-CIPHER
Cols: Dataset, F1 mean±std, Wilcoxon p vs Legacy
```

### Table 3 — Privacy-Utility (E3)
```
Rows: σ=8.0, 4.0, 2.0, 1.2, 0.8, No-DP
Cols: σ, ε, F1, AUC (for r6.2 as primary, r5.2 as secondary)
```

### Table 4 — Byzantine Robustness (E9)
```
Rows: Clean, FedAvg+Attack, Krum+Attack
Cols: Dataset, F1, AUC, Recall, FPR, F1-Drop%
```

---

## How to Interpret Results

| Metric | Meaning | Threshold |
|--------|---------|----------|
| F1 | Harmonic mean of Precision and Recall. Best metric for imbalanced classes. | ≥ 0.85 target for r6.2 |
| AUC | Area under ROC curve. Threshold-independent. | ≥ 0.97 target |
| ε (epsilon) | DP privacy budget. Lower = stronger privacy. ε=1.3 means model output shifts ≤ e^1.3 ≈ 3.67× per data record added. | ε < 2.0 is strong |
| MIA AUC | Membership inference attack success. 0.5 = random = perfect DP. | < 0.53 is effective DP |
| Wilcoxon p | Statistical significance of F1 difference. | < 0.05 required; < 0.01 preferred |
| F1 Byzantine Drop | % F1 reduction under 30% poisoned clients. | < 5% required |

---

## Code Rules (Never Break These)

| Rule | Reason |
|------|--------|
| Use `GroupNorm(8, d)` — NEVER `BatchNorm1d` | BatchNorm running stats corrupt FedAvg aggregation |
| Always restart kernel between Part A and Part B | Stale in-memory arrays corrupt Part B data loading |
| Save checkpoint `.npy` files before Part B | Part B loads from disk, not from memory |
| Keep `DATASET` as the single variable to change | All paths and hyperparameters derive from it |
| r4.2 must run on Kaggle | Local RAM insufficient for chunked CSV loading |
| Verify malicious rate < 6% on r4.2 before training | Label noise inflates FPR and makes results meaningless |

---

## Quick Reference: Hyperparameters

| Parameter | r4.2 | r5.2 | r6.2 |
|-----------|------|------|------|
| `FLROUNDS` | 28 | 28 | 20 |
| `LOCAL_EPOCHS` | 5 | 5 | 3 |
| `QSAMPLE` | 0.015 | 0.015 | 0.01 |
| `SIGMA` | 0.8 | 0.8 | 0.8 |
| `N_CLIENTS` | 10 | 10 | 10 |
| `N_BYZANTINE` | 3 | 3 | 3 |
| `CLIP_NORM` | 1.0 | 1.0 | 1.0 |
| `PATIENCE` | 10 | 10 | 8 |
| `WARMUP_ROUNDS` | 3 | 3 | 3 |
| `TAIL_AVG_K` | 5 | 5 | 5 |
| Code version | v4 | v3 | v3 |
| Run on | Kaggle | Local/Kaggle | Local/Kaggle |

---

## Starting a Fresh Thread — What to Share

If you open a new conversation and need to pick up where you left off, share these files in this order:

1. `docs/00_MASTER_CONTEXT.md` — full background and results so far
2. `docs/01_RESEARCH_PLAN.md` — what is locked and what needs fixing
3. `docs/02_EXPERIMENTS_GUIDE.md` — how to run experiments
4. `docs/04_HOWTO_WORK.md` — this file

That is sufficient for any assistant or collaborator to fully understand the state of the project and continue without re-explaining anything.
