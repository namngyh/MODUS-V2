"""Vong huan luyen PPO (spec 005).

Diem de sai nhat cua ca module nay: **thi truong khong bao gio "ket thuc"**. Bar 256 van
ton tai, gia van chay. Nen moi ranh gioi episode chi la TAM DUNG (truncation), khong phai
KET THUC (termination), va hai thu do doi hoi cach xu ly khac nhau:

    delta_t = r_t + gamma*V(s_{t+1}) - V(s_t)        <- LUON bootstrap, khong bao gio gan 0
    A_t     = delta_t + gamma*lam*A_{t+1}*(1 - cut)  <- CAT chuoi de quy tai ranh gioi

Gop hai mat na nay lam mot la loi im lang: ham gia tri bi keo lech o moi trang thai gan
ranh gioi, ma diem cat lai ngau nhien nen sai lech trai deu len toan bo du lieu.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import torch
import torch.nn as nn

from .env import TradingEnv
from .policy import Policy


@dataclass
class PPOConfig:
    n_steps: int = 64             # so bar thu moi lan cap nhat, tren MOI moi truong
    n_epochs: int = 4
    minibatch: int = 1024
    lr: float = 3e-4
    gamma: float = 0.99
    lam: float = 0.95             # tham so lam muot cua GAE
    clip_eps: float = 0.2
    entropy_coef: float = 0.01
    value_coef: float = 0.5
    max_grad_norm: float = 0.5


def compute_gae(rewards: torch.Tensor, values: torch.Tensor, next_values: torch.Tensor,
                cut: torch.Tensor, gamma: float, lam: float):
    """Generalized Advantage Estimation, co xu ly tam dung cho dung.

    Bon doi so dau deu co dang (T, N). `next_values[t]` phai la `V(s_{t+1})` cua trang
    thai TIEP DIEN THAT - nguoi goi chiu trach nhiem tinh no truoc khi reset moi truong
    nao.

    Nhan tham so nay tuong minh chu khong tu suy ra `values[t + 1]` chinh la de trach
    nhiem do khong bi giau di: tai bar tam dung, `values[t + 1]` la gia tri cua trang
    thai SAU KHI RESET - mot diem bat dau ngau nhien moi, thuoc quy dao hoan toan khac.

    `cut[t]` = True nghia la sau bar t co mot ranh gioi (het episode hoac het rollout).
    Tai do van bootstrap, nhung KHONG cho advantage lan nguoc qua.
    """
    adv = torch.zeros_like(rewards)
    carry = torch.zeros_like(rewards[0])
    keep = (~cut).to(rewards.dtype)

    for t in reversed(range(rewards.shape[0])):
        delta = rewards[t] + gamma * next_values[t] - values[t]
        carry = delta + gamma * lam * carry * keep[t]
        adv[t] = carry
    return adv, adv + values


class PPOTrainer:
    def __init__(self, policy: Policy, env: TradingEnv, cfg: PPOConfig | None = None,
                 device: torch.device | str = "cpu"):
        self.policy, self.env = policy, env
        self.cfg = cfg or PPOConfig()
        self.device = torch.device(device)
        self.policy.to(self.device)
        self.optimizer = torch.optim.Adam(self.policy.parameters(), lr=self.cfg.lr)
        self.obs = self.env.reset()
        self.total_steps = 0

    # ------------------------------------------------------------------ #
    def log_prob_of(self, win, state_vec, position, entry_a, exit_a) -> torch.Tensor:
        """Log-prob cua hanh dong da chon, gop dung cac head DA duoc dung.

        Bar dao chieu dung ca hai head nen co hai so hang; bar HOLD chi co mot. Lay
        thieu mot so hang lam ty le importance sai ma khong co gi bao (spec 002).
        """
        log_prob, _, _ = self.policy.evaluate_actions(win, state_vec, position,
                                                      entry_a, exit_a)
        return log_prob

    def policy_loss(self, ratio: torch.Tensor, advantage: torch.Tensor) -> torch.Tensor:
        """Muc tieu cat cua PPO: advantage lon den may cung khong keo ratio ra ngoai bien."""
        clipped = ratio.clamp(1 - self.cfg.clip_eps, 1 + self.cfg.clip_eps)
        return -torch.min(ratio * advantage, clipped * advantage).mean()

    # ------------------------------------------------------------------ #
    @torch.no_grad()
    def collect(self) -> dict:
        """Thu `n_steps` bar tren moi moi truong."""
        c, env = self.cfg, self.env
        buf = {k: [] for k in ("win", "sv", "pos", "entry", "exit", "logp",
                               "value", "reward", "cut", "profit")}
        pre_reset, truncations = [], []

        for step in range(c.n_steps):
            win, sv = self.obs
            pos = env.state.position.clone()
            out = self.policy.act(win, sv, pos)

            self.obs, reward, truncated = env.step(out.entry_action, out.exit_action)

            for k, v in (("win", win), ("sv", sv), ("pos", pos),
                         ("entry", out.entry_action), ("exit", out.exit_action),
                         ("logp", out.log_prob), ("value", out.value),
                         ("reward", reward), ("profit", env.profit_points)):
                buf[k].append(v)

            # Het rollout cung la mot ranh gioi, khong chi rieng het episode.
            buf["cut"].append(truncated | (step == c.n_steps - 1))
            truncations.append(truncated)

            if truncated.any():
                # Tinh V cua trang thai TIEP DIEN THAT truoc khi reset. Chi tinh khi that
                # su co moi truong tam dung - voi bar binh thuong thi values[t+1] da la
                # dung gia tri do roi, khong can them mot luot forward nao.
                pre_reset.append(self.policy.logits(*self.obs)[2])
                self.obs = env.reset(truncated)
            else:
                pre_reset.append(None)

        last_value = self.policy.logits(*self.obs)[2]
        out = {k: torch.stack(v) for k, v in buf.items()}
        values = out["value"]

        # next_values[t] = V(s_{t+1}) cua trang thai tiep dien that. Voi bar binh thuong
        # do dung la values[t+1]; voi bar tam dung phai lay ban tinh truoc khi reset, vi
        # values[t+1] luc do la gia tri cua diem bat dau ngau nhien moi (bat bien #18).
        next_values = torch.cat([values[1:], last_value.unsqueeze(0)], dim=0)
        for t, (pre, trunc) in enumerate(zip(pre_reset, truncations)):
            if pre is not None:
                next_values[t] = torch.where(trunc, pre, next_values[t])
        out["next_value"] = next_values

        adv, ret = compute_gae(out["reward"], values, next_values, out["cut"],
                               c.gamma, c.lam)
        out["advantage"], out["returns"] = adv, ret
        self.total_steps += c.n_steps * env.n_env
        return out

    # ------------------------------------------------------------------ #
    def update(self, batch: dict) -> dict:
        c = self.cfg
        flat = lambda x: x.reshape(-1, *x.shape[2:])
        win, sv = flat(batch["win"]), flat(batch["sv"])
        pos, entry_a, exit_a = flat(batch["pos"]), flat(batch["entry"]), flat(batch["exit"])
        old_logp, adv, ret = flat(batch["logp"]), flat(batch["advantage"]), flat(batch["returns"])

        # Chuan hoa advantage trong lo: giu cho do lon cua buoc cap nhat khong phu thuoc
        # vao viec doan nay thi truong dang bien dong manh hay yeu.
        adv = (adv - adv.mean()) / (adv.std() + 1e-8)

        n = win.shape[0]
        stats = {}
        for _ in range(c.n_epochs):
            for idx in torch.randperm(n, device=win.device).split(c.minibatch):
                # Mot luot forward duy nhat cho ca ba dai luong.
                logp, entropy, value = self.policy.evaluate_actions(
                    win[idx], sv[idx], pos[idx], entry_a[idx], exit_a[idx])
                ratio = (logp - old_logp[idx]).exp()

                p_loss = self.policy_loss(ratio, adv[idx])
                v_loss = nn.functional.mse_loss(value, ret[idx])
                entropy = entropy.mean()

                loss = p_loss + c.value_coef * v_loss - c.entropy_coef * entropy
                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.policy.parameters(), c.max_grad_norm)
                self.optimizer.step()

                stats = {"loss": loss.item(), "policy_loss": p_loss.item(),
                         "value_loss": v_loss.item(), "entropy": entropy.item()}
        return stats

    def train(self, total_steps: int, log_every: int = 10):
        """Chay cho toi khi du `total_steps` bar. Tra ve nhat ky huan luyen."""
        history = []
        rollout = 0
        while self.total_steps < total_steps:
            batch = self.collect()
            stats = self.update(batch)
            rollout += 1
            stats.update(steps=self.total_steps,
                         reward_mean=float(batch["reward"].mean()),
                         profit_points=float(batch["profit"].sum()))
            history.append(stats)
            if log_every and rollout % log_every == 0:
                print(f"  {self.total_steps:>9,} buoc | loss {stats['loss']:+.4f} "
                      f"| entropy {stats['entropy']:.3f} "
                      f"| reward TB {stats['reward_mean']:+.5f}")
        return history
