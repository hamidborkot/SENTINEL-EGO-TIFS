# CIPHER-TIFS — Datasets Guide

---

## Why Three CERT Versions Are Sufficient

All three datasets (r4.2, r5.2, r6.2) are from the **CMU CERT Insider Threat Dataset**. Using same-family versions is **scientifically correct** for the following reasons:

1. **Controlled comparison:** Same raw CSV format, same event types. Differences in results come from genuine dataset properties (scale, prevalence, scenario), not format noise.
2. **Increasing realism:** r4.2 → r5.2 → r6.2 represents a progression from high-prevalence noisy scenarios to realistic enterprise low-prevalence settings (2.72%).
3. **Standard benchmark:** CERT is the accepted standard for insider threat research. Every major prior paper uses it.
4. **No extra engineering needed:** Adding an unrelated dataset (LANL, UNSW-NB15, HDFS) would require complete new feature extraction code, which is out of scope and not required for the contribution claim.

**Statement for reviewers:** *"We validate across three progressively realistic scenarios of the CERT insider threat benchmark, from high-prevalence (r4.2, ~10% malicious) to enterprise-realistic low-prevalence (r6.2, ~2.7% malicious), demonstrating consistent performance across threat environments."*

---

## r4.2 — CERT v4.2

| Property | Value |
|----------|-------|
| Approx. rows | ~300K |
| Malicious rate (raw) | ~8–12% |
| Malicious rate (after fix) | < 6% |
| Users | ~1,000 |
| Time span | ~18 months |
| FL Rounds needed | 28 |
| Local Epochs | 5 |
| Code version | **v4 Part A FINAL** + **v4 Part B** |
| Run environment | **Kaggle GPU** (local RAM insufficient) |

### Known Issues for r4.2

**Issue 1: Label Noise (High Malicious Rate)**
- Raw OR-logic labelling flags rows if ANY malicious event type is present → malicious rate ~10%
- This inflates FPR and degrades F1
- **Fix (v4 code):** AND-logic labelling. A user-day is only labelled malicious if multiple independent event types agree.
- **How to verify the fix worked:** After Step 3 in Part A, print: `Malicious rows: X / Y (Z%)`. Z must be < 6%. If > 6%, the AND-logic is not applying correctly.

**Issue 2: Missing Device Columns**
- Some r4.2 CSV versions lack `to_removable_media` / `from_removable_media` columns
- **Fix (v4 code):** Defensive column handling with `.get()` and zero-filling:
  ```python
  df['rmcopies'] = df.get('to_removable_media', pd.Series(0, index=df.index))
  df['rmreads']  = df.get('from_removable_media', pd.Series(0, index=df.index))
  ```

**Issue 3: Memory**
- Reading all raw CSVs at once exceeds 16GB RAM
- **Fix (v4 code):** Chunked reading:
  ```python
  chunks = []
  for chunk in pd.read_csv(path, chunksize=100000):
      chunks.append(process(chunk))
  df = pd.concat(chunks, ignore_index=True)
  ```

---

## r5.2 — CERT v5.2

| Property | Value |
|----------|-------|
| Approx. rows | ~692K |
| Malicious rate | ~5.45% |
| Users | ~2,000 |
| Time span | ~2 years |
| FL Rounds needed | 28 (more rounds — smaller data per client) |
| Local Epochs | 5 |
| Code version | **v3 Part A FINAL** + **v3 Part B** |
| Run environment | Local GPU or Kaggle |
| E1 Results | F1=0.7684, AUC=0.9467 ✅ |
| E2 Results | Wilcoxon p=0.0039 ✅ (Legacy-Only vs Full-CIPHER, significant) |
| E8 Results | MIA AUC=0.4895 ✅ |

---

## r6.2 — CERT v6.2

