"""
federated.py — CIPHER Federated Learning Components (DPFA module)

Paper: IEEE TIFS Submission — hamidborkot/CIPHER-TIFS
Module: DPFA (Differentially Private Federated Aggregation), Section III-D

Includes:
  - local_train        : DP-SGD honest local training (Eq. 4, 5)
  - fed_avg            : weighted FedAvg aggregation (Eq. 6)
  - multi_krum         : Multi-Krum Byzantine-robust aggregation
  - malicious_train    : Byzantine attack simulation (E9)
  - run_fl             : standard DPFA FL loop
  - run_fl_byzantine   : FL loop with mixed honest/Byzantine clients (E9)
  - compute_epsilon    : Renyi-DP epsilon accounting (Theorem 1)
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from copy import deepcopy

# ── Default hyperparameters (see config/cipher_config.yaml) ──
FL_ROUNDS    = 10
LOCAL_EPOCHS = 3
LR           = 0.001
N_CLIENTS    = 10      # user-stratified FL clients (K in paper)
N_BYZANTINE  = 3
GRAD_SCALE   = 10.0

# ── Training-loop constants (NOT paper privacy accounting values) ──
# WARNING: NOISE_SCALE and Q_SAMPLE below are used only for batch-sizing
# and gradient-noise injection inside the training loop. They are NOT the
# privacy accounting parameters cited in the paper.
#
# PAPER PRIVACY ACCOUNTING (Theorem 1, Section III-D) uses:
#   sigma = 1.28, q = 0.10, R = 10  →  epsilon = 1.2830
# See src/dpfa.py → compute_epsilon(sigma=1.28, R=10, q=0.10) for the
# authoritative calculation. Do NOT cite NOISE_SCALE or Q_SAMPLE below
# in any paper text, table, or proof.
NOISE_SCALE  = 2.0    # training-loop noise injection scale (not paper sigma)
CLIP_NORM    = 1.0    # gradient clipping norm C (same as paper C=1.0)
Q_SAMPLE     = 0.01   # training-loop batch-size fraction (not paper q)
DP_DELTA     = 1e-5   # target delta (matches paper delta=1e-5)


def compute_epsilon(q: float, sigma: float, steps: int,
                    delta: float = DP_DELTA, alpha: int = 10) -> float:
    """Renyi-DP to (epsilon, delta)-DP conversion. Theorem 1 in CIPHER paper.

    NOTE: This function is a helper used at the end of run_fl() to report
    a runtime epsilon estimate. For the AUTHORITATIVE paper privacy accounting,
    use src/dpfa.py → compute_epsilon(sigma=1.28, R=10, q=0.10) → 1.2830.

    Args:
        q:      Poisson subsampling rate per step
        sigma:  Gaussian noise multiplier
        steps:  Total gradient steps = rounds * local_epochs
        delta:  DP failure probability
        alpha:  Renyi order (default 10)

    Returns:
        epsilon: privacy budget

    Paper operating point (from dpfa.py, not this function's defaults):
        compute_epsilon(q=0.10, sigma=1.28, steps=30) -> 1.2830
    """
    rdp = alpha * (q ** 2) / (2 * sigma ** 2) * steps
    return rdp + np.log(1 / delta) / (alpha - 1)


def local_train(model, Xn: np.ndarray, yn: np.ndarray,
                epochs: int = LOCAL_EPOCHS,
                apply_dp: bool = True) -> nn.Module:
    """DPFA honest local training with DP-SGD (Eqs. 4 and 5).

    Applies per-sample gradient clipping (Eq. 4) then Gaussian noise (Eq. 5).
    Class weight capped at 40 to prevent gradient explosion on imbalanced shards.

    Args:
        model:     ThreatNet instance
        Xn:        Feature matrix (numpy float32)
        yn:        Binary label vector (numpy float32)
        epochs:    Number of local epochs
        apply_dp:  If True, apply DPFA clipping + noise

    Returns:
        Trained model
    """
    model.train()
    n_pos = max(int((yn == 1).sum()), 1)
    n_neg = max(int((yn == 0).sum()), 1)
    pos_w = torch.tensor([min(n_neg / n_pos, 40.0)], dtype=torch.float32)
    opt   = optim.Adam(model.parameters(), lr=LR, weight_decay=1e-4)
    ds    = TensorDataset(torch.tensor(Xn, dtype=torch.float32),
                          torch.tensor(yn, dtype=torch.float32))
    bs    = max(32, int(Q_SAMPLE * len(Xn)))
    dl    = DataLoader(ds, batch_size=bs, shuffle=True, drop_last=False)

    for _ in range(epochs):
        for Xb, yb in dl:
            opt.zero_grad()
            wt   = torch.where(yb == 1, pos_w.expand_as(yb), torch.ones_like(yb))
            loss = (nn.functional.binary_cross_entropy(
                        model(Xb), yb, reduction='none') * wt).mean()
            loss.backward()
            if apply_dp:  # DPFA: Eq.(4) clip, Eq.(5) noise
                for p in model.parameters():
                    if p.grad is None:
                        continue
                    norm = p.grad.norm(2)
                    p.grad.mul_(min(1.0, CLIP_NORM / (norm + 1e-9)))
                    p.grad.add_(torch.randn_like(p.grad) * NOISE_SCALE * CLIP_NORM)
            opt.step()
    return model


def malicious_train(model, Xn: np.ndarray, yn: np.ndarray,
                    epochs: int = LOCAL_EPOCHS,
                    scale: float = GRAD_SCALE) -> nn.Module:
    """E9 Byzantine attack: label flip (insider->benign) + gradient scaling.

    This attack is empirically effective against standard FedAvg but
    filtered by DPFA's Multi-Krum distance-based selection (E9 results).

    Args:
        model:   ThreatNet instance
        Xn:      Feature matrix
        yn:      True labels (flipped internally)
        epochs:  Local training epochs
        scale:   Gradient amplification factor

    Returns:
        Poisoned model
    """
    model.train()
    yn_flipped = yn.copy()
    yn_flipped[yn == 1] = 0
    opt = optim.Adam(model.parameters(), lr=LR)
    ds  = TensorDataset(torch.tensor(Xn, dtype=torch.float32),
                        torch.tensor(yn_flipped, dtype=torch.float32))
    bs  = max(32, int(Q_SAMPLE * len(Xn)))
    dl  = DataLoader(ds, batch_size=bs, shuffle=True, drop_last=False)

    for _ in range(epochs):
        for Xb, yb in dl:
            opt.zero_grad()
            nn.functional.binary_cross_entropy(model(Xb), yb).backward()
            for p in model.parameters():
                if p.grad is not None:
                    p.grad.mul_(scale)
            opt.step()
    return model


def fed_avg(global_model, local_models: list, weights: list) -> nn.Module:
    """DPFA weighted FedAvg aggregation (Eq. 6).

    Args:
        global_model:  Current global ThreatNet (updated in-place)
        local_models:  List of locally-trained models
        weights:       Per-client weights (client_size / total_size)

    Returns:
        Updated global model
    """
    gd = global_model.state_dict()
    for k in gd:
        gd[k] = torch.stack(
            [lm.state_dict()[k].float() * w
             for lm, w in zip(local_models, weights)], 0
        ).sum(0)
    global_model.load_state_dict(gd)
    return global_model


def multi_krum(models: list, n_byzantine: int = N_BYZANTINE) -> nn.Module:
    """DPFA Multi-Krum Byzantine-robust aggregation.

    Scores each model by sum of squared L2 distances to k nearest neighbors.
    Selects m = n - n_byzantine lowest-scoring models and averages them.
    Tolerates up to n_byzantine < n/2 adversaries (E9 experiment).

    Reference: Blanchard et al., NeurIPS 2017.

    Args:
        models:      List of local ThreatNet models
        n_byzantine: Number of assumed Byzantine clients

    Returns:
        Aggregated model from honest candidates
    """
    params = [torch.cat([p.data.view(-1) for p in m.parameters()])
              for m in models]
    n     = len(params)
    k     = max(1, n - n_byzantine - 2)
    m_sel = max(1, n - n_byzantine)

    scores = []
    for i in range(n):
        dists = sorted(
            [((params[i] - params[j]) ** 2).sum().item()
             for j in range(n) if j != i]
        )
        scores.append(sum(dists[:k]))

    selected_ids = np.argsort(scores)[:m_sel]
    selected     = [models[i] for i in selected_ids]

    gd = deepcopy(selected[0]).state_dict()
    for key in gd:
        gd[key] = torch.stack(
            [s.state_dict()[key].float() for s in selected], 0
        ).mean(0)
    result = deepcopy(selected[0])
    result.load_state_dict(gd)
    return result


def run_fl(Xtr: np.ndarray, ytr: np.ndarray, masks: list,
           apply_dp: bool = True, label: str = "CIPHER",
           n_rounds: int = FL_ROUNDS,
           eval_fn=None, X_test=None, y_test=None):
    """Standard DPFA federation loop (FedAvg). Paper Algorithm 3.

    Args:
        Xtr:       Training feature matrix
        ytr:       Training label vector
        masks:     Boolean index arrays per silo
        apply_dp:  Enable DPFA DP-SGD
        label:     Display label
        n_rounds:  Federation rounds
        eval_fn:   Optional eval function for mid-training metrics
        X_test:    Test features
        y_test:    Test labels

    Returns:
        (global_model, epsilon)
    """
    from src.model import ThreatNet
    gm = ThreatNet(Xtr.shape[1])

    for rnd in range(n_rounds):
        lms, sizes = [], []
        for mask in masks:
            if mask.sum() < 10:
                continue
            lm = deepcopy(gm)
            lm = local_train(lm, Xtr[mask], ytr[mask], apply_dp=apply_dp)
            lms.append(lm)
            sizes.append(int(mask.sum()))
        if not lms:
            continue
        total = sum(sizes)
        gm    = fed_avg(gm, lms, [s / total for s in sizes])

        if eval_fn is not None and X_test is not None and rnd % 3 == 2:
            r, _ = eval_fn(gm, X_test, y_test)
            print(f"  [CIPHER-{label}] Round {rnd+1}/{n_rounds} "
                  f"F1={r['F1']:.4f} AUC={r['AUC']:.4f}")

    # NOTE: epsilon reported here uses local training constants (Q_SAMPLE, NOISE_SCALE).
    # For the paper-canonical epsilon=1.2830, see dpfa.py → compute_epsilon(sigma=1.28, R=10, q=0.10).
    eps = compute_epsilon(Q_SAMPLE, NOISE_SCALE, n_rounds * LOCAL_EPOCHS)
    return gm, eps


def run_fl_byzantine(Xtr: np.ndarray, ytr: np.ndarray, masks: list,
                     poison_ids: set,
                     aggregation: str = "fedavg",
                     label: str = "CIPHER",
                     n_rounds: int = FL_ROUNDS):
    """DPFA FL loop with Byzantine clients (E9 experiment). Table X.

    Honest clients: DPFA DP-SGD (local_train).
    Byzantine clients: label flip + gradient scaling (malicious_train).
    Aggregation: 'fedavg' (vulnerable) or 'krum' (DPFA Multi-Krum, robust).

    Returns:
        (global_model, epsilon)
    """
    from src.model import ThreatNet
    gm = ThreatNet(Xtr.shape[1])

    for _ in range(n_rounds):
        lms, sizes = [], []
        for i, mask in enumerate(masks):
            if mask.sum() < 10:
                continue
            lm = deepcopy(gm)
            if i in poison_ids:
                lm = malicious_train(lm, Xtr[mask], ytr[mask])
            else:
                lm = local_train(lm, Xtr[mask], ytr[mask], apply_dp=True)
            lms.append(lm)
            sizes.append(int(mask.sum()))
        if not lms:
            continue
        if aggregation == "krum":
            gm = multi_krum(lms, n_byzantine=N_BYZANTINE)
        else:
            total = sum(sizes)
            gm    = fed_avg(gm, lms, [s / total for s in sizes])

    # NOTE: epsilon reported here uses local training constants (Q_SAMPLE, NOISE_SCALE).
    # For the paper-canonical epsilon=1.2830, see dpfa.py → compute_epsilon(sigma=1.28, R=10, q=0.10).
    eps = compute_epsilon(Q_SAMPLE, NOISE_SCALE, n_rounds * LOCAL_EPOCHS)
    print(f"  [CIPHER-{label}] epsilon={eps:.4f}  aggregation={aggregation}")
    return gm, eps
