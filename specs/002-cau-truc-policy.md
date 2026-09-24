# 002 — Cấu trúc policy: hai head, entry và exit

- **Trạng thái**: xong
- **Ngày**: 2026-09-06
- **Ảnh hưởng tới**: `laplace/rl/` (mới), bất biến #14, spec 003 (reward)

## 1. Câu hỏi

Định nghĩa không gian hành động và trạng thái cho agent PPO giao dịch VN30F1M trên bar
5 phút. Đứng trước hàm reward, vì reward là hàm `R: S × A → ℝ` nên không viết được khi
chưa có `A`.

## 2. Đã chốt

### 2.1 Hai head, action masking, một MDP

```
FLAT (không có lệnh)  →  head ENTRY,  3 lối ra:  LONG (+1) | SHORT (−1) | SKIP (0)
đang có lệnh          →  head EXIT,   2 lối ra:  HOLD      | EXIT
```

Loại phương án "hai policy huấn luyện tách": giá trị của hành động vào lệnh là hàm của
policy thoát lệnh, nên huấn luyện tách tạo ra mục tiêu không dừng (non-stationary target).

### 2.2 Đảo chiều bằng hành động ghép, hoàn tất trong 1 bar

```
bar t   đang LONG  →  head exit  →  HOLD  →  hết bar, vẫn LONG
                                 →  EXIT  →  head entry được hỏi ngay, cùng bar t
                                             →  SKIP         →  cuối bar t: FLAT
                                             →  LONG / SHORT →  cuối bar t: vị thế mới
```

Không cho head exit một lối ra "ĐẢO CHIỀU" riêng: khi đó câu hỏi *"lúc này SHORT có tốt
không"* phải được hai head học riêng từ hai mảnh dữ liệu bị chia đôi, và hai head có thể
bất đồng mà không có cơ chế hoà giải. Hành động ghép giữ kiến thức đó ở một chỗ — head
entry vẫn quyết định chiều mới, chỉ là được hỏi sớm hơn 5 phút.

Xác suất của một bar có đảo chiều là tích hai bước:

```
log π(a_t | s_t)  =  log π_exit(EXIT | s_t)  +  log π_entry(a₂ | s′_t)
s′_t = cùng h_t, nhưng position đặt về 0
```

Entropy cộng hai phần. Không thêm tham số mạng nào — dùng lại đúng head entry.

### 2.3 Encoder: chiếu tuyến tính rồi LSTM một lớp

```
454 đặc trưng × 64 bar
        │
        ▼  Linear(454 → 64) + tanh          29.120 tham số
        ▼  LSTM(64 → 64), 1 lớp             33.024 tham số
      h_t (64)
        │
        ├─ ghép 6 biến vị thế + 4 số hạng tương tác (10 số)
        ▼
   ┌────┴─────┬──────────┐
 ENTRY(3)   EXIT(2)   VALUE(1)              tổng toàn mạng: 77.190
```

Vì sao có lớp chiếu: đưa thẳng 454 đặc trưng vào LSTM tốn 132.864 tham số, trong đó 87%
nằm ở ma trận đầu vào. Chiếu xuống 64 trước còn 62.144 — giảm hơn một nửa mà không giảm
hidden size. Ngân sách: 83.025 cửa sổ train nhưng chỉ **1.297 khối 64-bar độc lập**, nên
mọi tham số đều phải trả giá.

**Không dùng PCA để nén.** Đo trên tập valid: 64 thành phần đầu giữ 95,6% phương sai
nhưng chỉ còn **38% sức dự báo**. Các thành phần tương quan mạnh nhất với return tương
lai gồm PC #179 và #167, mỗi cái chỉ chiếm 0,01% phương sai — đúng chỗ PCA vứt đi đầu
tiên. Lớp chiếu tự học thì nén theo *điểm thưởng*, nên có thể giữ những hướng đó.

Chiều rộng lớp chiếu quét `{64, 96, 128}` trong thí nghiệm, không cố định.

### 2.4 Encoder đọc lại cửa sổ mỗi bước (cách A), không mang trạng thái

Mỗi quyết định chạy LSTM từ đầu qua đúng 64 bar. Đo trên RTX 4060, 32 môi trường song
song: cách A 0,70 s/vòng PPO, cách B (mang trạng thái) 0,31 s — B nhanh hơn 2,3×, nhưng
cách A vẫn chỉ mất **4,3 phút cho 3 triệu bước**, tức 1,1 giờ cho cả 15 lần thí nghiệm.

