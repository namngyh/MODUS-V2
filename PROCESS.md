# PROCESS.md

> **Operational memory, engineering protocol, and research safety standard for AI coding agents**
>
> File này là nguồn ngữ cảnh vận hành chung cho Codex, Claude Code và các AI coding agent khác khi làm việc với repository.
>
> Mục tiêu:
>
> - Giúp AI hiểu nhanh project và trạng thái hiện tại.
> - Giữ continuity giữa nhiều session và nhiều AI khác nhau.
> - Không lặp lại lỗi đã từng gặp.
> - Không tự ý sửa code trước khi thảo luận.
> - Giữ phạm vi implementation đúng với phần đã được approve.
> - Không mất kết quả training/backtest/optimization.
> - Đảm bảo research quant/ML có thể tái tạo.
> - Ngăn look-ahead bias, leakage, cherry-picking và overfitting.
> - Có thể truy ngược một kết quả về code, data, config và experiment đã tạo ra nó.
>
> **Mọi AI phải đọc file này trước khi bắt đầu một task mới.**

---

# 0. AI ENTRY POINT

`PROCESS.md` phải nằm tại root repository:

```text
<repository-root>/PROCESS.md
```

Các instruction file của từng agent nên trỏ về file này.

Ví dụ `CLAUDE.md`:

```text
Before doing any work, read PROCESS.md and follow it.
```

Ví dụ `AGENTS.md`:

```text
Before doing any work, read PROCESS.md and follow it.
```

Instruction cho Codex:

```text
PROCESS.md is the operational source of truth for this repository.
Read it before starting any task.
```

---

# 1. PRIORITY OF INSTRUCTIONS

Thứ tự ưu tiên:

1. Yêu cầu trực tiếp mới nhất của người dùng.
2. `PROCESS.md`.
3. Documentation và conventions chính thức của project.
4. Architecture/code hiện tại.
5. Giả định của AI.

AI không được tự thay thế yêu cầu của người dùng bằng một phương án mà AI nghĩ là tốt hơn.

Nếu AI thấy có giải pháp tốt hơn:

```text
Explain
→ Compare
→ Discuss
→ Get approval
→ Implement
```

---

# 2. GOLDEN WORKFLOW

Quy trình mặc định:

```text
INSPECT
   ↓
UNDERSTAND
   ↓
DISCUSS
   ↓
APPROVAL
   ↓
SCOPE LOCK
   ↓
IMPLEMENT
   ↓
TEST
   ↓
CHECKPOINT
   ↓
VERIFY
   ↓
REPORT
   ↓
RECORD
```

Không được bỏ qua:

```text
DISCUSS
APPROVAL
```

trước khi sửa code.

---

# 3. INSPECTION ≠ IMPLEMENTATION

## 3.1 Inspection / Investigation

AI được phép chủ động thực hiện trước khi hỏi người dùng:

- Đọc source code.
- Search repository.
- Đọc documentation.
- Đọc `PROCESS.md`.
- Đọc config.
- Kiểm tra cấu trúc thư mục.
- Kiểm tra schema.
- Xem `git status`.
- Xem `git diff`.
- Xem git log.
- Kiểm tra dependency.
- Đọc logs.
- Kiểm tra checkpoint.
- Kiểm tra experiment đang dang dở.
- Chạy existing tests.
- Chạy lint.
- Chạy type check.
- Chạy static analysis.
- Reproduce bug trong môi trường an toàn.
- Chạy diagnostic không gây side effect.

Mục đích:

> AI phải hiểu project đủ tốt trước khi đề xuất giải pháp.

Không yêu cầu AI hỏi người dùng trước mỗi thao tác đọc.

---

## 3.2 Implementation

Implementation bao gồm:

- Sửa source code.
- Tạo source code.
- Refactor.
- Xóa code.
- Rename/move file.
- Sửa config.
- Thêm/xóa dependency.
- Sửa database schema.
- Viết migration.
- Viết `.bat`.
- Sửa CI/CD.
- Thay architecture.
- Thay data processing behavior.
- Thay model behavior.

Implementation chỉ được bắt đầu sau approval.

---

# 4. PROJECT SNAPSHOT

## Project

```text
Name:            MODUS 2 (thư mục làm việc: laplace)
Purpose:         Mô hình auto-trading VN30F1M, nến 5 phút: LSTM dự báo → Meta-labeling → PPO ra quyết định
Repository:      https://github.com/namngyh/MODUS-V2 (nhánh main)
Primary language: Python 3.13 — chạy bằng `py -3.13` (lệnh `python` trên máy là 3.12 KHÔNG có thư viện)
Framework:       PyTorch 2.13.0+cu130 (RTX 4060), TA-Lib 0.7, pandas, numpy, scipy, scikit-learn
Database:        PostgreSQL 16 + TimescaleDB qua Tailscale — CHỈ cho paper trading; huấn luyện dùng CSV
Package manager: pip (requirements.txt)
Test framework:  pytest (123 bài, ~6–13 phút)
```

## Important directories

| Path | Purpose |
|---|---|
| `laplace/` | Dữ liệu, đặc trưng (468 cột), dừng hoá, chia tập, bot AFL |
| `laplace/forecast/` | Tầng ① LSTM dự báo: nhãn, lịch học ngoài mẫu, mô hình, huấn luyện, chấm điểm (spec 008) |
| `laplace/rl/` | Tầng ③ PPO: policy, môi trường GPU, vòng học, đánh giá (spec 002–005) |
| `bot/` | Hai file AFL gốc (KESPT, roofing2) |
| `specs/` | Spec 001–008, sổ ghi số lần nhìn tập test |
| `tests/` | 123 test, canh 20 bất biến |
| `experiments/` | Kết quả chạy (không commit) |
| `data/` | Đặc trưng đã dựng, snapshot DB (không commit) |

## Entry points

```text
Application:    — (chưa có)
CLI đặc trưng:  py -3.13 build_features.py --out data/features
Training LSTM:  run_forecast.bat [run-id]   (gọi run_forecast.py; người dùng chạy)
Backtest:       — (chưa có; đánh giá PPO ở laplace/rl/evaluate.py)
Tests:          py -3.13 -m pytest tests/ -q
Configuration:  laplace/config.py (đặc trưng, chia tập), laplace/forecast/train.py (TrainConfig)
Checkpoints:    experiments/forecast/<run-id>/<bản>/seed_XX/<vòng>/ckpt_latest.pt, ckpt_best.pt
Experiments:    experiments/forecast/<run-id>/run_config.json, summary.json
Outputs:        pred.parquet (xác suất từng nến), metrics.json mỗi lần học
Logs:           experiments/forecast/<run-id>/run.log
```

