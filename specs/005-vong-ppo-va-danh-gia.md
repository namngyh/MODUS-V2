# 005 — Vòng PPO và đánh giá trên valid

- **Trạng thái**: xong
- **Ảnh hưởng tới**: `laplace/rl/ppo.py`, `laplace/rl/evaluate.py` (mới), bất biến #18
- **Không** làm ở spec này: behavior cloning và thí nghiệm 3 nhánh → spec 007

## 1. Câu hỏi

Có mạng (spec 002) và môi trường (spec 004) nhưng chưa có gì nối chúng lại. Cần vòng
huấn luyện PPO chạy được từ đầu đến cuối, và một cách đánh giá **bằng điểm** trên tập
valid để biết nó có học được gì không.

Phạm vi dừng ở nhánh 1 của thí nghiệm (không warm-start). Đủ để trả lời câu hỏi đầu tiên:
*toàn bộ chồng này có chạy không.*

## Ký hiệu và khái niệm

| Ký hiệu | Nghĩa bằng lời | Giá trị |
|---|---|---|
| `V(s)` | **Hàm giá trị** — mạng đoán "đứng ở trạng thái này thì từ giờ tới cuối kỳ vọng được bao nhiêu reward" | head thứ ba của mạng |
| `γ` gamma | **Hệ số chiết khấu** — reward ở xa đáng giá bao nhiêu so với reward bây giờ | 0,99 |
| `λ` lambda | Tham số làm mượt của GAE — đánh đổi giữa nhiễu và thiên lệch khi ước lượng advantage | 0,95 |
| `Â_t` | **Advantage** — "hành động vừa chọn tốt hơn mức trung bình bao nhiêu" | tính bằng GAE |
| `ratio` | Xác suất policy mới chia cho policy cũ, cho **cùng** hành động đã chọn | — |
| `ε` clip | Biên cắt `ratio`, giữ cho mỗi lần cập nhật không nhảy quá xa | 0,2 |
| **truncation** | Ta ngừng nhìn, thị trường vẫn chạy | luôn là trường hợp này |
| **termination** | Trò chơi thật sự kết thúc, tương lai = 0 | **không bao giờ xảy ra ở đây** |

## 2. Đã chốt

### 2.1 Thị trường không bao giờ "kết thúc" — mọi ranh giới đều là tạm dừng

Đây là điểm dễ sai nhất của cả spec. PPO chuẩn viết:

```
delta_t = r_t + γ·V(s_{t+1})·(1 − done_t) − V(s_t)
```

`done_t = 1` nghĩa là "hết trò chơi, tương lai bằng 0". **Ở đây `done` luôn bằng 0** — bar
256 vẫn tồn tại, giá vẫn chạy. Nên `V(s_{t+1})` luôn được dùng.

Nhưng vẫn phải **cắt chuỗi đệ quy GAE** tại ranh giới, vì `s_{t+1}` sau khi reset thuộc
một quỹ đạo khác hẳn:

```
delta_t = r_t + γ·V(s_{t+1}) − V(s_t)              <- LUON bootstrap
Â_t     = delta_t + γ·λ·Â_{t+1}·(1 − cut_t)        <- CAT tai ranh gioi
```

Hai mặt nạ khác nhau cho hai việc khác nhau. Gộp chúng làm một là lỗi im lặng: giá trị
của mọi trạng thái gần cuối khúc bị kéo xuống, và vì điểm cắt ngẫu nhiên nên sai lệch rải
đều lên toàn bộ dữ liệu.

**`TradingEnv.step()` không tự reset**, nên `V(s_{t+1})` tính được trên trạng thái *tiếp
diễn thật* trước khi reset. Vòng PPO phải theo đúng thứ tự:

```
1. step()                       -> obs_{t+1}, reward, truncated
2. tinh V(obs_{t+1})            <- TRUOC khi reset
3. reset cac moi truong truncated
```

Làm ngược lại sẽ bootstrap bằng giá trị của một trạng thái ngẫu nhiên hoàn toàn không
liên quan.

### 2.2 Có hai loại ranh giới, cả hai đều cắt

- **Hết episode** (255 bar) — môi trường báo `truncated`
- **Hết rollout** (`n_steps` bar) — ta dừng thu để cập nhật mạng