Tốc độ không phải ràng buộc nên chọn A vì ba ưu thế còn lại:

1. **Trí nhớ luôn đúng 64 bar.** Cách B khởi động `h = 0` đầu episode nên bar thứ 3 chỉ
   nhớ 3 bar còn bar 250 nhớ 250 — cùng tình huống thị trường lại cho `h` khác nhau tuỳ
   vị trí trong episode.
2. **Mỗi mẫu độc lập** → PPO trộn minibatch tự do, đúng như thuật toán giả định.
3. Khớp nguyên `SequenceDataset` đã có trong `dataset.py`.

### 2.5 Mười biến ghép sau encoder

Sáu biến trạng thái vị thế — thứ mà thị trường không biết, chỉ tồn tại vì agent đã hành động:

| Biến | Đơn vị | Nghĩa |
|---|---|---|
| `position` | −1 / 0 / +1 | Chiều lệnh đang cầm |
| `bars_held` | bar 5 phút, chia 51 | Đã giữ bao lâu, tính theo phần của một phiên |
| `pnl_atr` | lần ATR | Lãi lỗ chưa thực hiện chia ATR tại thời điểm vào lệnh |
| `mfe_atr` | lần ATR | Đỉnh lãi từng chạm trong lệnh này |
| `retained` | −1…1 | `pnl / max(MFE, \|pnl\|, ε)` — còn giữ bao nhiêu phần lợi nhuận đỉnh |
| `dist_stop_atr` | lần ATR | Còn bao xa tới mức dừng lỗ tham chiếu |

Chia cho ATR là bắt buộc: lãi 6 điểm khi ATR = 3 và khi ATR = 15 là hai tình huống khác
hẳn nhau. ATR lấy **tại bar vào lệnh** và giữ nguyên suốt lệnh, để mẫu số không đổi giữa
chừng làm biến nhảy khi thị trường đổi chế độ chứ không phải khi lệnh thay đổi.

**`retained` chặn trong [−1, 1], không cần quy ước cho trường hợp suy biến.** Mẫu số lấy
`max(MFE, |pnl|, ε)`: khi `MFE > |pnl|` nó là tỷ lệ giữ đỉnh đúng nghĩa; khi `|pnl| ≥ MFE`
nó bằng ±1 = "đang ở điểm tốt/tệ nhất của lệnh này". Lệnh chưa từng có lãi tự rơi vào
nhánh thứ hai và ra −1 — đúng nghĩa, không phải con số gán ép. Đo trên 1.539 lệnh của
KESPT: **9,3% số lệnh không bao giờ có lãi**, nên nhánh này không hiếm.

**Ba biến không chặn được nén bằng log có dấu** `sign(x)·log1p(|x|)`: `pnl_atr`,
`mfe_atr`, `dist_stop`. Lý do là con số đo được: `mfe_atr` lên tới **80 lần ATR**
(99% ở 39,7), trong khi 454 đặc trưng đều đã scale và cắt ở ±8. Một đầu vào lớn gấp mười
lần mọi đầu vào khác sẽ át hết phần còn lại ngay từ khởi tạo. Chọn log chứ không phải
`tanh` vì `tanh` bão hoà — 5 và 80 ATR đều thành ~1, mà **42,5% số lệnh nằm trên 5 ATR**.

Bốn số hạng tương tác — cho head exit biết thị trường đang thuận hay nghịch với lệnh:

```
position × base__ret1                  bar vừa rồi chạy thuận hay nghịch
position × base__ret12                 một giờ qua
position × base__ret51                 một phiên qua
position × bot__kespt_st_dist_atr      SuperTrend đang che chở hay đe doạ
```

Đã loại bỏ ý tưởng nhân cả `h_t` với `sign(position)`: `h_t` trộn lẫn đại lượng **có
chiều** (return, đổi dấu khi soi gương) với đại lượng **không chiều** (biến động, biên
độ, ngày tới đáo hạn — luôn dương). Nhân −1 sẽ sửa loại thứ nhất và phá loại thứ hai, mà
không tách chúng ra được. Bốn số hạng trên chỉ lật đúng những cột ta biết chắc là có chiều.

Thị trường gần đối xứng ở phần thân (số bar tăng/giảm = 1,022; biên độ trung bình
tăng/giảm = 0,992) và hai bot mâu thuẫn nhau về bên nào tốt hơn, nên không ưu ái chiều nào.