Tài liệu đi kèm: **CLAUDE.md** (quy tắc làm việc, bất biến, quyết định), **KIENTRUC.md**
(kiến trúc MODUS 2 và các quyết định đã chốt), **README.md** (đặc trưng), **FEATURES.md**
(từng cột, sinh tự động).

---

# 5. CURRENT STATUS

## Current objective

```text
Kiểm chứng tầng ① của MODUS 2: LSTM có dự báo được HƯỚNG giá VN30F1M (nến 5 phút) tốt hơn
một mốc không nhìn biểu đồ hay không, trước khi xây Meta và PPO lên trên.
```

## Current task

```text
Spec 008 — LSTM dự báo (specs/008-lstm-du-bao.md).
Code xong, test xanh, chạy thử GPU xong. Đang chờ người dùng chốt 2 quyết định (mục 53)
trước khi sửa phần chấm điểm và giao cho người dùng chạy thật.
```

## Current state

```text
DISCUSSING
```

## Last known working state

```text
Branch:   main
Commit:   b3132fb (+ commit cập nhật PROCESS.md này)
Command:  py -3.13 -m pytest tests/ -q
Result:   123 passed
Date:     2026-10-01
```

## Current modifications

```text
None — cây làm việc sạch, mọi thứ đã push.
```

## Blockers

```text
1. Tiêu chí chấm LSTM (A / B / C) — người dùng chưa chốt.
2. Thiết kế bản thí nghiệm thứ ba "tự học không nhãn" (đã duyệt THÊM; chưa chốt mục tiêu
   T1/T2 và cách tính sai số).
```

## Tiến trình đã xong

| Spec | Nội dung | Trạng thái |
|---|---|---|
| 001 | Gộp nến 1 phút → 5 phút (khớp 100 % nến của nhà cung cấp) | xong |
| 002 | Cấu trúc policy PPO: encoder LSTM + head entry / exit / value | xong |
| 003 | Snapshot DB (chỉ paper trading); sửa nhãn mua/bán bị đảo trong CSV | xong |
| 004 | Môi trường RL trên GPU, reward theo bội số ATR | xong |
| 005 | Vòng PPO + đánh giá bằng điểm; mức may rủi 164 điểm (đã hết hiệu lực) | xong |
| 006 | Dừng hoá theo bản chất cột; phát hiện nhà cung cấp đổi phân loại mua/bán năm 2023 | xong |
| 007 | Chia tập 2018–2021 / 2022 / 2023+; tách đặc trưng bot khỏi đầu vào LSTM | xong |
| 008 | LSTM dự báo — code, test, chạy thử | **đang làm** |

## Các quyết định đã chốt (chi tiết: KIENTRUC.md, CLAUDE.md mục 8–9)

- Thứ tự tầng: **LSTM → Meta → PPO**; mọi tầng học trên dự báo "chưa thấy đáp án" (theo năm)
- Nến 5 phút cho mọi tầng; một vị thế tại một thời điểm; **không đảo chiều trong một nến**
- PPO: 2 head ra quyết định (entry LONG/SHORT/SKIP, exit HOLD/EXIT) + head value; **không nhận `h_t`**
- Reward = ½R + ½C; profit (đánh giá) khớp ở **giá mở cửa nến kế tiếp**, tính bằng điểm
- Chia tập: train 2018–2021 (51.068 nến), valid 2022 (12.596), **test 2023-01 → 2026-09 (45.722) — mở một lần**
- Đặc trưng bot AFL chỉ vào Meta; ARS mặc định tắt (chờ ARSH v0.6)
- LSTM: head (a) giá chạm ±1,5 ATR(51) trước trong 24 nến, không qua phiên (3 nhóm);
  thí nghiệm bản (a) và (a)+(c); **10 seed ngẫu nhiên**; 4 lần học mỗi seed
- Phí, thuế: làm sau cùng — không nhắc tới

## Phát hiện quan trọng (có số liệu)

- Nhà cung cấp đổi cách phân loại mua/bán từ 2023: mất cân bằng −0,13 → +0,05; 3,5 % khối lượng không còn được phân loại
- Chênh giá đóng cửa → mở cửa nến sau: trong phiên TB 0,19 điểm, qua trưa/qua đêm TB **3,90 điểm**
- Bỏ đảo chiều làm KESPT mất ≈ 10 điểm/năm (337 lần đảo / 1.347 lệnh)
- **Bẫy giờ trong phiên của nhãn (a)**: nhãn bị cắt ở cuối phiên → tỷ lệ "đi ngang" 2,6 % lúc
  10:00 nhưng 54,9 % lúc 14:20 và 100 % lúc 14:30. Mốc chỉ dùng tỷ lệ theo giờ (0,7873) thắng
  LSTM 1 epoch (0,8467) trên valid 2022 — tiêu chí chấm cũ không đo được khả năng đoán hướng
- Chạy thử LSTM: 0,2–0,5 giây/epoch trên RTX 4060

---

# 6. FACTS / ASSUMPTIONS / UNKNOWNS

Trước một thay đổi quan trọng, AI nên phân biệt:

```text
Confirmed:
- ...

Assumptions:
- ...

Unknown:
- ...

Needs user confirmation:
- ...
```

Không được biến assumption thành fact.

Không implement dựa trên một assumption có thể thay đổi behavior quan trọng mà chưa xác minh hoặc thảo luận.

---

# 7. BEFORE CODING GATE

Trước khi viết code, AI phải trình bày:

## Understanding

```text
AI hiểu yêu cầu là gì?
```

## Current implementation

```text
Code hiện tại hoạt động như thế nào?
```

## Findings

```text
Những gì đã phát hiện sau khi inspect repository.
```

Nếu là bug:

```text
Possible root cause:
Confirmed root cause:
```

Nếu là feature:

```text
Relevant modules:
Relevant architecture:
```

## Proposed solution

```text
Giải pháp dự kiến.
```

## Files expected to change

