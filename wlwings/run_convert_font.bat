@echo off
setlocal
:: ����: %1=input_dir_or_file

@REM python convert_excel_font.py %*

set VENV_PYTHON=%~dp0.venv\Scripts\python.exe
if not exist "%VENV_PYTHON%" (
    echo [ERROR] ���z����������܂���: %VENV_PYTHON%
    echo ��� "python -m venv .venv" �����s���Ă��������B
    pause
    exit /b 1
)

"%VENV_PYTHON%" convert_excel_font.py %*

endlocal
pause
