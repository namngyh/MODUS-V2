# 004 — Hàm reward và môi trường vector hoá

- **Trạng thái**: xong
- **Ngày**: 2026-09-06
- **Ảnh hưởng tới**: `laplace/rl/env.py` (mới), bất biến #17. Vòng PPO để spec 005

## 1. Câu hỏi

Mạng policy đã có (spec 002) nhưng chưa có gì để nó chơi. Cần hàm reward và một môi
trường chạy được: nhận hành động, trả về trạng thái mới và điểm thưởng, cho **N môi
trường song song** trên GPU.

## Ký hiệu

| Ký hiệu | Nghĩa | Đơn vị |
|---|---|---|
| `pos_t` | Vị thế sau khi áp hành động ở bar `t`, có hiệu lực từ cuối bar `t` | −1 / 0 / +1 |
| `Δc_t` | `close_{t+1} − close_t` | điểm chỉ số |
| `ATR_e` | ATR tại bar **vào lệnh**, giữ nguyên suốt lệnh | điểm |
| `r_t` | Điểm thưởng cho hành động ở bar `t` | không đơn vị (bội số ATR) |
| `k` | Chi phí mỗi lượt giao dịch (`cost_per_turn`) | bội số ATR |

## 2. Đã chốt

### 2.1 Hàm reward

```
r_t  =  pos_t · Δc_t / ATR_e  −  k · |pos_t − pos_{t−1}|
```

**Không có thành phần rủi ro.** Người dùng chọn phương án này với lý do: quản trị rủi ro
sẽ là một **tầng riêng** đặt lên trên tín hiệu, chứ không khoá cứng vào hàm reward. Như
vậy nó áp được cho mọi tín hiệu chứ không riêng mô hình này.

**Hệ quả đã biết và đã chấp nhận** (ghi lại một lần, không nêu lại ở các spec sau): với
`k = 0` và reward thuần P&L, `E[r | vào lệnh] ≥ E[r | SKIP] = 0`, nên `π(SKIP) → 0` và
nhánh SKIP của head entry gần như không nhận gradient trong giai đoạn phát triển. Đây là
hệ quả trung thực của thiết kế, không phải lỗi.

### 2.2 Chuẩn hoá theo ATR lúc vào lệnh, không phải ATR hiện tại

ATR trung vị theo năm chạy từ **0,84 điểm (2019) tới 4,00 điểm (2026) — chênh 4,78 lần**.
Thưởng bằng điểm nghĩa là một bar năm 2026 đáng giá gấp năm lần một bar năm 2019, và agent
sẽ học chủ yếu từ những năm biến động cao.

Chọn `ATR_e` (lúc vào lệnh) chứ không phải ATR hiện tại vì hai lý do:

1. Tổng thưởng của một lệnh trở thành `(giá thoát − giá vào) / ATR_e` — đúng khái niệm
   **bội số R** mà người giao dịch vẫn nghĩ. Dùng ATR hiện tại thì tổng là
   `Σ Δc_t / ATR_t`, không phải một đại lượng có ý nghĩa gì.
2. Biến trạng thái `pos_pnl_atr` (spec 002) đã dùng `ATR_e`. Reward và state phải chung
   một mẫu số, nếu không agent nhìn thấy lãi "2 ATR" mà được thưởng theo một thang khác.

### 2.3 Thưởng mỗi bar (mark-to-market), không phải chỉ khi đóng lệnh

Bị chốt sẵn bởi thiết kế episode ở spec 002: bar cuối là *tạm dừng*, vị thế vẫn mở. Trả
thưởng chỉ lúc đóng lệnh thì một lệnh còn mở ở bar 255 **chưa từng được trả điểm nào** và
cả đoạn giữ lệnh trở thành vô hình.

Hai cách cho **cùng tổng** trên một lệnh đã đóng (chuỗi thu gọn), nhưng khác hẳn về động
lực học: thưởng dày cho tín hiệu ở mọi bước, thưởng thưa bắt agent gán công qua 40 bar.

### 2.4 Chi phí tính đúng cho hành động ghép

`k · |pos_t − pos_{t−1}|` tự xử lý đảo chiều: LONG → SHORT cho `|−1 − 1| = 2`, đúng hai
lượt giao dịch. Không cần trường hợp riêng.

