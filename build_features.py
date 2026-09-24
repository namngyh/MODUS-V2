"""CLI: dung ma tran dac trung tu file OHLC va ghi ra dia.

    python build_features.py --out data/features
    python build_features.py --window 32 --no-candles --train-end 2023-12-31
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

from laplace.config import FeatureConfig
from laplace.dataset import make_datasets, save_dataset
from laplace.pipeline import build_feature_frame

GROUPS = ("base", "candles", "cycles", "momentum", "overlap", "statistic",
          "volatility", "volume", "orderflow", "session", "bots")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--csv", default="ohlc_export.csv", help="file OHLC dau vao")
    p.add_argument("--out", default="data/features", help="thu muc ghi ket qua")
    p.add_argument("--symbol", default=None, help="loc theo ma; mac dinh lay tat ca")
    p.add_argument("--window", type=int, default=None, help="do dai chuoi dua vao mo hinh")
    p.add_argument("--bar-minutes", type=int, default=None,
                   help="kich thuoc bar dich; loader gop du lieu nguon ve day")
    p.add_argument("--horizon", type=int, default=0,
                   help="so bar nhan nhin toi tuong lai, de chua cho khi cat cua so")
    p.add_argument("--train-end", default=None, help="ngay cuoi tap train (YYYY-MM-DD)")
    p.add_argument("--valid-end", default=None, help="ngay cuoi tap valid (YYYY-MM-DD)")
    p.add_argument("--scaler", choices=("robust", "standard", "none"), default=None)
    p.add_argument("--cross-day", dest="cross_day", action="store_true", default=None,
                   help="cho cua so bac qua ranh gioi phien")
    p.add_argument("--no-cross-day", dest="cross_day", action="store_false")
    p.add_argument("--dry-run", action="store_true", help="chi in bao cao, khong ghi file")
    for g in GROUPS:
        # Ca hai chieu: mac dinh cua tung nhom nam trong FeatureConfig, nen chi co
        # --no-x se khong bat lai duoc nhom da tat mac dinh (vi du candles).
        p.add_argument(f"--{g}", dest=f"use_{g}", action="store_true",
                       help=f"bat nhom {g}")
        p.add_argument(f"--no-{g}", dest=f"use_{g}", action="store_false",
                       help=f"bo nhom {g}")
        p.set_defaults(**{f"use_{g}": None})
    return p.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> FeatureConfig:
    cfg = FeatureConfig(csv_path=args.csv, symbol=args.symbol)
    for name, value in (
        ("window", args.window), ("bar_minutes", args.bar_minutes),
        ("train_end", args.train_end),
        ("valid_end", args.valid_end), ("scaler", args.scaler),
        ("cross_day", args.cross_day),
    ):
        if value is not None:
            setattr(cfg, name, value)
    for g in GROUPS:
        chosen = getattr(args, f"use_{g}")
        if chosen is not None:
            setattr(cfg, f"use_{g}", chosen)
    return cfg


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cfg = config_from_args(args)

    if not Path(cfg.csv_path).exists():
        print(f"khong tim thay file: {cfg.csv_path}", file=sys.stderr)
        return 1

    t0 = time.perf_counter()
    fs = build_feature_frame(cfg)
    print(cfg.describe_periods())
    print()
    print(fs.report())
    print(f"\ntinh trong {time.perf_counter() - t0:.1f}s")

    datasets = make_datasets(fs, cfg, horizon=args.horizon)
    print(f"\nCua so (do dai {cfg.window}, cross_day={cfg.cross_day}, "
          f"horizon={args.horizon}):")
    for name, ds in datasets.items():
        print(f"  {name:6s} {len(ds):7,d} chuoi   "
              f"(neu vat chat hoa: {ds.nbytes_if_materialised / 1e9:.1f} GB)")

    if fs.signals is not None:
        from laplace.dataset import signals_at_ends
        sig = signals_at_ends(fs, datasets["train"].ends)
        cols = list(fs.signals.columns)
        pos = sig[:, [cols.index("kespt_pos"), cols.index("roofing_pos")]]
        agree = (pos[:, 0] == pos[:, 1]).mean()
        print(f"\nTin hieu bot tai bar cuoi cua so train: "
              f"hai bot dong thuan {agree:.1%}")

    matrix = datasets["train"].matrix
    print(f"\nMa tran 2 chieu: {matrix.shape} float32 = {matrix.nbytes / 1e6:.0f} MB")
    print(f"finite={np.isfinite(matrix).all()} "
          f"mean={matrix.mean():.3f} std={matrix.std():.3f}")

    if args.dry_run:
        print("\n--dry-run: khong ghi file")
        return 0

    out = save_dataset(fs, cfg, args.out)
    print(f"\nDa ghi vao {out.resolve()}")
    for f in sorted(out.iterdir()):
        print(f"  {f.name:20s} {f.stat().st_size / 1e6:8.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