```text
path/to/file_1
path/to/file_2
```

## Risks

```text
[ ] API impact
[ ] Database impact
[ ] Breaking changes
[ ] Performance impact
[ ] Dependency changes
[ ] Migration
[ ] Data impact
[ ] Checkpoint compatibility
[ ] Backward compatibility
[ ] Quant/model impact
```

## Validation plan

```text
[ ] Unit tests
[ ] Integration tests
[ ] Lint
[ ] Type check
[ ] Build
[ ] Manual verification
[ ] Backtest
[ ] Benchmark
[ ] Save/load checkpoint test
[ ] Resume checkpoint test
```

Sau đó:

> **STOP AND WAIT FOR USER APPROVAL.**

Một cuộc thảo luận chưa kết thúc không được xem là approval.

---

# 8. CHANGE SCOPE LOCK

Sau khi được approve, phạm vi implementation phải được khóa.

Template:

```text
Approved scope:

Modify:
- ...

Create:
- ...

Delete:
- ...

Out of scope:
- ...
```

Ví dụ:

```text
Approved scope:

Modify:
- src/model.py
- tests/test_model.py

Create:
- run_training.bat

Out of scope:
- Database schema
- API contract
- UI
- Dependency upgrades
```

AI không được tự mở rộng scope.

Nếu cần sửa ngoài scope:

```text
STOP
→ Explain
→ Update scope
→ Get approval
```

---

# 9. IMPLEMENTATION RULES

Sau approval:

1. Ưu tiên minimal diff.
2. Chỉ sửa phần liên quan.
3. Không refactor unrelated code.
4. Không tự đổi architecture.
5. Không thêm dependency nếu không cần thiết.
6. Không xóa code chỉ vì AI nghĩ là thừa.
7. Không overwrite uncommitted work.
8. Không sửa technical debt ngoài scope.
9. Không thay behavior âm thầm.
10. Không kết hợp nhiều vấn đề không liên quan vào cùng task.

Nếu phát hiện thông tin mới làm proposal không còn đúng:

```text
STOP
→ Report finding
→ Update proposal
→ Discuss
→ Approval
```

---

# 10. GIT SAFETY PROTOCOL

Trước khi sửa:

```bash
git status
```

Nếu phù hợp:

```bash
git diff
```

AI phải phân biệt:

```text
Pre-existing user changes
vs
Changes made by AI
```

Không được claim toàn bộ diff là do AI tạo.

Không tự sử dụng:

```bash
git reset --hard
git clean -fd
git checkout -- .
```

Không force push nếu chưa có approval rõ ràng.

Uncommitted changes luôn được coi là có giá trị cho đến khi xác minh ngược lại.

---

# 11. ROLLBACK PLAN

Đối với thay đổi có mức rủi ro từ MEDIUM trở lên, phải xác định rollback plan.

Template:

```text
Rollback plan:

Previous commit:
Previous config:
Previous checkpoint:
Previous artifact:
Database rollback:
Other:
```

Nếu rollback không đơn giản, phải nói rõ trước khi triển khai.

---

# 12. TESTING PROTOCOL

AI được phép tự chạy test an toàn:

```text
Unit tests
Integration tests
Build
Lint
Type checking
Static analysis
Benchmark
Bug reproduction
Mock API tests
Local isolated DB tests
Checkpoint tests
Resume tests
```

Chỉ tự chạy khi:

- Không tác động production.
- Không sửa dữ liệu thật.
- Không deploy.
- Không gửi transaction thật.
- Không gửi email/message thật.
- Không gọi live trading system.

Báo cáo:

```text
Command:
Passed:
Failed:
Warnings:
Relevant result:
```

Không được nói:

```text
Tests pass.
```

nếu chưa thực sự chạy.

---

# 13. VERIFICATION LEVELS

Không dùng từ "DONE" mơ hồ.

Phân biệt:

```text
IMPLEMENTED
TESTED
VERIFIED
USER-RUN VERIFIED
```

Ví dụ:

```text
Implementation: DONE
Unit tests: PASS
Integration tests: PASS
Local validation: PASS
Real training run: NOT VERIFIED
User-run validation: NOT VERIFIED
```

AI không được nâng trạng thái lên `VERIFIED` nếu bằng chứng chưa đủ.

---

# 14. REAL RUN PROTOCOL

Phân biệt:

```text
TEST / VALIDATION
```

với:

```text
REAL RUN
```

AI được chạy validation an toàn.

Đối với real run:

- Full model training.
- Full backtest.
- Hyperparameter optimization.
- Production pipeline.
- Large Monte Carlo.
- Database migration.
- Live application.
- Live trading.

AI không tự chạy thay người dùng.

Phải tạo `.bat`.

Ví dụ:

```text
run_training.bat
resume_training.bat
run_backtest.bat
run_optimization.bat
run_pipeline.bat
run_app.bat
```

Người dùng chạy:

```powershell
.\run_training.bat
```

`.bat` phải:

- Hiển thị progress.
- Hiển thị error rõ ràng.
- Không swallow stderr.
- Có exit code.
- Có timestamp khi hữu ích.
- Dừng nếu critical step fail.
- Không tự đóng ngay khi lỗi.
- Kiểm tra checkpoint trước.
- Ưu tiên resume.

Ví dụ:

```text
[1/6] Checking environment...
[2/6] Checking configuration...
[3/6] Checking checkpoint...
[4/6] Preparing run...
[5/6] Starting...
[6/6] Finished.
```

---

# 15. CHECKPOINT PROTOCOL

Mọi tiến trình dài hoặc tốn compute phải hỗ trợ checkpoint.

Áp dụng đặc biệt cho:

```text
Machine learning training
Deep learning training
Hyperparameter optimization
Grid search
Bayesian optimization
Walk-forward optimization
Long backtests
Monte Carlo simulations
Large preprocessing
Feature generation
Batch jobs
Research pipelines
```

Không chấp nhận:

```text
Start
→ Run for hours
→ Save only at the end
```

---

# 16. RESUME-FIRST RULE

Trước workflow dài:

```text
[ ] Existing checkpoint checked
[ ] Experiment ID verified
[ ] Run ID verified
[ ] Config verified
[ ] Dataset verified
[ ] Architecture verified
[ ] Checkpoint integrity verified
[ ] Resume possibility determined
```