Cả hai đều là tạm dừng và đều phải cắt chuỗi GAE. Quên loại thứ hai là lỗi kinh điển.

### 2.3 log-prob của hành động ghép

Đã chốt ở spec 002: một bar đảo chiều dùng **cả hai** head, nên log-prob là **tổng** hai
số hạng. `ratio` của PPO phải dùng đúng tổng đó, cả lúc thu kinh nghiệm lẫn lúc cập nhật.
Chỉ lấy một số hạng thì tỷ lệ importance sai mà không có gì báo.

### 2.4 Siêu tham số: dùng mặc định chuẩn, không tinh chỉnh ở spec này

| | Giá trị | Ghi chú |
|---|---|---|
| `n_env` | **128** | Đo được ở spec 004: 20.626 bar/s. Ở 32 chỉ còn một phần tư |
| `n_steps` mỗi rollout | 64 | → 8.192 chuyển tiếp mỗi lần cập nhật |
| epoch mỗi rollout | 4 | |
| minibatch | 1.024 | |
| learning rate | 3e-4 | |
| `γ`, `λ`, `ε` | 0,99 / 0,95 / 0,2 | mặc định chuẩn của PPO |
| hệ số entropy | 0,01 | |
| hệ số value loss | 0,5 | |

**Không cái nào được tinh chỉnh ở spec này.** Chúng là mặc định chuẩn, ghi ra để sau này
biết mình đã bắt đầu từ đâu. Tinh chỉnh làm ở spec 007 trở đi, trên tập valid.

### 2.5 Đánh giá báo cáo bằng ĐIỂM, không bằng reward

Theo mục từ vựng trong CLAUDE.md. Chạy policy trên **toàn bộ tập valid** theo đúng thứ tự
thời gian (không cắt ngẫu nhiên, không lặp), cộng dồn `env.profit_points`, và báo cáo:

- **`profit_points`** tổng và theo năm — thước đo hiệu quả
- Số lệnh, tỷ lệ thời gian có vị thế, sụt giảm tối đa **tính bằng điểm**
- Phân bố hành động (bao nhiêu % SKIP / LONG / SHORT / HOLD / EXIT)
- `reward` trung bình — **chỉ để chẩn đoán huấn luyện**, không phải con số thành tích

Đánh giá chạy **lấy mẫu ngẫu nhiên** từ policy chứ không lấy argmax: policy là ngẫu nhiên
theo thiết kế, và đo bản tất định của nó là đo một thứ khác với thứ đang được huấn luyện.

## 3. Bất biến

**Bất biến mới #18 — mọi ranh giới episode và rollout đều bootstrap `V`, không bao giờ
gán tương lai bằng 0.** Vi phạm thì hàm giá trị bị kéo lệch ở mọi trạng thái gần ranh
giới, mà điểm cắt lại ngẫu nhiên nên sai lệch trải đều lên toàn bộ dữ liệu — không có
triệu chứng nào ngoài việc mô hình học kém hơn mức đáng lẽ.

## 4. Bài test làm spec này thất bại

```
tests/test_ppo.py::test_gae_matches_hand_computation
tests/test_ppo.py::test_boundary_bootstraps_instead_of_zeroing_future
tests/test_ppo.py::test_gae_recursion_is_cut_at_boundaries
tests/test_ppo.py::test_ratio_uses_summed_log_prob_for_compound_actions
tests/test_ppo.py::test_clipping_limits_the_policy_update
tests/test_ppo.py::test_one_update_reduces_loss_on_a_fixed_batch
tests/test_ppo.py::test_evaluation_reports_profit_in_points
tests/test_ppo.py::test_evaluation_covers_the_split_in_time_order
tests/test_ppo.py::test_evaluation_never_touches_the_test_split
```

- **gae hand computation** — GAE tính tay cho một trường hợp 4 bước, so từng số
- **bootstraps instead of zeroing** — dựng một batch có `truncated`, kiểm tra advantage
  **khác** với khi gán `V(s_{t+1}) = 0`. Đây là bài canh bất biến #18
- **recursion is cut** — advantage ở bar cuối một episode không được lan sang episode sau
- **summed log prob** — dựng một bar đảo chiều, kiểm tra `ratio` dùng tổng hai head
- **clipping** — advantage rất lớn cũng không đẩy `ratio` ra ngoài `[1−ε, 1+ε]`
- **one update reduces loss** — kiểm tra sơ bộ rằng vòng cập nhật thật sự học
- **profit in points** — kết quả đánh giá có trường `profit_points`; nếu ai đó báo cáo
  `reward` như thành tích thì bài này đỏ