### 2.6 Episode: 255 bar, bắt đầu ngẫu nhiên, tạm dừng chứ không kết thúc

- **255 bar = 5 phiên = 1 tuần.** Đủ chứa lệnh dài nhất của KESPT (213 bar). Nếu chọn
  1 phiên (51 bar) thì ép agent đóng lệnh cuối mỗi phiên — cấm đúng cái mà KESPT làm ở
  62,8% số phiên.
- **Bắt đầu ngẫu nhiên.** Cắt cố định chỉ cho 326 khúc khác nhau trong tập train; cắt
  ngẫu nhiên cho ~82.800 điểm khởi đầu. Đây là nguồn đa dạng duy nhất, vì thị trường
  không phản ứng lại agent. Giới hạn cần nói rõ: các khúc chồng lấn nhau nên **không tạo
  thông tin mới**, ngân sách 1.297 khối độc lập vẫn y nguyên.
- **Vị thế giữ qua ranh giới phiên** trong episode. Agent có `session__bars_to_close`,
  `is_last_bar`, `bar_gap` để tự biết đêm đang tới và tự quyết định.
- **Không ép đóng lệnh ở bar cuối.** Bar cuối episode là **tạm dừng** (truncation), không
  phải **kết thúc** (termination): thị trường vẫn chạy tiếp, chỉ là ta ngừng nhìn. Nên
  bootstrap `V(s_255)` thay vì gán tương lai = 0.

```
sai   :  bar 255 → ép đóng → lãi lỗ gán cho hành động HOLD ở bar 255
đúng  :  bar 255 → dừng nhìn, vị thế vẫn mở → tương lai = V(s_255)
```

Coi bar cuối là "kết thúc" sẽ kéo `V(s)` xuống sai lệch ở mọi trạng thái gần cuối khúc,
và vì điểm cắt ngẫu nhiên nên sai lệch đó rải đều lên **mọi** trạng thái.

### 2.7 Warm-start cả hai head, kèm thí nghiệm 3 nhánh

Behavior cloning từ hai bot AFL (học có giám sát, nhãn là hành động bot đã chọn) trước
khi chạy PPO.

| Nhánh | Warm-start |
|---|---|
| 1 | Không (mốc so sánh) |
| 2 | Chỉ head entry |
| 3 | Cả entry và exit |

≥ 5 hạt giống ngẫu nhiên mỗi nhánh — PPO phương sai cao, so một lần chạy là vô nghĩa.
Đánh giá trên **tập valid**, không đụng tập test.

**Chỉ số chẩn đoán bắt buộc: tỷ lệ hành động khác bot sau khi huấn luyện xong.** ≈ 0%
nghĩa là ta chỉ dựng lại con bot bằng đường vòng tốn kém hơn; ≈ 100% nghĩa là warm-start
vô tác dụng; 20–60% là vùng lành mạnh. Đây là bài kiểm tra đầu tiên trả lời được câu
*"mô hình có học được gì vượt qua hai con bot không"*.

## 3. Nợ kỹ thuật: chi phí giao dịch

Giai đoạn phát triển chạy với **chi phí = 0**, thêm phí ở cuối. Hàm reward khai tham số
`cost_per_turn` đặt `0.0` ngay từ đầu để sau này chỉ đổi một con số. Hệ quả đã ghi trong
CLAUDE.md, không nhắc lại ở mỗi đề xuất.

Hai điều cần nhớ khi diễn giải kết quả giai đoạn này: **SKIP sẽ gần như không được dùng**
(đứng ngoài cho kỳ vọng 0, vào lệnh cho kỳ vọng ≥ 0), và **head exit sẽ không chết đói**
— nên mọi cơ chế chống chết đói xây bây giờ đều **chưa được kiểm chứng**.

## 4. Giả định tôi tự đặt (chưa hỏi, dễ đổi)

Hai chỗ spec chưa nói rõ mà code buộc phải chọn:

- **`dist_stop` tham chiếu**: `entry_price − position × 2 × ATR(tại bar vào lệnh)`. Đây
  chỉ là **mốc đo khoảng cách**, không phải lệnh dừng lỗ thật được thực thi — agent vẫn
  tự quyết định thoát. Bội số 2 chọn theo thông lệ, đổi được bằng một tham số.
