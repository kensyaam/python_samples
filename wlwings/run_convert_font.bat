@echo off
setlocal
:: ˆø”: %1=input_dir_or_file

@REM python convert_excel_font.py %*

set VENV_PYTHON=%~dp0.venv\Scripts\python.exe
if not exist "%VENV_PYTHON%" (
    echo [ERROR] ‰¼‘zŠÂ‹«‚ªŒ©‚Â‚©‚è‚Ü‚¹‚ñ: %VENV_PYTHON%
    echo æ‚É "python -m venv .venv" ‚ğÀs‚µ‚Ä‚­‚¾‚³‚¢B
    pause
    exit /b 1
)

"%VENV_PYTHON%" convert_excel_font.py %*

endlocal
pause