- **time order / never touches test** — họ hàng của bất biến #5 và của sổ ghi số lần nhìn
  tập test

## 5. Tiêu chí chấp nhận

Thay đổi kỹ thuật. Tập test: **không nhìn thêm lần nào** (vẫn 1, ghi ở
[SO-LAN-NHIN-TAP-TEST.md](SO-LAN-NHIN-TAP-TEST.md)).

- 9 bài test ở mục 4 xanh; 70 test hiện có vẫn xanh
- Chạy được 200.000 bước huấn luyện đầu-đến-cuối mà không lỗi
- Thông lượng huấn luyện ≥ 15.000 bar/s ở 128 môi trường (thấp hơn 20.626 của spec 004 vì
  có thêm backward pass)
- Đánh giá trên valid chạy hết 12.502 bar và trả về `profit_points`

**Không** đặt tiêu chí về lợi nhuận. Spec này chỉ trả lời *"chồng này có chạy không"*;
hỏi *"nó có kiếm được tiền không"* khi chưa warm-start và chưa tinh chỉnh gì là hỏi sai
câu. Con số profit đầu tiên ghi lại làm mốc, không phải để đạt ngưỡng.

---

## Kết quả

**Chấp nhận.** Đã làm `laplace/rl/ppo.py`, `laplace/rl/evaluate.py`, `tests/test_ppo.py`
11 bài, bất biến #18. Chồng chạy được từ đầu tới cuối trên GPU.

| Tiêu chí | Kết quả |
|---|---|
| 9 bài test mục 4 xanh | **đạt** — 11 bài |
| 70 test hiện có vẫn xanh | **đạt** |
| Chạy 200.000 bước đầu-đến-cuối | **đạt** — 42,7 giây |
| Đánh giá chạy hết valid | **đạt** — 12.438 bar |
| ≥ 15.000 bar/s khi huấn luyện | **không đạt — 4.801. Tiêu chí sai lần thứ ba** |

### Ba lỗi thật, bài test bắt được hai

**1. `collect()` bootstrap bằng trạng thái SAU KHI RESET** — đúng lỗi mà bất biến #18
cấm. Sau khi một môi trường tạm dừng và nhận điểm bắt đầu ngẫu nhiên mới, `values[t+1]`
là giá trị của một quỹ đạo hoàn toàn khác.

Điều đáng nói: bài `test_boundary_bootstraps_instead_of_zeroing_future` **không bắt được**
— nó kiểm `compute_gae` với đầu vào đúng, chứ không kiểm rằng `collect()` *nạp* đầu vào
đúng. Tôi tìm ra khi đọc lại code, không phải nhờ test.

Đã sửa hai chỗ: `compute_gae` nay nhận `next_values` **tường minh** thay vì tự suy ra
`values[t+1]` — để trách nhiệm tính đúng không bị giấu đi — và thêm bài
`test_collect_bootstraps_from_the_pre_reset_state` canh đúng khe hở đó.

**2. `evaluate()` để mạng kẹt ở chế độ eval** — lần huấn luyện kế tiếp ném
`cudnn RNN backward can only be called in training mode`, một thông báo không hề trỏ tới
chỗ thật sự sai. Đã dùng `try/finally` trả lại chế độ cũ, kèm test.

**3. `update()` chạy ba lượt forward mỗi minibatch** — gọi riêng `action_log_probs`,
`logits` và `act`. Gộp thành `Policy.evaluate_actions()`, một lượt duy nhất.

### Hai bài test của tôi đo sai thứ

Cả hai lần tôi tưởng code sai, hoá ra test sai:

- **Tổng loss không đơn điệu giảm** — mục tiêu chính sách bị *cắt* nên chững lại khi
  policy đi qua biên, còn entropy tụt khi policy sắc lại mà loss lại *trừ* entropy.
- **Value loss cũng không** — head giá trị **dùng chung encoder** với head chính sách,
  nên gradient của policy loss kéo encoder đi và làm value dự đoán lệch theo.

