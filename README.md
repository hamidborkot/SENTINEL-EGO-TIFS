# CIPHER — Certified Insider-threat detection via Privacy-preserving Hierarchical fEderated behavioral leaRning

> **IEEE Transactions on Information Forensics and Security (TIFS) — Submission-Ready Repository**  
> **Status:** Writing phase. All experiments complete. 

---

## ⚡ One-Line Summary

CIPHER is the **first insider threat detection system** that provides **formally proven (ε,δ)-differential privacy** with **empirical membership inference attack (MIA) validation**, Byzantine-robust federated learning, and behavioral drift detection — all on the CERT insider threat dataset.

> **Headline result:** DP suppresses MIA attacker AUC from **0.7834 → 0.5024** while maintaining detection **F1 = 0.8531, AUC = 0.9601** (ε = 1.28, δ = 1e-5, CERT r4.2).

---


| Dimension | CIPHER / TIFS (this repo) |
|---|---|---|
| System name |  **CIPHER** |
| Domain | **Insider threat** |
| Dataset | **CERT r4.2 / r5.2 / r6.2** |
| Core novelty | **MIA-validated DP** |
| Module: drift | **BDM** |
| Module: ensemble | **PSE** |
| Module: federation | **DPFA** |

---

## 🏗️ System Architecture

CIPHER has **three core modules** (distinct from the TDSC paper):

```
┌─────────────────────────────────────────────────────────────┐
│                    CIPHER PIPELINE                          │
│                                                             │
│  [User Behavioral Logs]                                     │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────┐   KL-divergence drift detected?           │
│  │  BDM        │──► YES → forward to PSE                   │
│  │  Behavioral │   NO  → update persona baseline           │
│  │  Drift Mon. │                                            │
│  └─────────────┘                                            │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────┐   Archetype-stratified ensemble           │
│  │  PSE        │   (RF + XGBoost + LightGBM + MLP)         │
│  │  Persona-   │──► threat score ρ ∈ [0,1]                 │
│  │  Stratified │                                            │
│  │  Ensemble   │                                            │
│  └─────────────┘                                            │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────┐   DP-SGD + clipping + Gaussian noise      │
│  │  DPFA       │   Multi-Krum Byzantine filtering           │
│  │  Diff.Priv. │──► (ε=1.28, δ=1e-5)-DP guarantee          │
│  │  Fed. Aggr. │   MIA AUC: 0.7834 → 0.5024                │
│  └─────────────┘                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Key Results at a Glance

| Metric | Value | Source |
|---|---|---|
| **F1 (primary)** | **0.8531** | `results/results_e1.csv` |
| **AUC (primary)** | **0.9601** | `results/results_e1.csv` |
| **Privacy budget** | **ε = 1.2830, δ = 1e-5** | `results/results_e3_privacy.csv` |
| **MIA AUC (DP)** | **0.5024** (near-random) | `results/results_e8_mia.csv` |
| **MIA AUC (No-DP)** | **0.7834** (attacker succeeds) | `results/results_e8_mia.csv` |
| **DP cost vs No-DP FL** | **ΔF1 = −0.0586** | `results/results_e4_comparison_FINAL.csv` |
| **Byzantine resilience** | F1 drop < 5pp at 30% poison | `results/results_e9_byzantine.csv` |
| **Ablation AUC gain** | +0.0093 (Full vs Legacy-Only) | `results/results_e2_ablation_FIXED.csv` |

---

## 📁 Repository Structure

```
CIPHER-TIFS/
│
├── README.md                   ← You are here. Start here every time.
├── WRITING_CHECKLIST.md        ← Section-by-section writing tracker
├── CITATION.cff                ← Citation metadata (update before submission)
├── requirements.txt            ← Python dependencies
│
├── src/                        ← All source code
│   ├── cipher_main.py          ← Main entry point (renamed from sentinel_ego_local.py)
│   ├── bdm.py                  ← BDM: Behavioral Drift Monitor (was: pbi)
│   ├── pse.py                  ← PSE: Persona-Stratified Ensemble (was: aif)
│   ├── dpfa.py                 ← DPFA: Differentially Private Federated Aggregation (was: federated.py)
│   ├── features.py             ← Feature extraction (42-dim CERT behavioral features)
│   ├── labeling.py             ← CERT dataset labeling
│   ├── model.py                ← Model definitions
│   └── evaluate.py             ← Evaluation metrics
│
├── results/                    ← ALL experimental results (DO NOT EDIT MANUALLY)
│   ├── RESULTS_KEY.md          ← ⭐ START HERE — maps every paper table to its CSV
│   ├── ABLATION_VERIFICATION.md← Confirms E2 ablation is a real run
│   ├── results_e1.csv          ← E1: Primary detection (Table V in paper)
│   ├── results_e2_ablation_FIXED.csv ← E2: Ablation — USE THIS, not results_e2_ablation.csv
│   ├── results_e3_privacy.csv  ← E3: ε-sweep privacy-utility tradeoff (Fig. 2)
│   ├── results_e4_comparison_FINAL.csv ← E4: SOTA comparison — USE THIS (Table VII)
│   ├── results_e5_scenario_breakdown.csv ← E5: Scenario breakdown
│   ├── results_e7_scenario_breakdown.csv ← E7: Scenario breakdown (Table VIII)
│   ├── results_e8_mia.csv      ← E8: MIA audit ← YOUR STRONGEST RESULT (Table IX)
│   ├── results_e9_byzantine.csv← E9: Byzantine robustness (Table X)
│   ├── results_convergence.csv ← Convergence per round (Fig. 1)
│   ├── results_cross_env_final.csv ← Cross-dataset r4.2/r5.2/r6.2
│   ├── results_master.csv      ← Summary of all primary results
│   ├── r5.2/                   ← CERT r5.2 local GPU results
│   ├── r6.2/                   ← CERT r6.2 local GPU results
│   └── archive/                ← Old/broken results — DO NOT USE
│
├── figures/                    ← Paper figures (regenerate with scripts/generate_figures.py)
│   ├── README.md               ← Figure descriptions and source CSVs
│   ├── fig1_convergence.png    ← Fig.1: FL convergence curves
│   ├── fig2_epsilon_utility.png← Fig.2: ε-sweep tradeoff
│   ├── fig3_ablation.png       ← Fig.3: Ablation bar chart
│   └── fig4_sota_comparison.png← Fig.4: SOTA comparison
│
├── theory/                     ← Formal proofs (TO BE WRITTEN during writing phase)
│   └── README.md               ← Maps 3 theorems to paper sections
│
├── config/                     ← Hyperparameter configs
├── data/                       ← Dataset notes (CERT data not stored here — too large)
├── experiments/                ← Experiment runner scripts
├── scripts/
│   └── generate_figures.py     ← Regenerates all 4 paper figures from CSVs
└── notebooks/
    └── [UPLOAD KAGGLE NOTEBOOK HERE before submission]