- ~~**`retained` khi `mfe_atr` = 0**: quy ước `1.0`~~ — **đã bỏ.** Thay bằng mẫu số
  `max(MFE, |pnl|, ε)` nên không còn trường hợp suy biến nào cần quy ước.

## 5. Bất biến

**Bất biến mới #14 — trạng thái vị thế không bao giờ nằm trong `features.npy`.** Sáu biến
vị thế và bốn số hạng tương tác đều phụ thuộc hành động của agent, không phải thị trường,
nên phải ghép sau encoder chứ không đi qua pipeline đặc trưng. Đây là họ hàng của bất biến
#6 (tín hiệu bot không nằm trong X): cùng một nguyên tắc — X chỉ chứa thứ mọi người nhìn
thấy như nhau.

## 6. Bài test làm spec này thất bại

```
tests/test_policy.py::test_entry_head_used_only_when_flat
tests/test_policy.py::test_exit_head_used_only_when_in_position
tests/test_policy.py::test_compound_action_reverses_within_one_bar
tests/test_policy.py::test_compound_log_prob_is_sum_of_both_steps
tests/test_policy.py::test_hold_keeps_position_and_increments_bars_held
tests/test_policy.py::test_mfe_never_decreases_within_a_trade
tests/test_policy.py::test_position_state_resets_on_new_trade
tests/test_policy.py::test_interaction_terms_flip_sign_with_position
tests/test_policy.py::test_position_state_variables_are_scale_free
tests/test_policy.py::test_retained_is_bounded_without_any_convention
tests/test_policy.py::test_unbounded_state_vars_are_squashed
tests/test_policy.py::test_policy_runs_on_gpu_when_available
tests/test_invariants.py::test_position_state_not_in_feature_matrix
```

Mỗi bài đỏ khi nào:

- **entry/exit head masking** — nếu gọi nhầm head theo vị thế, hoặc quên mask thì hành
  động EXIT xuất hiện lúc đang FLAT
- **compound reverses within one bar** — nếu quên hỏi head entry sau EXIT, vị thế sẽ về
  FLAT rồi đứng im, đảo chiều mất 2 bar thay vì 1
- **log_prob is sum** — nếu chỉ lấy log-prob của một bước, PPO tính sai tỷ lệ importance
  và cập nhật lệch. Đây là lỗi im lặng nhất trong cả spec: không crash, chỉ học sai
- **mfe never decreases** — nếu MFE tính bằng `pnl` hiện tại thay vì đỉnh chạy, `retained`
  luôn bằng 1 và mất hết ý nghĩa trailing stop
- **resets on new trade** — nếu `bars_held` hay `mfe` không reset khi mở lệnh mới, lệnh
  sau thừa hưởng trạng thái lệnh trước
- **interaction flips sign** — nếu quên nhân với `position`, head exit mất khả năng phân
  biệt thuận/nghịch và phải học riêng hai chiều
- **scale-free** — nếu quên chia ATR, biến vị thế mang đơn vị điểm và sẽ thay đổi thang
  đo giữa 2018 (giá 900) và 2026 (giá 1900)
- **runs on GPU** — nếu có tensor bị bỏ quên trên CPU, forward pass sẽ ném lỗi thiết bị
- **not in feature matrix** — bất biến #14

## 7. Tiêu chí chấp nhận

Thay đổi kỹ thuật, chưa có giả thuyết thị trường nào được kiểm định, **chưa nhìn tập test
lần nào**. Tiêu chí kỹ thuật:

- 11 bài test ở mục 6 xanh
- Toàn bộ 36 test hiện có vẫn xanh
- Tổng tham số mạng ≤ 100.000 (mục tiêu 77.190 ở cấu hình chiếu 64)
- Forward pass chạy được trên GPU với lô `(512, 64, 454)` mà không tràn 8,6 GB VRAM
- Thông lượng mạng ≥ 10.000 bước/s ở 32 môi trường song song trên GPU, khớp benchmark
- Mô phỏng môi trường **vector hoá**, không có vòng lặp Python trên chiều môi trường

---

## Kết quả

**Chấp nhận.** Đã làm — `laplace/rl/`:

| File | Nội dung |
|---|---|
| `device.py` | Chọn thiết bị ở một chỗ duy nhất |
| `state.py` | `resolve_actions()` (hành động ghép), `PositionState` (6 biến + 4 số hạng tương tác), `STATE_NAMES` |
| `policy.py` | `Policy` — chiếu 454→64, LSTM(64,64), ba head; `act()` và `action_log_probs()` |