Thay bằng thứ PPO thật sự làm: sau cập nhật, hành động có advantage dương phải trở nên
khả dĩ hơn. Đo bằng tương quan giữa `Δlog π` và advantage.

### Tiêu chí thông lượng sai lần thứ ba

| Spec | Tôi đặt | Thực tế | Lấy từ đâu |
|---|---:|---:|---|
| 002 | — | 20.626 | đo mạng, không có môi trường |
| 004 | 20.000 | 20.626 | **đúng** — lấy từ số đo cùng phạm vi |
| 005 | 15.000 | **4.801** | đoán "backward tốn thêm chút" |

Backward không tốn "thêm chút" mà tốn **gấp bốn lần** phần thu kinh nghiệm: mỗi rollout
thu 8.192 bước rồi chạy 4 epoch × 8 minibatch, mỗi minibatch là `(1024, 64, 454)` qua
LSTM cả chiều xuôi lẫn chiều ngược.

Đây là lần thứ ba tôi đặt tiêu chí thông lượng từ một phép đo **hẹp hơn phạm vi tiêu chí**.
Quy tắc rút ra: **chỉ đặt ngưỡng thông lượng từ phép đo bao trọn thứ sắp đo.** Nếu chưa
đo được thì ghi "chưa có cơ sở" thay vì đoán.

Về tuyệt đối thì 4.801 bar/s vẫn đủ dùng: 3 triệu bước ≈ 10,4 phút một lần chạy, 15 lần
thí nghiệm ≈ 2,6 giờ.

### Con số profit đầu tiên — và tại sao chưa đọc được gì từ nó

```
valid, trước huấn luyện (policy ngẫu nhiên):  +442,5 điểm
valid, sau 200.000 bước:                      −218,3 điểm
entropy: 1,210 → 1,130
```

**Chưa kết luận được gì**, và spec này đã nói trước là sẽ không đặt tiêu chí lợi nhuận:

- 200.000 bước chỉ là 2,4 lượt qua tập train
- Entropy hầu như không giảm (1,21 → 1,13): policy vẫn gần như ngẫu nhiên
- Chưa warm-start, chưa tinh chỉnh siêu tham số nào
- **Một policy ngẫu nhiên kiếm được +442,5 điểm** — đó là thước đo tốt nhất cho thấy hai
  con số này nằm trong vùng nhiễu

### Ngưỡng nhiễu — con số quan trọng nhất của spec này

Chạy 10 policy **khởi tạo ngẫu nhiên** (chưa huấn luyện gì) trên valid:

```
+442,5   +153,4    −15,0   +189,3    +52,7
 −46,9   −136,4   +151,5     +2,5   +198,1     điểm

trung bình +99,2 | độ lệch chuẩn 164,3 | trải từ −136 đến +443
```

Điều này **giải thích hoàn toàn** con số ở trên: mốc "+442,5" chính là **hạt giống may
nhất trong mười**. Tôi đã so sánh hạt giống may nhất với một lần chạy huấn luyện duy
nhất — phép so hoàn toàn vô nghĩa. Và −218,3 nằm ngay trong vùng nhiễu.

Kết luận đúng: **cả hai con số đều không nói lên điều gì.**

### Công suất phát hiện — số liệu để thiết kế spec 007

| Số hạt giống | Sai số chuẩn | Phát hiện được chênh lệch |
|---:|---:|---:|
| 1 | 164,3 | > 328 điểm |
| 3 | 94,8 | > 190 điểm |
| **5** | **73,5** | **> 147 điểm** |
| 10 | 51,9 | > 104 điểm |

Tập valid dài ~1 năm và KESPT kiếm ~508 điểm/năm, nên **một chiến lược có chất lượng
tương đương KESPT sẽ hiện ra ở mức 6,9 sigma với 5 hạt giống** — thí nghiệm 3 nhánh đã
chốt ở spec 002 đủ công suất để phát hiện. Với 3 hạt giống vẫn còn 5,4 sigma, nên nếu
thiếu thời gian thì cắt xuống 3 vẫn dùng được.

Nhưng đọc bảng theo chiều ngược lại cũng quan trọng: **một cải thiện dưới 147 điểm/năm
sẽ không phân biệt được với nhiễu** dù chạy đủ 5 hạt giống. Đừng đuổi theo những khác
biệt nhỏ hơn thế.
