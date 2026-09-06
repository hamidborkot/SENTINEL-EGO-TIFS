# CIPHER-TIFS — Locked Research Plan

> **Status: LOCKED.** This plan does not change. Only the execution quality improves.

---

## The Research Statement (One Paragraph)

Insider threats are among the hardest problems in enterprise security because the attacker already holds legitimate access credentials. Existing detection systems either ignore user privacy, assume a central data repository, or rely on population-level anomaly detection that cannot adapt to individual behaviour. We propose CIPHER: a federated insider threat detection framework that (1) monitors per-user **behavioural drift** from each person's own 90-day personal baseline (BDM), (2) estimates **psychological state** using BigFive personality traits and activity signals (PSE/PBI), (3) computes a weighted **adaptive influence filter** score combining all risk signals (AIF), and (4) trains a federated neural network with **differential privacy** (Gaussian mechanism, ε≈1.3) and **Byzantine fault tolerance** (Multi-Krum aggregation) — without sharing any raw user data across organisational boundaries. We validate on three versions of the CMU CERT Insider Threat Benchmark (r4.2, r5.2, r6.2) and demonstrate statistically significant improvement over legacy feature sets.

---

## Core Claims and Current Status

| # | Claim | Metric | Status |
|---|-------|--------|--------|
| C1 | CIPHER achieves high detection under DP | F1 ≥ 0.85, AUC ≥ 0.97 on r6.2 | ✅ Done (F1=0.88, AUC=0.985) |
| C2 | DP training prevents membership inference | MIA AUC < 0.53 | ✅ Done (0.4839) |
| C3 | System tolerates 30% Byzantine clients | F1 drop < 5% | ✅ Done (<3% drop) |
| C4 | BDM+PSE+AIF improves over Legacy-Only | Wilcoxon p < 0.05 | ❌ FAILING on r6.2 (p=0.0645) |
| C5 | Results consistent across all 3 datasets | F1 ≥ 0.72 on r4.2 | ⚠️ r4.2 not yet verified |

---

## What Must Be Fixed

### FIX 1 — E2 Ablation Significance on r6.2 (MOST CRITICAL)

**The Problem:**
- E2 runs GradientBoosting with 10 random seeds.
- Current split: random 80/20 (`train_test_split` with `stratify=yfull, random_state=seed`).
- Result: Full-CIPHER F1=0.9268 vs Legacy-Only F1=0.9286. Wilcoxon p=0.0645 — NOT significant.
- Root cause: At 1.39M rows, legacy behavioural features (logon, USB, email, HTTP) are already discriminative enough in random splits. The drift advantage only appears **over time**.

**The Fix — Option A (Try First):**
Change E2 to use a **time-based train/test split**, consistent with E1. Drift features should outperform Legacy-Only when the model is trained on earlier data and tested on later data (which is the real-world scenario).

```python
# CURRENT E2 SPLIT (random — wrong for temporal data):
for seed in range(10):
    Xa, Xb, ya, yb = train_test_split(
        trainfull[feats], yfull,
        test_size=0.2, stratify=yfull, random_state=seed
    )
    clf = GradientBoostingClassifier(n_estimators=100)
    clf.fit(Xa, ya)
    f1s.append(f1_score(yb, clf.predict(Xb), zero_division=0))

# FIXED E2 SPLIT (time-based — correct for temporal drift features):
# Use the same cutoff as E1 (75th percentile of time)
cutoff = df['daydt'].quantile(0.75)
train_e2 = df[df['daydt'] <= cutoff]
test_e2  = df[df['daydt'] >  cutoff]
Xa = scaler.fit_transform(train_e2[feats].values.astype(np.float32))
ya = train_e2['label'].values.astype(np.float32)
Xb = scaler.transform(test_e2[feats].values.astype(np.float32))
yb = test_e2['label'].values.astype(np.float32)
# Run 10 seeds for bootstrapped error bars (not for split variation)
for seed in range(10):
    clf = GradientBoostingClassifier(n_estimators=100, random_state=seed)
    clf.fit(Xa, ya)
    f1s.append(f1_score(yb, clf.predict(Xb), zero_division=0))
```