Đối chiếu với tiêu chí ở mục 7:

| Tiêu chí | Kết quả |
|---|---|
| 13 bài test mục 6 xanh | **đạt** |
| 36 test cũ vẫn xanh | **đạt** — 50/50 (thêm 14 test của spec này) |
| Tham số ≤ 100.000 | **đạt** — đúng 77.190 như dự tính |
| Lô (512, 64, 454) trên GPU | **đạt** — VRAM đỉnh 0,33 GB / 8,6 |
| Môi trường vector hoá, không vòng lặp Python trên chiều môi trường | **đạt** |
| ≥ 10.000 bar/s ở 32 môi trường | **không đạt — 6.467. Tiêu chí đặt sai, không phải code sai** |

### Điều học được: tiêu chí thông lượng đặt sai chỗ

Tôi lấy ngưỡng 10.000 từ benchmark **chỉ đo mạng neural** (11.648 bar/s ở 32 môi trường),
rồi áp nó cho hệ thống **có cả môi trường**. Đo lại đầy đủ:

| Môi trường song song | Mạng | Môi trường | Tổng | bar/s |
|---:|---:|---:|---:|---:|
| 32 | 0,86 s | 0,40 s | 1,26 s | 6.467 |
| 128 | 0,98 s | 0,40 s | 1,37 s | **23.747** |
| 512 | 0,96 s | 0,40 s | 1,37 s | 95.494 |
| 1024 | 1,30 s | 0,42 s | 1,71 s | 152.489 |

Điểm mấu chốt: **chi phí môi trường gần như không đổi ở mọi cỡ lô** (0,40–0,42 s cho 255
bar). Nó không phải chi phí *tính* mà là chi phí *khởi động kernel* — 255 bước × ~15 lời
gọi nhỏ mỗi bước ≈ 3.800 kernel, mỗi cái vài chục micro giây điều phối, bất kể tensor có
32 hay 1024 phần tử. Cùng lý do khiến `act()` tốn gấp 4 lần forward thuần: máy móc lấy
mẫu, log-prob và entropy sinh ra rất nhiều kernel tí hon.

Hệ quả thực tế: **dùng ≥ 128 môi trường song song**, khi đó chi phí cố định được chia đều
và thông lượng vượt xa ngưỡng. Ở 32 môi trường thì 3 triệu bước mất 7,7 phút; ở 128 môi
trường còn 2,1 phút. Cả hai đều thừa sức chạy thí nghiệm 15 lần.

Chưa tối ưu phần môi trường (gộp kernel, CUDA graph) vì ở cỡ lô sẽ dùng thật nó chỉ chiếm
29% thời gian — tối ưu bây giờ là tối ưu chỗ không đau.

### Sửa sau khi đo (vòng thứ hai)

Đo phân bố `pnl_atr` và `mfe_atr` trên 1.539 lệnh của KESPT làm lộ hai vấn đề, đã sửa cả hai:

1. **`retained` có trường hợp suy biến không hiếm** — 9,3% số lệnh chưa từng có lãi. Quy
   ước `1.0` cho chúng cùng giá trị với lệnh đang ở đỉnh lãi. Thay bằng mẫu số
   `max(MFE, |pnl|, ε)`, chặn [−1, 1], không còn quy ước nào.
2. **Ba biến không chặn, `mfe_atr` lên tới 80** trong khi mọi đầu vào khác đã cắt ở ±8.
   Đây là vấn đề lớn hơn hẳn vấn đề thứ nhất và tôi đáng lẽ phải thấy khi thiết kế, không
   phải sau khi đo. Đã nén bằng log có dấu.

Lý do tôi **rút lại** đề xuất `(MFE − pnl)/ATR`: cả `pnl_atr` lẫn `mfe_atr` đã là đầu vào,
nên hiệu của chúng là một phép trừ tuyến tính mà một lớp Linear tính được ngay. Nó gần như
không thêm thông tin. Ngược lại **phép chia thì mạng rất khó tự học**, nên tỷ lệ mới là
thứ đáng đưa vào.

### Giả định vẫn còn treo

Mốc dừng lỗ tham chiếu `entry ∓ 2×ATR` vẫn là con số tôi tự chọn theo thông lệ, chưa kiểm
chứng. Đổi được bằng một tham số.
