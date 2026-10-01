"""Chay thi nghiem LSTM du bao (spec 008).

    py -3.13 run_forecast.py --run-id lstm_v1            # chay that (hoac chay tiep)
    py -3.13 run_forecast.py --smoke                      # chay thu: 1 seed, 1 epoch

Thu tu vong lap: VONG HOC -> ban -> seed. Moi vong hoc dung mot ma tran rieng (tien xu ly
khop tren phan hoc cua vong do), nen chi giu mot ma tran trong bo nho tai mot luc.

Chay tiep (PROCESS.md muc 16): chay lai cung --run-id thi bo qua cac lan hoc da xong
(`done.json`) va chay tiep lan dang do tu `ckpt_latest.pt`. Tu choi chay tiep neu du lieu
hoac cau hinh khac luc bat dau.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import secrets
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from laplace.config import FeatureConfig
from laplace.forecast.folds import make_schedule
from laplace.forecast.labels import NO_LABEL, labels_from_ohlcv
from laplace.forecast.metrics import baseline_probs, evaluate
from laplace.forecast.prep import prepare_fold_matrix
from laplace.forecast.train import TrainConfig, predict, train_fold
from laplace.loader import load_ohlcv
from laplace.pipeline import assemble_features
from laplace.rl.device import describe, get_device
from laplace.scaling import make_split

LABEL = {"k_atr": 1.5, "horizon_bars": 24, "atr_period": 51, "cross_session": False}


def log(msg: str, logfile: Path | None = None) -> None:
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    if logfile is not None:
        with logfile.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_state() -> dict:
    def run(*a):
        try:
            return subprocess.run(["git", *a], capture_output=True, text=True).stdout.strip()
        except OSError:
            return ""
    return {"commit": run("rev-parse", "HEAD"), "dirty": bool(run("status", "--porcelain"))}


def environment(device: torch.device) -> dict:
    return {"python": platform.python_version(), "torch": torch.__version__,
            "cuda": torch.version.cuda, "device": describe(device),
            "numpy": np.__version__, "pandas": pd.__version__, "os": platform.platform()}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--run-id", default=None)
    p.add_argument("--out", default="experiments/forecast")
    p.add_argument("--seeds", type=int, default=10)
    p.add_argument("--variants", nargs="+", default=["a", "ac"])
    p.add_argument("--max-epochs", type=int, default=30)
    p.add_argument("--smoke", action="store_true", help="chay thu: 1 seed, 1 epoch")
    p.add_argument("--cpu", action="store_true")
    args = p.parse_args()

    if args.smoke:
        args.seeds, args.max_epochs = 1, 1
        args.run_id = args.run_id or f"smoke_{datetime.now():%Y%m%d_%H%M%S}"
    run_id = args.run_id or f"lstm_{datetime.now():%Y%m%d_%H%M%S}"
    root = Path(args.out) / run_id
    root.mkdir(parents=True, exist_ok=True)
    logfile = root / "run.log"
    device = torch.device("cpu") if args.cpu else get_device()
    tcfg = TrainConfig(max_epochs=args.max_epochs)
    fcfg = FeatureConfig()

    # ------------------------------------------------------------------ #
    # [1/5] Kiem tra moi truong va du lieu
    # ------------------------------------------------------------------ #
    log(f"[1/5] Moi truong: {describe(device)}", logfile)
    if not Path(fcfg.csv_path).exists():
        log(f"LOI: khong thay {fcfg.csv_path}", logfile)
        return 2
    data_hash = sha256(fcfg.csv_path)

    # ------------------------------------------------------------------ #
    # [2/5] Cau hinh thi nghiem: tao moi hoac kiem tra de chay tiep
    # ------------------------------------------------------------------ #
    cfg_path = root / "run_config.json"
    identity = {"variants": args.variants, "n_seeds": args.seeds, "train": asdict(tcfg),
                "label": LABEL, "data_sha256": data_hash,
                "split": {"train_start": fcfg.train_start, "train_end": fcfg.train_end,
                          "valid_end": fcfg.valid_end}}
    if cfg_path.exists():
        saved = json.loads(cfg_path.read_text(encoding="utf-8"))
        if saved["identity"] != identity:
            log("LOI: run-id nay da ton tai voi du lieu/cau hinh KHAC. Doi --run-id moi.", logfile)
            return 3
        seeds = saved["seeds"]
        if saved["git"]["commit"] != git_state()["commit"]:
            log("CANH BAO: code da doi commit so voi luc bat dau thi nghiem", logfile)
        log(f"[2/5] Chay tiep thi nghiem {run_id}", logfile)
    else:
        # Seed boc NGAU NHIEN (khong co dinh truoc), ghi lai ngay de chay tiep van dung no.
        seeds = {v: [secrets.randbelow(2**31 - 1) for _ in range(args.seeds)]
                 for v in args.variants}
        cfg_path.write_text(json.dumps({
            "run_id": run_id, "created": datetime.now().isoformat(), "identity": identity,
            "seeds": seeds, "git": git_state(), "environment": environment(device),
            "spec": "specs/008-lstm-du-bao.md"}, indent=2), encoding="utf-8")
        log(f"[2/5] Thi nghiem moi {run_id}, seed: {seeds}", logfile)

    # ------------------------------------------------------------------ #
    # [3/5] Dac trung (chua tia, chua scale), nhan, lich hoc
    # ------------------------------------------------------------------ #
    t0 = time.perf_counter()
    df = load_ohlcv(fcfg)
    a = assemble_features(fcfg, df)
    split = make_split(a.features.index, fcfg)
    lab = labels_from_ohlcv(a.ohlcv, LABEL["k_atr"], LABEL["horizon_bars"], LABEL["atr_period"])
    folds = make_schedule(a.features.index, split, lab.end, window=tcfg.window)
    idx = a.features.index
    log(f"[3/5] Dac trung {a.features.shape}, nhan, {len(folds)} vong hoc "
        f"({time.perf_counter() - t0:.0f}s)", logfile)
    for f in folds:
        log(f"      {f.name:9s} hoc {len(f.train_ends):6,} nen "
            f"({idx[f.train_ends].min():%Y-%m-%d} -> {idx[f.train_ends].max():%Y-%m-%d}) | "
            f"du bao {len(f.predict_ends):6,} nen "
            f"({idx[f.predict_ends].min():%Y-%m-%d} -> {idx[f.predict_ends].max():%Y-%m-%d})",
            logfile)

    # ------------------------------------------------------------------ #
    # [4/5] Hoc
    # ------------------------------------------------------------------ #
    total = len(folds) * sum(len(s) for s in seeds.values())
    done_count = 0
    for f in folds:
        x, cols = prepare_fold_matrix(a.features, f.train_mask, clip=fcfg.clip_sigma,
                                      mode=fcfg.scaler)
        base = baseline_probs(lab.label[f.train_ends][lab.label[f.train_ends] != NO_LABEL])
        for variant in args.variants:
            for k, seed in enumerate(seeds[variant]):
                done_count += 1
                d = root / variant / f"seed_{k:02d}" / f.name
                if (d / "done.json").exists():
                    log(f"[4/5] {done_count}/{total} {variant} seed_{k:02d} {f.name}: da xong, bo qua",
                        logfile)
                    continue
                t1 = time.perf_counter()
                model, hist = train_fold(x, f.train_ends, lab.label, lab.ret_atr, lab.end,
                                         variant, seed + 7919 * folds.index(f), tcfg, d, device)
                out = predict(model, x, f.predict_ends, tcfg.window, device)
                y = lab.label[f.predict_ends]
                pred = pd.DataFrame({"ts": idx[f.predict_ends], "label": y,
                                     "ret_atr": lab.ret_atr[f.predict_ends],
                                     "p_down": out["prob"][:, 0], "p_flat": out["prob"][:, 1],
                                     "p_up": out["prob"][:, 2]})
                if "ret" in out:
                    pred["ret_pred"] = out["ret"]
                pred.to_parquet(d / "pred.parquet")
                has = y != NO_LABEL
                metrics = evaluate(out["prob"][has], y[has].astype(np.int64), base)
                metrics.update(fold=f.name, variant=variant, seed=seed, n_features=len(cols),
                               best_epoch=hist["best_epoch"], stopped=hist["stopped"])
                (d / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
                (d / "done.json").write_text(json.dumps({"finished": datetime.now().isoformat()}),
                                             encoding="utf-8")
                secs = time.perf_counter() - t1
                per_epoch = np.mean([e["seconds"] for e in hist["epochs"]]) if hist["epochs"] else 0
                log(f"[4/5] {done_count}/{total} {variant} seed_{k:02d} {f.name}: "
                    f"{len(hist['epochs'])} epoch ({per_epoch:.1f}s/epoch), {secs:.0f}s | "
                    f"sai so {metrics['log_loss']:.4f} vs moc {metrics['log_loss_baseline']:.4f} "
                    f"({metrics['improvement']:+.4f})", logfile)
        del x

    # ------------------------------------------------------------------ #
    # [5/5] Tong hop tren valid 2022 (vong "final")
    # ------------------------------------------------------------------ #
    summary = {}
    for variant in args.variants:
        rows = []
        for k in range(len(seeds[variant])):
            m = root / variant / f"seed_{k:02d}" / "final" / "metrics.json"
            if m.exists():
                rows.append(json.loads(m.read_text(encoding="utf-8")))
        if not rows:
            continue
        imp = np.array([r["improvement"] for r in rows])
        ll = np.array([r["log_loss"] for r in rows])
        summary[variant] = {
            "n_seeds": len(rows), "log_loss_mean": float(ll.mean()),
            "log_loss_std": float(ll.std(ddof=1)) if len(ll) > 1 else None,
            "improvement_mean": float(imp.mean()), "seeds_better_than_baseline": int((imp > 0).sum()),
            "baseline": rows[0]["log_loss_baseline"]}
    if {"a", "ac"} <= summary.keys() and summary["a"]["log_loss_std"] is not None:
        sa, sc = summary["a"], summary["ac"]
        diff = sa["log_loss_mean"] - sc["log_loss_mean"]
        se = float(np.sqrt(sa["log_loss_std"] ** 2 / sa["n_seeds"]
                           + sc["log_loss_std"] ** 2 / sc["n_seeds"]))
        summary["ac_vs_a"] = {"ac_better_by": diff, "se": se, "beyond_2se": bool(diff > 2 * se)}
    (root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log(f"[5/5] Xong. Tong hop valid 2022: {json.dumps(summary, ensure_ascii=False)}", logfile)
    return 0


if __name__ == "__main__":
    sys.exit(main())