Nếu checkpoint hợp lệ:

> **RESUME BEFORE RESTART.**

Không được chạy lại từ đầu chỉ vì dễ hơn.

---

# 17. CHECKPOINT CONTENT

Checkpoint nên lưu khi phù hợp:

```text
Model state
Optimizer state
Scheduler state
Epoch
Global step
Best metric
Current metric
Training history
Hyperparameters
Configuration
Random seeds
RNG state
Mixed precision scaler
Early stopping state
Dataset version
Feature configuration
Train/validation/test periods
Git commit
Experiment ID
Run ID
Timestamp
```

Chỉ lưu weights không nhất thiết đủ để resume.

---

# 18. CHECKPOINT STRATEGY

Nên có tối thiểu:

```text
latest
best
```

`latest`:

> Resume sau interruption.

`best`:

> Model tốt nhất theo metric đã định nghĩa trước.

Không giả định:

```text
latest == best
```

---

# 19. CHECKPOINT FREQUENCY

Checkpoint theo:

```text
N epochs
N steps
N minutes
Every fold
Every trial
Every walk-forward window
Every major pipeline stage
```

Job chạy nhiều giờ không được chỉ save khi hoàn tất.

---

# 20. SAFE CHECKPOINT WRITING

Ưu tiên atomic save:

```text
save temporary
→ verify
→ replace latest
```

Ví dụ:

```text
latest.tmp
→ latest.ckpt
```

Crash khi save không được phá checkpoint hợp lệ trước đó.

---

# 21. CHECKPOINT VALIDATION

Không xem checkpoint là tốt chỉ vì file tồn tại.

Kiểm tra:

```text
[ ] File loads
[ ] Model loads
[ ] Optimizer loads
[ ] Architecture compatible
[ ] Config compatible
[ ] Dataset compatible
[ ] Epoch/step valid
[ ] No corruption
```

Workflow quan trọng phải test:

```text
save
→ terminate
→ load
→ resume
```

---

# 22. ENVIRONMENT SNAPSHOT

Với ML/quant hoặc workflow phụ thuộc môi trường, lưu:

```text
OS:
Python:
Compiler:
PyTorch:
TensorFlow:
CUDA:
cuDNN:
NumPy:
Pandas:
GPU:
GPU driver:
CPU:
Package lock/hash:
Other critical libraries:
```

Nếu environment khác giữa hai experiment:

> Không mặc định kết quả hoàn toàn comparable.

---

# 23. DATA / MODEL SAFETY PROTOCOL

Phần này bắt buộc với:

- Quant research.
- ML.
- Time-series.
- Backtesting.
- Trading strategies.
- Portfolio/risk modeling.

---

# 24. NO LOOK-AHEAD BIAS

Không sử dụng thông tin tương lai để tạo decision trong quá khứ.

Kiểm tra đặc biệt:

```text
rolling()
shift()
resample()
center=True
future labels
aggregation
normalization
indicator computation
execution price
timestamp alignment
```

Nếu signal chỉ biết sau khi candle `t` đóng:

```text
execution >= t + 1
```

trừ khi execution model được định nghĩa khác rõ ràng.

---

# 25. NO DATA LEAKAGE

Validation/test không được ảnh hưởng:

```text
Scaler
Normalizer
Feature selection
PCA
Imputation
Distribution fitting
Threshold selection
Hyperparameter tuning
Model selection
```

Sai:

```text
fit preprocessing on entire dataset
→ split
```

Đúng:

```text
split
→ fit on train
→ transform validation/test
```

---

# 26. TIME-SERIES SPLIT INTEGRITY

Không random shuffle time series nếu không có lý do hợp lệ.

Ưu tiên:

```text
TRAIN
→ VALIDATION
→ TEST
```

theo chronology.

Nếu dùng:

```text
Walk-forward
Rolling window
Expanding window
Purged CV
Embargo
```

phải ghi configuration.

---

# 27. DATA PROVENANCE / DATA CONTRACT

Mỗi dataset quan trọng phải có metadata:

```text
Dataset name:
Source:
Version:
Hash:
Rows:
Columns:
Time range:
Timezone:
Frequency:
Primary key:
Expected columns:
Dtypes:
Missing-data policy:
Duplicate policy:
Outlier policy:
Filtering rules:
Resampling rules:
```

AI không được âm thầm thay:

- Timezone.
- Frequency.
- Missing data behavior.
- Duplicate handling.
- Filter rules.
- Resampling logic.

---

# 28. DATASET IMMUTABILITY

Không âm thầm thay:

```text
Dataset
Sample period
Symbols
Frequency
Filtering
Outlier rules
Train period
Validation period
Test period
```

để tạo kết quả đẹp hơn.

Mọi thay đổi dataset phải được ghi lại.

---

# 29. EXPERIMENT CONFIGURATION

Mỗi experiment quan trọng phải ghi:

```text
Experiment ID:
Run ID:

Parent experiment:

Dataset:
Dataset version/hash:

Features:

Train period:
Validation period:
Test period:

Random seed:

Model:
Model parameters:

Optimizer:
Learning rate:

Loss:

Transaction cost:
Commission:
Slippage:
Spread:

Execution assumptions:

Initial capital:
Position sizing:
Leverage:
Margin:

Primary metric:
Secondary metrics:

Baseline:

Git commit:

Environment:

Checkpoint path:
Output path:
```

---

# 30. EXPERIMENT LINEAGE

Mỗi experiment nên có parent nếu được phát triển từ experiment trước.

Ví dụ:

```text
Experiment:
EXP-024

Parent:
EXP-017

Changed:
- Error distribution: Gaussian → Student-t
- learning_rate: 0.001 → 0.0005

Unchanged:
- Dataset
- Features
- Train period
- Test period
- Costs
- Execution rules
```

Mục tiêu:

> Biết chính xác thay đổi nào dẫn đến kết quả nào.

---

# 31. SINGLE-VARIABLE CHANGE PRINCIPLE

Nếu mục tiêu là nghiên cứu ảnh hưởng của một yếu tố:

> Giữ các yếu tố khác cố định khi có thể.

Ví dụ so sánh:

```text
EGARCH Gaussian
vs
EGARCH Student-t
```

Không đồng thời đổi:

```text
Feature set
Window
Optimizer
Dataset
Training period
Execution assumptions
```

