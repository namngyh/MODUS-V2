"""Danh gia policy tren mot tap, bao cao bang DIEM (spec 005).

Quy uoc tu vung (CLAUDE.md): **profit tinh bang diem chi so, reward tinh bang boi so
ATR**. Hai dai luong nay khong ty le voi nhau - do tren bot KESPT, ty le R tren moi diem
chay tu 0,26 den 1,34 tuy nam, va xep hang cac nam theo hai thuoc do cho ra thu tu khac
nhau. Nen bao cao hieu qua LUON bang profit; reward chi giu lai de chan doan huan luyen.

Khac voi luc huan luyen, danh gia chay **tuan tu het ca tap** theo dung thu tu thoi gian:
khong cat ngau nhien, khong lap lai doan nao.
"""

from __future__ import annotations

import numpy as np
import torch

from ..config import FeatureConfig
from ..pipeline import FeatureSet
from .env import TradingEnv
from .policy import Policy
from .state import ENTRY_LONG, ENTRY_SHORT, EXIT_EXIT


@torch.no_grad()
def evaluate(policy: Policy, fs: FeatureSet, cfg: FeatureConfig, split: str = "valid",
             device: torch.device | str = "cpu", seed: int | None = None,
             max_bars: int | None = None) -> dict:
    """Chay policy het mot tap, tra ve cac chi so tinh bang diem.

    Lay mau ngau nhien tu policy chu khong lay argmax: policy la ngau nhien theo thiet
    ke, va do ban tat dinh cua no la do mot thu khac voi thu dang duoc huan luyen.
    """
    device = torch.device(device)
    policy = policy.to(device)
    # Nho tra lai che do cu. Bo qua buoc nay thi mang ket o che do eval, va lan huan
    # luyen ke tiep se nem "cudnn RNN backward can only be called in training mode" -
    # mot loi hoan toan khong lien quan gi toi cho that su sai.
    was_training = policy.training
    policy.eval()
    try:
        return _run(policy, fs, cfg, split, device, seed, max_bars)
    finally:
        policy.train(was_training)


@torch.no_grad()
def _run(policy: Policy, fs: FeatureSet, cfg: FeatureConfig, split: str,
         device: torch.device, seed: int | None, max_bars: int | None) -> dict:

    mask = np.asarray(getattr(fs.split, split))
    idx = np.flatnonzero(mask)
    first = int(idx.min()) + cfg.window - 1        # can du lich su cho cua so dau tien
    last = int(idx.max())
    n_bars = last - first
    if max_bars:
        n_bars = min(n_bars, max_bars)

    # Mot moi truong duy nhat, chay tuan tu. `episode_len` dat bang ca doan de khong co
    # ranh gioi nhan tao nao cat ngang.
    env = TradingEnv(fs, cfg, n_env=1, device=device, split=split,
                     episode_len=max(2, n_bars), seed=seed)
    env.cursor[:] = first
    env.steps[:] = 0
    env.state.reset()
    obs = env.observation()

    profit = torch.zeros(1, device=device)
    peak = torch.zeros(1, device=device)
    max_dd = 0.0
    rewards, positions, entries, exits = [], [], [], []

    for _ in range(n_bars):
        win, sv = obs
        pos_before = env.state.position.clone()
        out = policy.act(win, sv, pos_before)
        obs, reward, _ = env.step(out.entry_action, out.exit_action)

        profit += env.profit_points
        peak = torch.maximum(peak, profit)
        max_dd = min(max_dd, float(profit - peak))

        rewards.append(float(reward))
        positions.append(int(env.state.position))
        entries.append(int(out.entry_action))
        exits.append(int(out.exit_action) if bool(out.used_exit) else -1)

    pos = np.asarray(positions)
    changes = int(np.sum(pos[1:] != pos[:-1])) if len(pos) > 1 else 0
    opened = int(np.sum((pos[1:] != 0) & (pos[1:] != pos[:-1]))) if len(pos) > 1 else 0

    return {
        # --- hieu qua: bang DIEM ---
        "profit_points": float(profit),
        "max_drawdown_points": float(max_dd),
        "n_trades": opened,
        "n_position_changes": changes,
        "time_in_market": float(np.mean(pos != 0)),
        "share_long": float(np.mean(pos == 1)),
        "share_short": float(np.mean(pos == -1)),
        # --- chan doan huan luyen: KHONG phai con so thanh tich ---
        "reward_mean": float(np.mean(rewards)),
        "reward_sum": float(np.sum(rewards)),
        # --- pham vi da chay ---
        "n_bars": n_bars,
        "first_bar": first,
        "last_bar": first + n_bars,
        "split": split,
        "action_entry_long": float(np.mean(np.asarray(entries) == ENTRY_LONG)),
        "action_entry_short": float(np.mean(np.asarray(entries) == ENTRY_SHORT)),
        "action_exit": float(np.mean(np.asarray(exits) == EXIT_EXIT)),
    }


def describe(out: dict) -> str:
    """In ket qua danh gia. Profit dung truoc vi do la thuoc do hieu qua."""
    return "\n".join([
        f"  tap            : {out['split']} ({out['n_bars']:,} bar)",
        f"  PROFIT         : {out['profit_points']:+,.1f} diem",
        f"  sut giam toi da: {out['max_drawdown_points']:+,.1f} diem",
        f"  so lenh        : {out['n_trades']:,}",
        f"  co vi the      : {out['time_in_market']:.1%} "
        f"(long {out['share_long']:.1%}, short {out['share_short']:.1%})",
        f"  reward TB      : {out['reward_mean']:+.5f}  [chi de chan doan]",
    ])