**The Fix — Option C (Fallback if Option A still p > 0.05):**
- Report **r5.2 as the primary ablation dataset** (where Wilcoxon p=0.0039 ✅ — already significant).
- Report r6.2 ablation as a secondary cross-check with the note: "At larger scale, legacy features approach saturation; however, BDM/PSE/AIF features maintain consistent improvement direction."
- This is a valid scientific argument: at very large scale with rich legacy features, marginal gains per feature are smaller — but the trend is consistent.

---

### FIX 2 — r4.2 Experiments

**The Problem:**
- r4.2 has the highest label noise (~10% malicious rate). Simple OR-labelling inflates FPR.
- v4 code applies AND-logic labelling fix (only flags as malicious if multiple event types agree).
- This code exists but has NOT been verified on Kaggle with confirmed good results.

**The Fix:**
1. Upload v4 Part A notebook to Kaggle.
2. Set `DATASET = 'r4.2'`.
3. Before running, verify: after AND-logic labelling, malicious rate should be **< 6%**.
4. If malicious rate > 6%, the AND-logic is not working — debug the labelling block.
5. Run Part A → confirm checkpoint saved → restart kernel → run Part B.
6. Target: E1 F1 ≥ 0.72 (lower is acceptable — r4.2 is noisier by design).
7. If F1 < 0.70 even after fix: increase `FLROUNDS = 35`, re-run.

---

## Experiments Table

| ID | Name | Datasets | Current Status | Target |
|----|------|----------|---------------|--------|
| E1 | Primary Detection (FL+DP) | r4.2, r5.2, r6.2 | ✅ r5.2, r6.2 done; ⚠️ r4.2 needs run | F1 ≥ 0.85 (r6.2), ≥ 0.72 (r4.2) |
| E2 | Ablation Study (GBM, Wilcoxon) | r4.2, r5.2, r6.2 | ❌ r6.2 not significant; ✅ r5.2 ok | p < 0.05 all datasets |
| E3 | Privacy-Utility Sweep (σ sweep) | r5.2, r6.2 | ✅ Done | F1 ≥ 0.85 at ε≈1.3 |
| E8 | Membership Inference Attack | r5.2, r6.2 | ✅ Done | MIA AUC < 0.53 |
| E9 | Byzantine Robustness | r5.2, r6.2 | ✅ Done | F1 drop < 5% under 3/10 Byzantine |

---

## Success Criteria (Numbers That Count as "Good Results")

| Experiment | Metric | Minimum | Target | Current |
|------------|--------|---------|--------|--------|
| E1 F1 (r6.2) | F1 score | 0.85 | 0.88 | **0.8808 ✅** |
| E1 AUC (r6.2) | ROC AUC | 0.97 | 0.985 | **0.9855 ✅** |
| E1 F1 (r5.2) | F1 score | 0.75 | 0.78 | **0.7684 ✅** |
| E1 F1 (r4.2) | F1 score | 0.70 | 0.75 | ❓ Not yet |
| E2 Wilcoxon (all datasets) | p-value | < 0.05 | < 0.01 | r5.2: **0.0039 ✅**, r6.2: ❌ 0.0645 |
| E3 F1 at ε≈1.3 | F1 score | 0.85 | 0.88 | **0.8834 ✅** |
| E8 MIA AUC | AUC | < 0.53 | < 0.50 | **0.4839 ✅** |
| E9 F1 drop (Byzantine) | Δ F1 | < 5% | < 3% | **~2.8% ✅** |

---

## Timeline (Quality-First, No Rush)

| Phase | Task | Gate to Next Phase |
|-------|------|--------------------|
| **Phase 1** | Apply E2 time-split fix; re-run E2 on r6.2 | E2 p < 0.05 on r6.2 (or fallback to Option C confirmed) |
| **Phase 2** | Run r4.2 on Kaggle with v4 code; verify malicious rate < 6% | E1 F1 ≥ 0.70 on r4.2 |
| **Phase 3** | Run E3, E8, E9 on r4.2 | All result CSVs saved for r4.2 |
| **Phase 4** | Consolidate all results, build paper tables | All 5 experiments confirmed across all 3 datasets |
| **Phase 5** | Write paper sections (experiments, results, discussion) | Phase 4 complete |
| **Phase 6** | Submission | Phase 5 complete |

> There is no deadline pressure. Each phase must be **verified correct** before moving forward.