`k = 0` trong giai đoạn phát triển, nhưng **tham số phải tồn tại từ đầu** để sau này thêm
phí chỉ là đổi một con số.

### 2.5 Môi trường

```
TradingEnv(matrix, ohlcv, atr, split_mask, n_env, device)
    reset()          -> chon diem bat dau ngau nhien cho tung moi truong
    step(entry_a, exit_a) -> obs, reward, truncated
```

- **Vector hoá hoàn toàn**: một lời gọi cho cả `n_env` môi trường, không vòng lặp Python
  trên chiều môi trường. Vòng lặp duy nhất là theo thời gian, và nó không bỏ được.
- Quan sát dựng bằng gather: `matrix[cursor[:, None] + offsets[None, :]]` cho ra
  `(n_env, 64, 454)` — đúng thứ `SequenceDataset` đang sinh ra.
- Mỗi môi trường có con trỏ riêng và điểm bắt đầu ngẫu nhiên riêng.
- Episode 255 bar → `truncated = True` → môi trường đó nhận điểm bắt đầu ngẫu nhiên mới.
  **Không ép đóng lệnh**; PPO bootstrap `V(s)` (spec 002 mục 2.6).

### 2.6 Thứ tự trong một bước

```
bar t:  obs_t  = [cửa sổ 64 bar kết ở t, trạng thái vị thế tại t]
        a_t    = policy(obs_t)
        pos_t  = state.apply(a_t)          <- có hiệu lực từ cuối bar t
        r_t    = pos_t · (c_{t+1} − c_t) / ATR_e  −  k·|Δpos|
        t      = t + 1
```

Thưởng cho hành động ở bar `t` thực hiện trong khoảng `t → t+1`. Không có gì nhìn tới
tương lai: `pos_t` chỉ dùng dữ liệu tới `t`, còn `Δc_t` là kết quả xảy ra **sau** quyết
định — đúng như thực tế.

## 3. Bất biến

**Bất biến mới #17 — tổng thưởng mỗi bar của một lệnh phải bằng đúng lãi lỗ thực hiện của
lệnh đó**, tính bằng bội số ATR. Đây là ràng buộc chuỗi-thu-gọn: nếu sai, agent đang được
thưởng cho một thứ không phải tiền, và mọi kết quả backtest về sau đều vô nghĩa mà không
có gì báo.

## 4. Bài test làm spec này thất bại

```
tests/test_env.py::test_reward_telescopes_to_realised_pnl
tests/test_env.py::test_reward_is_zero_while_flat
tests/test_env.py::test_reward_uses_entry_atr_not_current_atr
tests/test_env.py::test_reward_is_scale_free_across_volatility_regimes
tests/test_env.py::test_reversal_is_charged_two_turns
tests/test_env.py::test_episode_truncates_at_configured_length
tests/test_env.py::test_episode_never_leaves_its_split
tests/test_env.py::test_observation_matches_sequence_dataset
tests/test_env.py::test_step_is_vectorised_over_environments
```

- **telescopes** — bài quan trọng nhất, canh bất biến #17. Cộng dồn thưởng từng bar của
  một lệnh phải ra đúng `(giá thoát − giá vào)/ATR_e`. Lệch một bar ở chỗ nhân `pos` là
  đỏ ngay, mà nếu không có bài này thì lỗi đó im lặng hoàn toàn.
- **zero while flat** — nếu quên mask lúc FLAT, agent nhận thưởng cho vị thế nó không có
- **entry atr not current** — dùng nhầm ATR hiện tại thì tổng thưởng không còn là bội số R
- **scale free** — cùng một lệnh 2R ở vùng giá 900/ATR 3 và 1900/ATR 15 phải cho cùng thưởng
- **two turns** — với `k > 0`, đảo chiều phải bị trừ `2k` chứ không phải `k`
- **truncates / never leaves its split** — episode không được lấn sang valid hay test; đây
  là họ hàng của bất biến #5
- **matches sequence dataset** — cửa sổ môi trường dựng ra phải trùng khít cửa sổ của
  `SequenceDataset`, tức là môi trường không tự bịa ra một đường dữ liệu thứ hai
- **vectorised** — thông lượng phải giữ mức đo được ở spec 002; vòng lặp Python trên chiều
  môi trường sẽ làm nó sụt hàng chục lần

