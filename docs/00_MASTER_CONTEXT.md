# CIPHER-TIFS — Master Research Context

> **Read this file first** in every new session or new thread. It is the single source of truth.

---

## 1. What Is This Research?

This is a research paper on **Privacy-Preserving Insider Threat Detection** using **Federated Learning (FL)** with **Differential Privacy (DP)**.

### The Core Claim (One Sentence)
> A federated, privacy-preserving insider threat detection system — combining per-user **Behavioural Drift Monitoring (BDM)**, **Psychological State Estimation (PSE)**, and an **Adaptive Influence Filter (AIF)** — can detect insider threats with high accuracy **while preserving employee privacy** and **resisting poisoning attacks**, without any centralised data collection.

### What Makes This Novel (The Unique Combination)
- **BDM (Behavioural Drift Monitor):** Tracks per-user deviation from their personal 90-day baseline using a Mahalanobis-like drift score (`pbidrift`). This is NOT population-level anomaly detection — it is individual-level.
- **PSE (Psychological State Estimation / PBI):** Uses BigFive personality traits (O, C, E, A, N) + behavioural signals to compute a per-user psychological drift score.
- **AIF (Adaptive Influence Filter):** A weighted composite alert score combining file operations, USB activity, risky web browsing, external email, and PBI drift signals (`aifscore`).
- **FL + DP + Byzantine Robustness:** All three signals are learned inside a federated neural network (ThreatNet) trained with Gaussian DP noise and Multi-Krum Byzantine-robust aggregation.

> **No prior work has combined BDM + PSE + AIF together inside a Federated + DP + Byzantine-robust framework for insider threat detection.**

---

## 2. Naming Clarification (IMPORTANT)

There are TWO different naming layers in this project:

| Layer | Name | Explanation |
|-------|------|-------------|
| Internal code | `CIPHER`, `ThreatNet`, `BDM`, `PSE`, `AIF` | Module/class names used inside the notebooks and source files |
| External paper | **Different name** (known to author) | The actual submitted/published paper title |

> ⚠️ The GitHub repo is `CIPHER-TIFS` and all code uses `CIPHER`/`ThreatNet` internally. The external paper title is different. This is intentional. Do NOT try to rename modules in the code — just keep the two layers separate.

---

## 3. Datasets (LOCKED — No New Datasets Needed)

All datasets come from the **CMU CERT Insider Threat Dataset** family.

| Dataset ID | CERT Version | Approx. Rows | Malicious Rate | Notes |
|------------|-------------|-------------|----------------|-------|
| `r4.2` | CERT v4.2 | ~300K | ~8–12% | Oldest; highest label noise; needs v4 code with AND-logic fix |
| `r5.2` | CERT v5.2 | ~692K | ~5.45% | Medium size; needs 28 FL rounds to converge |
| `r6.2` | CERT v6.2 | ~1.39M | ~2.72% | Largest; most realistic low-prevalence setting; best results |

### Why Three CERT Versions Is Enough
1. Same feature schema across all three — results differences reflect genuine dataset characteristics, not format noise.
2. They represent a progression from high-prevalence noisy scenarios (r4.2) to realistic enterprise settings (r6.2).
3. CERT is the **standard benchmark** for insider threat research — reviewers know it.
4. Adding a completely different dataset (e.g., LANL, UNSW-NB15) would require new feature engineering and is out of scope.

> ✅ **DECISION: Use r4.2, r5.2, r6.2 only. No new datasets.**

---

## 4. Repository Structure

```
CIPHER-TIFS/
├── src/
│   ├── bdm.py            # BDM module
│   └── ...               # Other source modules
├── notebooks/            # Jupyter notebooks (Part A and Part B per dataset)
├── results/              # CSV result files from experiments
├── docs/                 # ← All planning and context documents
│   ├── 00_MASTER_CONTEXT.md       # This file — read first
│   ├── 01_RESEARCH_PLAN.md        # The locked research plan
│   ├── 02_EXPERIMENTS_GUIDE.md    # How to run every experiment
│   ├── 03_DATASETS_GUIDE.md       # Dataset details and technical issues
│   └── 04_HOWTO_WORK.md           # Step-by-step working guide
└── README.md
```

---

## 5. Current Status (September 2026)

### ✅ Completed and Confirmed Working

| Item | Status | Notes |
|------|--------|-------|
| Feature extraction pipeline (Steps 1–4) | ✅ Done | BDM, PBI, AIF, PSE all compute correctly |
| GroupNorm fix (replaces BatchNorm1d) | ✅ Applied | Critical for FedAvg correctness |
| E1 Primary Detection — r6.2 | ✅ Done | F1=0.8808, AUC=0.9855 |
| E1 Primary Detection — r5.2 | ✅ Done | F1=0.7684, AUC=0.9467 |
| E3 Privacy-Utility Sweep — r5.2, r6.2 | ✅ Done | F1 barely drops at ε≈1.3 vs No-DP |
| E8 Membership Inference — r5.2, r6.2 | ✅ Done | MIA AUC 0.48–0.49 → DP effective |
| E9 Byzantine Robustness — r5.2, r6.2 | ✅ Done | <3% F1 drop under 3/10 Byzantine |

### ⚠️ Needs Fixing

| Item | Problem | Priority |
|------|---------|----------|
| E2 Ablation on r6.2 | p=0.0645, NOT significant. Full-CIPHER does not beat Legacy-Only. | **CRITICAL — Fix first** |
| r4.2 all experiments | Results are poor; v4 AND-logic fix exists but unverified on Kaggle | High |

---

## 6. Key Results So Far

### E1 — Primary Detection (tail-averaged, last 5 rounds)

| Dataset | F1 | AUC | Recall | FPR | ε (DP) |
|---------|----|-----|--------|-----|-------|
| r6.2 | **0.8808** | **0.9855** | 0.8543 | 0.0024 | 1.33 |
| r5.2 | 0.7684 | 0.9467 | 0.6808 | ~0.003 | 1.53 |
| r4.2 | TBD | — | — | — | — |

### E3 — Privacy-Utility Sweep (r6.2)

| σ (noise) | ε | F1 | AUC |
|-----------|---|----|-----|
| 8.0 | 1.28 | 0.8068 | 0.9253 |
| 2.0 | 1.29 | 0.8469 | 0.9738 |
| 0.8 | 1.33 | **0.8834** | 0.9824 |
| No-DP | ∞ | 0.8828 | 0.9898 |

> Key finding: At σ=0.8 (ε≈1.33), F1 is virtually identical to No-DP. This is a very strong result.

### E8 — Membership Inference Attack

| Dataset | MIA AUC | Verdict |
|---------|---------|---------|
| r6.2 | 0.4839 | DP effective ✅ |
| r5.2 | 0.4895 | DP effective ✅ |

### E9 — Byzantine Robustness (r6.2)

| Config | F1 | AUC |
|--------|----|-----|
| Clean (no attack) | 0.8833 | 0.9847 |
| FedAvg + 3/10 Byzantine | 0.8569 | ~0.978 |
| Multi-Krum + 3/10 Byzantine | 0.8581 | ~0.979 |

---

## 7. The Research Direction Is LOCKED

> We changed direction three times. That stops now.

**The paper is about one thing:**
*Privacy-preserving federated insider threat detection with BDM + PSE + AIF inside a DP + Byzantine-robust FL framework.*

Do not add new problem statements. Do not pivot. Do not change datasets. The job now is to **fix what is broken, verify what exists, and write the paper.**
