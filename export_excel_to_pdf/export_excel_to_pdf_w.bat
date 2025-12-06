@echo off
setlocal
:: 引数: %1=input_dir, %2以降=オプション

@REM python export_excel_to_pdf.py %*

set VENV_PYTHON=%~dp0.venv\Scripts\python.exe
if not exist "%VENV_PYTHON%" (
    echo [ERROR] 仮想環境が見つかりません: %VENV_PYTHON%
    echo 先に "python -m venv .venv" を実行してください。
    pause
    exit /b 1
)

"%VENV_PYTHON%" export_excel_to_pdf.py %*

endlocal
pause
