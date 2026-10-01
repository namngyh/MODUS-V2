"""Hoc mot lan (mot ban x mot seed x mot vong) cho LSTM du bao (spec 008).

Checkpoint (PROCESS.md muc 15-21):
  - `ckpt_latest.pt` sau MOI epoch: mang, optimizer, epoch, so epoch khong tot len, lich su
  - `ckpt_best.pt` khi sai so tren phan canh dung tot len
  - ghi nguyen tu: ghi file tam roi doi ten, nen tat may giua luc ghi khong pha checkpoint cu
  - chay lai cung lenh thi chay tiep tu `latest`

Thu tu xao tron cua moi epoch sinh tu (seed, epoch) chu khong tu bo sinh so ngau nhien
toan cuc: nho vay "hoc 4 epoch lien" va "hoc 2 epoch, dung, chay tiep" cho cung mot ket qua.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from .folds import split_train_holdout
from .labels import NO_LABEL
from .model import ForecastNet


@dataclass
class TrainConfig:
    window: int = 64
    max_epochs: int = 30
    patience: int = 3              # dung khi 3 epoch lien khong tot len
    batch: int = 512
    lr: float = 1e-3
    holdout_frac: float = 0.1      # 10 % cuoi phan hoc de canh dung
    weight_c: float = 1.0          # ty le hoc (a) : (c) = 1 : 1
    huber_delta: float = 1.0       # don vi ATR
    grad_clip: float = 1.0


def _atomic_save(obj: dict, path: Path) -> None:
    tmp = path.with_suffix(".tmp")
    torch.save(obj, tmp)
    os.replace(tmp, path)


def _windows(x: torch.Tensor, ends: torch.Tensor, offsets: torch.Tensor) -> torch.Tensor:
    return x[ends[:, None] + offsets[None, :]]


def _batches(n: int, size: int, order: torch.Tensor | None = None):
    idx = order if order is not None else torch.arange(n)
    for s in range(0, n, size):
        yield idx[s:s + size]


def _loss(model: ForecastNet, out: dict, y: torch.Tensor, r: torch.Tensor,
          cfg: TrainConfig) -> tuple[torch.Tensor, torch.Tensor]:
    ce = nn.functional.cross_entropy(out["logits"], y)
    if model.head_c is None:
        return ce, ce
    hub = nn.functional.huber_loss(out["ret"], r, delta=cfg.huber_delta)
    return ce + cfg.weight_c * hub, ce


@torch.no_grad()
def _holdout_ce(model, x, ends, y, offsets, batch) -> float:
    model.eval()
    total, n = 0.0, 0
    for b in _batches(len(ends), batch * 4):
        out = model(_windows(x, ends[b], offsets))
        total += nn.functional.cross_entropy(out["logits"], y[b], reduction="sum").item()
        n += len(b)
    model.train()
    return total / n


def train_fold(x: np.ndarray, train_ends: np.ndarray, label: np.ndarray, ret: np.ndarray,
               end: np.ndarray, variant: str, seed: int, cfg: TrainConfig,
               ckpt_dir: str | Path, device: torch.device) -> tuple[ForecastNet, dict]:
    """Hoc mot lan. Tra ve (mang voi trong so TOT NHAT tren phan canh dung, lich su)."""
    ckpt_dir = Path(ckpt_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    ok = label[train_ends] != NO_LABEL
    if variant == "ac":
        ok &= np.isfinite(ret[train_ends])
    fit, hold = split_train_holdout(train_ends[ok], end, cfg.holdout_frac)

    xt = torch.as_tensor(x, dtype=torch.float32, device=device)
    offsets = torch.arange(-cfg.window + 1, 1, device=device)
    y_all = torch.as_tensor(np.where(label == NO_LABEL, 0, label), dtype=torch.long, device=device)
    r_all = torch.as_tensor(np.nan_to_num(ret), dtype=torch.float32, device=device)
    fit_t = torch.as_tensor(fit, device=device)
    hold_t = torch.as_tensor(hold, device=device)

    torch.manual_seed(seed)
    model = ForecastNet(x.shape[1], variant).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=cfg.lr)
    identity = {"variant": variant, "seed": seed, "n_features": int(x.shape[1]),
                "n_fit": int(len(fit)), "n_hold": int(len(hold))}

    state = {"epoch": 0, "best": float("inf"), "bad": 0, "history": []}
    latest, best_path = ckpt_dir / "ckpt_latest.pt", ckpt_dir / "ckpt_best.pt"
    resumed_from = None
    if latest.exists():
        ck = torch.load(latest, map_location=device, weights_only=False)
        if ck["identity"] != identity:
            raise RuntimeError(f"checkpoint {latest} khong khop cau hinh: {ck['identity']} "
                               f"!= {identity}. Khong chay tiep tren checkpoint cua lan khac.")
        model.load_state_dict(ck["model"])
        opt.load_state_dict(ck["optimizer"])
        state = ck["state"]
        resumed_from = state["epoch"]

    model.train()
    while state["epoch"] < cfg.max_epochs and state["bad"] < cfg.patience:
        t0 = time.perf_counter()
        gen = torch.Generator().manual_seed(seed * 1_000_003 + state["epoch"])
        order = torch.randperm(len(fit_t), generator=gen).to(device)
        run_loss, n = 0.0, 0
        for b in _batches(len(fit_t), cfg.batch, order):
            e = fit_t[b]
            out = model(_windows(xt, e, offsets))
            loss, _ = _loss(model, out, y_all[e], r_all[e], cfg)
            opt.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
            opt.step()
            run_loss += loss.item() * len(b)
            n += len(b)
        hold_ce = _holdout_ce(model, xt, hold_t, y_all[hold_t], offsets, cfg.batch)
        if device.type == "cuda":
            torch.cuda.synchronize()
        state["epoch"] += 1
        improved = hold_ce < state["best"] - 1e-6
        if improved:
            state["best"], state["bad"] = hold_ce, 0
            _atomic_save({"model": model.state_dict(), "identity": identity,
                          "epoch": state["epoch"], "hold_ce": hold_ce}, best_path)
        else:
            state["bad"] += 1
        state["history"].append({"epoch": state["epoch"], "train_loss": run_loss / n,
                                 "hold_ce": hold_ce, "seconds": time.perf_counter() - t0})
        _atomic_save({"model": model.state_dict(), "optimizer": opt.state_dict(),
                      "state": state, "identity": identity, "config": asdict(cfg)}, latest)

    best = torch.load(best_path, map_location=device, weights_only=False)
    model.load_state_dict(best["model"])
    model.eval()
    history = {"identity": identity, "config": asdict(cfg), "best_epoch": best["epoch"],
               "best_hold_ce": best["hold_ce"], "epochs": state["history"],
               "stopped": "patience" if state["bad"] >= cfg.patience else "max_epochs",
               "resumed_from_epoch": resumed_from}
    (ckpt_dir / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
    return model, history


@torch.no_grad()
def predict(model: ForecastNet, x: np.ndarray, ends: np.ndarray, window: int,
            device: torch.device, batch: int = 4096) -> dict:
    model.eval()
    xt = torch.as_tensor(x, dtype=torch.float32, device=device)
    offsets = torch.arange(-window + 1, 1, device=device)
    ends_t = torch.as_tensor(ends, device=device)
    probs, rets = [], []
    for b in _batches(len(ends_t), batch):
        out = model(_windows(xt, ends_t[b], offsets))
        probs.append(out["prob"].cpu())
        if "ret" in out:
            rets.append(out["ret"].cpu())
    res = {"prob": torch.cat(probs).numpy()}
    if rets:
        res["ret"] = torch.cat(rets).numpy()
    return res