## 5. Tiêu chí chấp nhận

Thay đổi kỹ thuật, chưa có giả thuyết thị trường. Tập test: **chưa nhìn thêm lần nào**
(vẫn 1 lần, ghi ở [SO-LAN-NHIN-TAP-TEST.md](SO-LAN-NHIN-TAP-TEST.md)).

- 9 bài test ở mục 4 xanh
- 59 test hiện có vẫn xanh
- Thông lượng ≥ 20.000 bar/s ở 128 môi trường song song trên GPU — lấy từ số đo thật của
  spec 002 (23.747), không phải từ một phép đo hẹp hơn phạm vi tiêu chí
- Không vòng lặp Python trên chiều môi trường

---

## Kết quả

**Chấp nhận.** Đã làm `laplace/rl/env.py` (`TradingEnv`), `tests/test_env.py` 11 bài,
bất biến #17. **70/70 test xanh.**

| Tiêu chí | Kết quả |
|---|---|
| 9 bài test mục 4 xanh | **đạt** — 11 bài (thêm 2 bài phụ) |
| 59 test hiện có vẫn xanh | **đạt** — 70/70 |
| ≥ 20.000 bar/s ở 128 môi trường trên GPU | **đạt** — 20.626 |
| Không vòng lặp Python trên chiều môi trường | **đạt** |

Thông lượng đo đầy đủ (mạng **và** môi trường, RTX 4060):

| Môi trường song song | bar/s | Một episode 255 bar |
|---:|---:|---:|
| 32 | 5.105 | 1,60 s |
| 128 | **20.626** | 1,58 s |
| 512 | 72.777 | 1,79 s |

Thời gian mỗi episode gần như không đổi (1,58–1,79 s) ở mọi cỡ lô — vẫn là chi phí khởi
động kernel, đúng như đã thấy ở spec 002. Nên **dùng ít nhất 128 môi trường**; ở 32 thì
thông lượng chỉ còn một phần tư.

Lần này tiêu chí thông lượng **đặt đúng**: tôi lấy 20.000 từ số đo thật của spec 002
(23.747) chứ không phải từ một phép đo hẹp hơn phạm vi tiêu chí. Kết quả 20.626 sát ngưỡng
— thấp hơn 23.747 vì môi trường thật tốn hơn môi trường tổng hợp dùng lúc benchmark.

### Hai lỗi tự bắt trong lúc làm

1. Một dòng rác `if False else` còn sót trong `step()` — đã dọn.
2. Test cắt episode đếm thừa một vòng: môi trường cắt đúng ở 255 bước, test đếm thành 256.
   Lỗi ở test, không phải ở code.

### Bổ sung sau khi làm xong: tách `profit` khỏi `reward`

Người dùng yêu cầu phân biệt rõ hai từ, và đo lại cho thấy đây không phải chuyện chữ nghĩa:

```
KESPT — tỷ lệ R trên mỗi điểm:  0,26 (2017) → 1,34 (2019)     chênh 5,2 lần
tương quan profit năm với reward năm:  chỉ 0,748

xếp hạng năm theo profit:  2025, 2020, 2021, 2018
xếp hạng năm theo reward:  2018, 2020, 2019, 2021
```

2025 là năm tốt nhất tính theo profit nhưng **không lọt top-4** theo reward. Câu *"reward
tăng 20%"* không nói được gì về tiền.

Đã sửa: `TradingEnv` nay trả về **cả hai** — `reward` (bội số ATR, để huấn luyện) và
`env.profit_points` (điểm, để đánh giá). Biến `pnl` trong `step()` — đúng cái tên mà quy
ước mới cấm vì không nói đơn vị — đã đổi thành `r_atr`. Thêm `profit_from()` bên cạnh
`reward_from()`, và hai bài test canh việc hai đại lượng không bị lẫn.

Quy ước từ vựng đầy đủ nằm ở mục "Từ vựng" đầu CLAUDE.md.

### Còn treo sang spec 005

- `flow__buy_px_edge`, `flow__sell_px_edge`, `flow__px_spread` gần như không mang thông
  tin trên đường CSV (spec 003) — bỏ hay giữ, chưa quyết.
- Vòng PPO: GAE, cắt tỷ lệ, bootstrap tại điểm tạm dừng, behavior cloning để warm-start.