nếu muốn xác định riêng tác động của error distribution.

---

# 32. RANDOM SEED

Nếu experiment có stochastic component:

```text
Python seed:
NumPy seed:
PyTorch seed:
CUDA seed:
Other:
```

Nếu không đảm bảo full determinism:

```text
NON-DETERMINISTIC
Reason:
```

---

# 33. BASELINE-FIRST RULE

Không tuyên bố:

```text
model improved
strategy improved
performance improved
```

nếu chưa có baseline xác định trước.

Baseline phải ghi:

```text
Baseline ID:
Model/strategy:
Dataset:
Period:
Parameters:
Costs:
Slippage:
Seed:
Metrics:
```

---

# 34. FAIR MODEL COMPARISON

Khi so sánh model/strategy, giữ cố định khi có thể:

```text
Dataset
Train period
Validation period
Test period
Features
Costs
Slippage
Execution
Capital
Risk limits
Random seeds
Evaluation metric definitions
```

Nếu có khác biệt:

> Phải báo rõ.

---

# 35. METRIC DEFINITION REGISTRY

Không chỉ ghi tên metric.

Phải định nghĩa cách tính.

Ví dụ:

## Sharpe Ratio

```text
Return type:
Frequency:
Annualization factor:
Risk-free rate:
Gross/net:
Arithmetic/log:
```

## Sortino Ratio

```text
Target return:
Downside deviation definition:
Frequency:
Annualization:
```

## Max Drawdown

```text
Equity definition:
Realized/unrealized:
Gross/net:
Intraday/end-of-bar:
```

## CAGR

```text
Start/end convention:
Calendar basis:
```

Nếu metric definition thay đổi:

> Phải coi đó là một thay đổi methodology.

---

# 36. PRIMARY METRIC / NO CHERRY-PICKING

Primary metric phải được xác định trước experiment nếu có thể.

```text
Primary metric:
Secondary metrics:
Guardrail metrics:
```

Không được:

1. Chạy experiment.
2. Xem 20 metrics.
3. Chỉ báo metric đẹp nhất.

Nếu metric khác xấu đi, phải báo.

Ví dụ:

```text
Sharpe: improved
Max Drawdown: worse
Turnover: worse
Net Profit: unchanged
```

Không được giấu các trade-off này.

---

# 37. STATISTICAL UNCERTAINTY

Không chỉ báo point estimate khi uncertainty quan trọng.

Nếu phù hợp, bổ sung:

```text
Standard error
Confidence interval
Bootstrap interval
Number of observations
Number of trades
Number of independent periods
```

Ví dụ:

```text
Sharpe = 1.4
95% bootstrap interval = [...]
Trades = ...
```

---

# 38. MODEL SELECTION SAFETY

Không chọn model dựa trực tiếp vào final test set.

Ưu tiên:

```text
TRAIN
   ↓
VALIDATION / CV
   ↓
MODEL SELECTION
   ↓
FINAL TEST
```

Final test nên được giữ ngoài quá trình model selection.

---

# 39. OVERFITTING WARNING

AI phải cảnh báo khi có:

- Quá nhiều parameters.
- Quá nhiều trials.
- Nhiều rule được chỉnh dựa trên backtest.
- Performance quá tốt bất thường.
- Ít trades.
- Parameter sensitivity cao.
- Performance tập trung trong một đoạn nhỏ.
- Test set được xem quá nhiều lần.

Nếu phù hợp, kiểm tra:

```text
Out-of-sample
Walk-forward
Bootstrap
Monte Carlo
Sensitivity analysis
Parameter stability
Multiple-testing effects
```

---

# 40. BACKTEST SAFETY

Backtest phải ghi:

```text
Instrument:
Data period:
Frequency:

Signal timing:
Execution timing:

Fees:
Commission:
Spread:
Slippage:

Position sizing:
Leverage:
Margin:

Initial capital:

Missing data handling:
Corporate actions:
Execution assumptions:
```

Không mặc định:

```text
fees = 0
slippage = 0
```

nếu mục tiêu là đánh giá khả năng triển khai thực tế.

---

# 41. ARTIFACT REGISTRY

Mỗi run quan trọng nên ghi output chính thức.

```text
Experiment ID:
Run ID:

Model:
Checkpoint:
Metrics:
Predictions:
Backtest result:
Charts:
Logs:
Config:
Dataset snapshot:
Other outputs:
```

Mỗi artifact nên truy ngược được về:

```text
experiment_id
run_id
git_commit
dataset_version
config
```

Không để xảy ra:

> "Không biết file này được sinh từ model nào."

---

# 42. RESULT DIRECTORY CONVENTION

Khuyến nghị:

```text
experiments/
└── <experiment_name>/
    └── <run_id>/
        ├── config/
        ├── checkpoints/
        ├── metrics/
        ├── logs/
        ├── charts/
        ├── predictions/
        └── outputs/
```

Không đặt:

```text
final
final2
final_new
final_real
final_final
```

---

# 43. REPRODUCIBILITY COMMAND

Mỗi run quan trọng nên có một command chính thức để tái tạo.

Ví dụ:

```powershell
.\run_experiment_EXP024.bat
```

hoặc:

```bash
python train.py --config configs/EXP024.yaml
```

Command này phải được ghi cùng experiment metadata.

---

# 44. RESULT INTEGRITY RULE

Không được chỉnh thủ công:

```text
metrics
predictions
backtest results
experiment outputs
```

để làm kết quả đẹp hơn.

Nếu output sai:

```text
Fix code
→ rerun
→ generate new artifact
```

Không sửa kết quả bằng tay rồi coi là result hợp lệ.

---

# 45. NEGATIVE RESULTS ARE VALID

Một experiment không cải thiện kết quả vẫn là thông tin có giá trị.

Ví dụ:

```text
EXP-031:
Student-t did not outperform Gaussian under current setup.
```

Không tự thay configuration liên tục chỉ để cố tạo kết quả tốt hơn.

Negative result nên được lưu nếu nó giúp tránh lặp lại research không hiệu quả.

---

# 46. STOP CONDITIONS / FAIL-FAST

Workflow phải có điều kiện dừng.

Ví dụ:

```text
STOP if:
- Unexpected NaN/Inf
- Data schema mismatch
- Checkpoint cannot load
- Dataset hash changed unexpectedly
- Critical test regression
- Severe divergence
- Insufficient disk space
- Output path may overwrite another run
- Required environment missing
- Required config missing
- Data timestamps invalid
```

Không được tiếp tục chạy chỉ để "xem thử chuyện gì xảy ra" nếu có nguy cơ làm mất kết quả hoặc tạo output sai.

---

# 47. RESOURCE BUDGET

Trước experiment lớn nên xác định:

```text
Expected runtime:
Maximum acceptable runtime:

CPU:
RAM:
GPU:
VRAM:

Disk:
Maximum output size:

Number of trials:
Number of models:
Number of folds:
```

Nếu dự kiến vượt budget đáng kể:

> Thảo luận với người dùng trước.

AI không tự quyết định chạy grid search hàng chục nghìn combination nếu chưa được approve.

---

# 48. SECRETS & CREDENTIAL SAFETY

Không ghi:

```text
API keys
Passwords
Access tokens
Broker credentials
Database passwords
Private keys
```

vào:

```text
PROCESS.md
Source code
Committed config
Logs
Experiment metadata
```

Chỉ tham chiếu tên biến:

```text
BROKER_API_KEY
DATABASE_URL
OPENAI_API_KEY
```

Không in secret ra terminal/log.

---

# 49. KNOWN PITFALLS

Đây là danh sách ngắn các lỗi dễ tái phạm.

AI phải đọc mỗi session.

Ví dụ:

```text
- Check checkpoint before restarting training.
- Never fit preprocessing on entire dataset before split.
- Never use future candle information in signals.
- Never silently change the test window.
- Never overwrite best checkpoint with latest.
- Verify timestamp/timezone before backtesting.
```

**Của dự án này** (chi tiết: CLAUDE.md, các spec):

```text
- Dùng `py -3.13`, KHÔNG dùng `python` (3.12, không có thư viện).
- Cài lại torch có thể hỏng nó (đường dẫn Windows > 260 ký tự) — kiểm tra _C.cp313-win_amd64.pyd sau khi cài.
- Mọi tham số ước lượng (scaler, bỏ cột trùng lặp) chỉ khớp trên PHẦN HỌC của đúng lần học đó.
- Nhãn nhìn trước tới 24 nến: phải cắt bỏ nến học có nhãn chạm giai đoạn dự báo.
- Nhãn bị cắt ở cuối phiên → "đi ngang" phụ thuộc giờ; mốc so sánh phải theo giờ trong phiên.
- Dữ liệu dòng lệnh gãy năm 2023 do nhà cung cấp — không dùng mức tuyệt đối của các cột này.
- Profit khớp ở giá MỞ CỬA nến kế tiếp, không ở giá đóng cửa nến ra quyết định.
- So độ trôi theo năm chỉ trên năm đủ dữ liệu (năm thiếu tháng làm cột theo mùa "trôi" giả).
- File .bat phải xuống dòng kiểu Windows (CRLF) — đã ép bằng .gitattributes.
- Không commit data/, experiments/, ohlc_export.csv; không ghi mật khẩu/DSN (chỉ tên PG_DSN).
```

`Known Pitfalls` khác `Error Log`.

`Known Pitfalls`:

> Summary ngắn cần thấy ngay.

`Error Log`:

> Lịch sử chi tiết.

---

# 50. ERROR & LESSONS LOG

Template:

## ERR-XXX — Title

```text
Date:

Context:

Symptom:

Root cause:

Incorrect approach:

Correct solution:

Prevention rule:

Affected files:

Checkpoint impact:

Experiment impact:

Status:
OPEN / FIXED / MONITORING
```

Không ghi mọi typo nhỏ.

---

# 51. DECISION LOG

Template:

## DEC-XXX — Title

```text
Date:

Decision:

Reason:

Alternatives considered:

Trade-offs:

Affected modules:

Checkpoint compatibility:

Revisit conditions:

Status:
ACTIVE / SUPERSEDED / DEPRECATED
```

Ví dụ:

```text
Revisit when:
- Dataset > 100M rows
- Concurrent workers > 4
- Production deployment begins
```

Nếu bị thay thế:

```text
Superseded by: DEC-XXX
```

---

# 52. PROGRESS LOG

Chỉ lưu milestone có ý nghĩa.

Template:

## YYYY-MM-DD — Task

```text
Status:

Changes:

Files changed:

Validation:

Experiment ID:

Latest checkpoint:

Best checkpoint:

Artifacts:

Remaining:
```

Không dump toàn bộ terminal log.

---

# 53. CURRENT TASK HANDOFF