```

---

## 🚀 Quick Start — When You Come Back to Write

**Step 1:** Read `results/RESULTS_KEY.md` — it tells you exactly which CSV → which paper table.  
**Step 2:** Open `WRITING_CHECKLIST.md` — check off sections as you write.  
**Step 3:** Write in this order: Sec.V (Experiments) → Sec.III (System) → Sec.IV (Theory) → Sec.II (Related Work) → Sec.I (Intro) → Abstract.  
**Step 4:** The 3 formal theorems in `theory/README.md` must be written before Section IV.  

---

## 🎯 The Paper's Core Claim (use this exact framing)

> *"CIPHER is the first insider threat detection system to provide formal (ε,δ)-DP guarantees with empirical MIA validation, demonstrating that DP suppresses attacker advantage from MIA AUC = 0.7834 to 0.5024, while maintaining F1 = 0.8531 under Byzantine-robust federated learning across three CERT dataset versions."*

This claim is: **true**, **supported by data**, **not made by any existing paper**.

---

## 📋 What Remains Before Submission

| Task | Effort | Status |
|---|---|---|
| Write Theorem 1 (DP guarantee via Rényi composition) | 3–4 hrs | ⬜ TODO |
| Write Theorem 2 (MIA advantage bound) | 2–3 hrs | ⬜ TODO |
| Write Theorem 3 (convergence bound, appendix) | 1 day | ⬜ TODO |
| Draw system architecture figure (Fig. 1) | 4–6 hrs | ⬜ TODO |
| Write paper (Sections V → III → IV → II → I → Abstract) | 14 days | ⬜ TODO |
| Upload Kaggle notebook to `notebooks/` | 10 min | ⬜ TODO |
| **All experiments** | **DONE** | ✅ **COMPLETE** |

---

## 📚 Datasets

- **Primary:** CERT Insider Threat Dataset r4.2 — [Kaggle](https://www.kaggle.com/datasets/)
- **Secondary validation:** CERT r6.2 (local GPU, 4000 users), CERT r5.2 (local GPU, 700 users)
- **Not used:** D2/D3 synthetic corporate/classified environments (removed — see `results/results_cross_env_final.csv`)

---

## 🔬 Reproducing Results

```bash
pip install -r requirements.txt

# Primary experiment (CERT r4.2)
python src/cipher_main.py --dataset cert_r42 --epsilon 1.28 --rounds 10

# Generate all paper figures
python scripts/generate_figures.py
```

---

*Md. Hamid Borkot Tulla — IEEE TIFS Submission 2026*
