@echo off
setlocal
:: ����: %1=input_dir, %2=output_dir(�C��), %3�ȍ~=�I�v�V����

@REM python export_excel_to_pdf.py %*

set VENV_PYTHON=%~dp0.venv\Scripts\python.exe
if not exist "%VENV_PYTHON%" (
    echo [ERROR] ���z����������܂���: %VENV_PYTHON%
    echo ��� "python -m venv .venv" �����s���Ă��������B
    pause
    exit /b 1
)

"%VENV_PYTHON%" export_excel_to_pdf.py %*

endlocal
pause