```text
Current task:
  Spec 008 — LSTM dự báo (tầng ① MODUS 2).

Current status:
  DISCUSSING. Code, 11 test, chạy thử GPU đã xong và đã push. Chờ 2 quyết định.

Approved scope:
  laplace/forecast/ (nhãn, lịch học, tiền xử lý từng vòng, mô hình, huấn luyện, chấm điểm),
  run_forecast.py, run_forecast.bat, tách assemble_features trong pipeline, bất biến #20.
  Đã duyệt THÊM bản thí nghiệm thứ ba "tự học không nhãn" (chưa code).

What has been investigated:
  - Nhãn (a): tỷ lệ đi ngang theo giờ trong phiên (bảng ở mục 5)
  - Chạy thử 1 seed / 1 epoch: LSTM thắng mốc tỷ lệ chung chỉ nhờ biết giờ trong phiên;
    phần đoán hướng: LSTM 0,6867 vs mốc 0,6928 (1 seed — không kết luận được)
  - Đơn vị reward: R, C, ½R+½C, ⅓ mỗi phần (đo trên 860 lệnh KESPT 2018–2022)
  - Đọc 3 repo phụ trợ: ARSH (chưa chốt số trạng thái), Distributional BB (xong), EGARCH-X (dữ liệu NGÀY)

What has been implemented:
  laplace/forecast/{labels,folds,prep,model,train,metrics}.py, run_forecast.py/.bat, tests/test_forecast.py

Files touched:
  Xem commit b6cc361, b3132fb.

Pre-existing user changes:
  Không có thay đổi chưa commit. Thư mục .kilo/ (công cụ khác) không thuộc repo — không đụng tới.

Tests already run:
  py -3.13 -m pytest tests/ -q → 123 passed (2026-10-01)
  py -3.13 run_forecast.py --smoke → chạy hết 8 lần học, đủ file

Experiment ID:
  Chưa có lần chạy thật. Chỉ có experiments/forecast/smoke_* (không dùng để kết luận).

Latest checkpoint / Best checkpoint:
  Chỉ của lần chạy thử.

Can resume:
  Có — chạy lại `run_forecast.bat <run-id>` thì chạy tiếp từ ckpt_latest.pt.

Known issue:
  Tiêu chí chấm trong spec 008 mục 6 so với mốc tỷ lệ chung — mốc này thua một mốc chỉ
  biết giờ trong phiên. Giữ tiêu chí cũ thì kết quả "đạt" không chứng minh đoán được hướng.

Next recommended action:
  1. Người dùng chốt tiêu chí (đề xuất A) và thiết kế bản thứ ba (đề xuất T2 + Huber)
  2. Sửa metrics.py + phần tổng hợp run_forecast.py; viết bản thứ ba; test; commit
  3. Người dùng chạy run_forecast.bat (ước tính < 30 phút)

Do NOT:
  - Nhìn tập test 2023+ (chỉ mở một lần ở cuối, ghi sổ specs/SO-LAN-NHIN-TAP-TEST.md)
  - Kết luận từ lần chạy thử hoặc từ một seed
  - Nhắc tới phí / thuế
  - Dùng lệnh `python` (là 3.12 không có thư viện) — dùng `py -3.13`

Waiting for user decision on:
  1. Tiêu chí chấm LSTM:
     A — mốc = tỷ lệ lên/xuống/đi ngang theo từng giờ trong phiên (khớp trên phần học);
         tiêu chí chính chỉ trên nến có nhãn lên/xuống: sai số thấp hơn mốc ở trung bình
         10 seed VÀ ở ≥ 8/10 seed          [đề xuất]
     B — chỉ giữ nến còn ≥ 24 nến tới cuối phiên (mất ~47 % dữ liệu)
     C — bỏ 19 cột giờ trong phiên khỏi đầu vào LSTM
  2. Bản thứ ba "tự học không nhãn": mục tiêu T1 (giá trị đặc trưng nến t+1) hay
     T2 (thay đổi đặc trưng từ t sang t+1) [đề xuất]; sai số Huber [đề xuất] hay bình phương
```

---

# 54. CURRENT CHECKPOINT STATUS

```text
Experiment:   chưa có lần chạy thật
Run:          experiments/forecast/smoke_20261001_142056 (chạy thử, 1 seed, 1 epoch)

Latest checkpoint: chỉ của lần chạy thử
Created:           2026-10-01
Progress:          8/8 lần học (chạy thử)

Best checkpoint:   chỉ của lần chạy thử
Metric:            entropy chéo head (a) trên 10 % cuối phần học
Value:             —

Resume status:
  VERIFIED ở mức test (test_checkpoint_resume_restores_training_state: học 4 epoch liền =
  học 2 epoch, dừng, chạy tiếp). NOT VERIFIED trên lần chạy thật bị ngắt.

Last successful resume test: 2026-10-01 (pytest)
```

---

# 55. NEXT ACTIONS

```text
[ ] Người dùng chốt tiêu chí chấm LSTM (A/B/C) và thiết kế bản thứ ba
[ ] Sửa phần chấm điểm; code bản thứ ba; test; commit
[ ] Người dùng chạy run_forecast.bat → đọc summary.json, ghi kết quả vào spec 008
[ ] Nếu LSTM đạt: thiết kế Meta (nhãn "lệnh thành công", đầu ra P(thành công), 10 seed → trung bình?)
[ ] Nếu LSTM không đạt: dừng lại bàn hướng khác trước khi xây Meta/PPO
[ ] PPO: bỏ đảo chiều, khớp ở giá mở cửa nến sau, reward ½R + ½C, đầu vào từ Meta (một spec)
[ ] Đo lại mức may rủi của PPO trên valid 2022
[ ] Việc tối ưu đã ghi: số nến LSTM nhìn lại (64), độ dài h_t (64), cửa sổ ATR 51 và "1 năm"
[ ] Lọc đặc trưng: tương quan 0,95 → mRMR (so với mốc 468 cột)
[ ] Mô hình phụ trợ: DBB, EGARCH-X (học lại từng vòng), ARS khi ARSH v0.6
[ ] Front-end theo dõi/điều khiển — bàn sau lần chạy LSTM đầu tiên
```

Danh sách này không phải authorization để code. Mỗi task mới vẫn phải qua:

```text
Inspect
→ Discuss
→ Approval
```

---

# 56. TECHNICAL DEBT / RISKS

Template:

## RISK-XXX — Title

```text
Area:

Description:

Impact:
LOW / MEDIUM / HIGH / CRITICAL

Likelihood:
LOW / MEDIUM / HIGH

Suggested remediation:

Status:
```

Không tự sửa technical debt ngoài scope.

---

# 57. CONTEXT HYGIENE

`PROCESS.md` là living operational document.

Không biến file thành kho chứa mọi lịch sử.

Giữ tại đây:

- Current state.
- Current handoff.
- Active decisions.
- Important pitfalls.
- Active risks.
- Current checkpoint.
- Core protocols.

Không giữ:

- Chain-of-thought.
- Terminal logs hàng nghìn dòng.
- Full source code.
- Historical noise.
- Typo nhỏ.

---

# 58. ARCHIVE POLICY

Khi lịch sử dài, chuyển sang:

```text
docs/
└── process/
    ├── ERRORS.md
    ├── DECISIONS.md
    ├── EXPERIMENTS.md
    ├── METRICS.md
    ├── DATASETS.md
    └── CHANGELOG_AI.md
```

`PROCESS.md` chỉ giữ summary và active information.

Ví dụ:

```text
PROCESS.md
→ current rules + current state

docs/process/ERRORS.md
→ historical errors

docs/process/EXPERIMENTS.md
→ full experiment history
```

---

# 59. DANGEROUS OPERATIONS

Không tự chạy:

```text
Production deployment
Live trading
Real financial orders
Production DB migration
DROP
TRUNCATE
Mass DELETE
Database reset
Delete checkpoints
Delete experiments
Delete datasets
git reset --hard
git clean -fd
Force push
Delete branch
Rotate credentials
Change secrets
Send real emails/messages
Modify production cloud infrastructure
```

