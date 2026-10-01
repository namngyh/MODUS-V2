@echo off
REM ======================================================================
REM  MODUS 2 - LSTM du bao (spec 008)
REM  Chay:          run_forecast.bat              (run-id mac dinh: lstm_v1)
REM                 run_forecast.bat ten_khac      (thi nghiem moi)
REM  Bi ngat:       chay lai DUNG lenh cu -> tu chay tiep tu checkpoint.
REM  KHONG xoa thu muc experiments\forecast\<run-id> khi bi ngat.
REM ======================================================================
setlocal
cd /d "%~dp0"
set RUN_ID=%1
if "%RUN_ID%"=="" set RUN_ID=lstm_v1

echo [1/4] Kiem tra Python 3.13...
py -3.13 --version
if errorlevel 1 (
    echo LOI: khong tim thay Python 3.13. Lenh "python" tren may nay la 3.12 khong co thu vien.
    goto :fail
)

echo [2/4] Kiem tra torch va GPU...
py -3.13 -c "import torch; print('torch', torch.__version__, '| CUDA:', torch.cuda.is_available())"
if errorlevel 1 (
    echo LOI: khong import duoc torch.
    goto :fail
)

echo [3/4] Kiem tra du lieu...
if not exist ohlc_export.csv (
    echo LOI: thieu ohlc_export.csv o thu muc goc.
    goto :fail
)
if exist "experiments\forecast\%RUN_ID%\run_config.json" (
    echo Da co thi nghiem %RUN_ID% - se CHAY TIEP tu checkpoint.
) else (
    echo Thi nghiem moi: %RUN_ID%
)

echo [4/4] Bat dau luc %date% %time%
py -3.13 run_forecast.py --run-id %RUN_ID%
if errorlevel 1 (
    echo LOI: run_forecast.py dung voi ma loi %errorlevel%. Xem experiments\forecast\%RUN_ID%\run.log
    goto :fail
)
echo.
echo XONG luc %date% %time%. Ket qua: experiments\forecast\%RUN_ID%\summary.json
pause
exit /b 0

:fail
echo.
echo Chua xong. Sua loi o tren roi chay lai dung lenh nay.
pause
exit /b 1