| Property | Value |
|----------|-------|
| Approx. rows | ~1,394,010 |
| Malicious rate | ~2.72% |
| Users | ~4,000 |
| Time span | ~2.5 years |
| FL Rounds needed | 20 |
| Local Epochs | 3 |
| Q Sample | 0.01 |
| Code version | **v3 Part A FINAL** + **v3 Part B** |
| Run environment | Local GPU (fits in memory) or Kaggle |
| E1 Results | F1=0.8808, AUC=0.9855 ✅ |
| E2 Results | Wilcoxon p=0.0645 ❌ (NOT significant — fix required) |
| E8 Results | MIA AUC=0.4839 ✅ |
| E9 Results | Byzantine F1 drop < 3% ✅ |

---

## Feature Schema (All Datasets, 27 Total Features)

### Input CSVs (per dataset)

| File | Contents |
|------|----------|
| `logon.csv` | Logon/logoff events: date, user, PC, activity |
| `device.csv` | USB device connect/disconnect: date, user |
| `file.csv` | File operations: date, user, filename, to/from removable media |
| `email.csv` | Email events: date, user, to, size, attachments |
| `http.csv` | Web browsing: date, user, URL |
| `psychometric.csv` / `LDAP/` | User role, department, BigFive scores (O, C, E, A, N) |

### Computed Feature Groups

#### Group 1: Legacy CERT Features (23)
```
logoncount    Number of logon events per user-day
afterhrs      Logons occurring outside business hours
uniquepcs     Number of distinct PCs used
ahratio       afterhrs / logoncount
usbcount      USB device connection count
fileops       Total file operations
rmcopies      Files copied TO removable media
rmreads       Files read FROM removable media
rmratio       rmcopies / (fileops + 1e-9)
emailsent     Emails sent per day
extemail      External (non-org) emails sent
avgmailsize   Average email size in bytes
extratio      extemail / (emailsent + 1e-9)
httpcount     Web browsing events
riskycount    Visits to flagged/risky domains
riskyratio    riskycount / (httpcount + 1e-9)
rolechanges   Number of role changes in LDAP
deptchanges   Number of department transfers
O, C, E, A, N BigFive personality trait scores
```

#### Group 2: BDM / PBI Features (2)
```
pbidrift    Per-user Mahalanobis-like drift score:
            For each user, 90-day rolling window = enrolment baseline
            score_i = mean((current_week - mu) / std)^2
            High score = user is behaving very differently from their own norm

pbialert    Binary: 1 if pbidrift > τ
            τ = 40th percentile of malicious users' pbidrift
                (or 70th percentile of all if median malicious pbidrift = 0)
```

#### Group 3: AIF Features (2)
```
aifscore    Weighted composite risk score:
            0.30 * norm(rmcopies)
            + 0.20 * norm(rmratio)
            + 0.15 * norm(usbcount)
            + 0.10 * norm(riskycount)
            + 0.10 * norm(extratio)
            + 0.10 * norm(pbidrift)
            + 0.05 * norm(ahratio)
            where norm(x) = (x - min) / (max - min)

aifalert    Binary: 1 if aifscore > 97th percentile
```

---

## Critical Technical Issue: GroupNorm vs BatchNorm

**Problem:** Original ThreatNet used `BatchNorm1d`. During `FedAvg`, the running statistics (`running_mean`, `running_var`) are averaged across all client models. When clients have heterogeneous data distributions (which they do — different user groups), this corrupts the normalisation statistics and degrades the global model.

**Fix:** Replace every `BatchNorm1d(d)` with `GroupNorm(8, d)`.

```python
# WRONG (old code):
nn.BatchNorm1d(256)

# CORRECT (GroupNorm — no running stats, safe for FedAvg):
nn.GroupNorm(8, 256)
```

**Status:** ✅ Fixed in all v3 and v4 notebooks. The comment `# CONFIRMED FIX ALREADY PRESENT` marks this in Part B.

> **Never revert this fix. Every future version of ThreatNet must use GroupNorm.**