Nếu cần:

```text
Explain
→ Discuss
→ Explicit approval
→ Prefer user-run command/.bat
```

---

# 60. ANTI-PATTERNS

AI không được:

```text
- Code trước rồi mới hỏi.
- Code ngay mà chưa inspect repository.
- Tự mở rộng approved scope.
- Refactor unrelated code.
- Tự đổi architecture.
- Thêm dependency vô lý.
- Claim tests pass khi chưa chạy.
- Claim model tốt hơn khi chưa có baseline.
- Thay dataset/test window âm thầm.
- Fit preprocessing bằng test data.
- Dùng future data trong signal.
- Cherry-pick metric.
- Chỉ báo positive results.
- Restart training mà chưa kiểm tra checkpoint.
- Save model chỉ khi training hoàn tất.
- Overwrite best checkpoint.
- Xóa checkpoint không cần thiết.
- Xóa uncommitted user work.
- Dump logs vào PROCESS.md.
- Lặp lại lỗi đã có trong Known Pitfalls.
- Chỉnh output thủ công.
- Over-engineer task đơn giản.
```

---

# 61. SESSION START CHECKLIST

```text
[ ] Read PROCESS.md
[ ] Read Current Status
[ ] Read Current Task Handoff
[ ] Read Known Pitfalls
[ ] Check git status
[ ] Check branch
[ ] Check uncommitted changes
[ ] Check current checkpoints
[ ] Check incomplete experiments
[ ] Inspect relevant code
[ ] Identify facts/assumptions/unknowns
[ ] Do NOT modify yet
[ ] Present findings
[ ] Present proposal
[ ] Wait for approval
```

---

# 62. LONG-RUN CHECKLIST

Trước train/backtest/optimization:

```text
[ ] Experiment ID created
[ ] Run ID created
[ ] Parent experiment recorded
[ ] Config saved
[ ] Dataset identified
[ ] Dataset hash/version recorded
[ ] Timezone verified
[ ] Train period recorded
[ ] Validation period recorded
[ ] Test period recorded
[ ] Features recorded
[ ] Seeds recorded
[ ] Environment recorded
[ ] Baseline recorded
[ ] Primary metric defined
[ ] Secondary metrics defined
[ ] Metric definitions verified
[ ] Transaction costs recorded
[ ] Slippage recorded
[ ] Execution assumptions recorded
[ ] Existing checkpoint checked
[ ] Resume possibility checked
[ ] Checkpoint interval defined
[ ] Latest checkpoint configured
[ ] Best checkpoint configured
[ ] Best metric defined
[ ] Output directory checked
[ ] No overwrite risk
[ ] Logging configured
[ ] Disk space checked
[ ] Resource budget checked
[ ] Save/load checkpoint tested
[ ] .bat prepared for real run
```

---

# 63. SESSION END CHECKLIST

```text
[ ] Update Current Status
[ ] Update Current Task Handoff
[ ] Update Progress Log
[ ] Record important errors
[ ] Update Known Pitfalls
[ ] Record technical decisions
[ ] Record latest checkpoint
[ ] Record best checkpoint
[ ] Record resume status
[ ] Record experiment artifacts
[ ] Record negative results if useful
[ ] Record remaining risks
[ ] Archive old history if necessary
[ ] Do not mark VERIFIED without evidence
```

---

# 64. DEFINITION OF DONE

Một task chỉ được xem là DONE khi các mục phù hợp được xác minh:

```text
[ ] Requirement implemented
[ ] Approved scope respected
[ ] Relevant tests pass
[ ] Build passes
[ ] Lint/type check passes
[ ] No known regression
[ ] No unrelated modifications
[ ] Error handling checked
[ ] No temporary debug code
[ ] No secrets exposed
[ ] Checkpoint implemented for long-running jobs
[ ] Resume verified
[ ] Data leakage checked
[ ] Look-ahead bias checked
[ ] Dataset/version recorded
[ ] Train/validation/test periods recorded
[ ] Random seed recorded
[ ] Baseline comparison fair
[ ] Metric definitions consistent
[ ] Costs/slippage recorded
[ ] Artifacts registered
[ ] Reproduction command exists
[ ] PROCESS.md updated
```

Nếu chưa kiểm tra:

```text
NOT VERIFIED
```

Không suy diễn thành PASS.

---

# 65. FINAL REPORT FORMAT

Sau implementation:

## Changed

```text
What changed:
```

## Approved Scope

```text
Scope respected:
YES / NO

Out-of-scope changes:
None / ...
```

## Files

```text
Files modified:
Files created:
Files deleted:
```

## Validation

```text
Commands:

Passed:
Failed:
Warnings:
```

## Verification Level

```text
IMPLEMENTED:
TESTED:
VERIFIED:
USER-RUN VERIFIED:
```

## Data / Model Safety

Nếu liên quan:

```text
Look-ahead check:

Leakage check:

Dataset:
Version/hash:

Train:
Validation:
Test:

Seed:

Baseline:

Primary metric:

Costs:
Slippage:
```

## Checkpoints

```text
Latest:

Best:

Interval:

Resume:
VERIFIED / NOT VERIFIED
```

## Artifacts

```text
Model:
Metrics:
Predictions:
Backtest:
Charts:
Logs:
Config:
```

## Remaining Risks

```text
None / ...
```

## User Action

Nếu cần real run:

```powershell
.\run_xxx.bat
```

Sau đó mô tả người dùng cần quan sát điều gì.

---

# 66. CORE PRINCIPLES

> **Inspect before proposing.**

> **Discuss before implementing.**

> **Lock the scope after approval.**

> **Test before claiming success.**

> **Checkpoint before risking hours of computation.**

> **Resume before restarting.**

> **Preserve existing user work.**

> **Know which data produced which result.**

> **Know which code and config produced which artifact.**

> **Define metrics before comparing models.**

> **Use a fixed baseline before claiming improvement.**

> **Report trade-offs, not only improvements.**

> **Never let future information leak into the past.**

> **Never silently change the experiment to get a better result.**

> **Negative results are valid research results.**

> **A result that cannot be reproduced should not be trusted as a final result.**

> **Record enough information so another AI—or the user months later—can understand exactly what happened.**
