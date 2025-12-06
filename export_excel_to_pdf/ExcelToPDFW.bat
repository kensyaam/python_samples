@echo off
setlocal
:: 入力フォルダ: 固定（INPUT_DIRに設定）
:: 引数: %1以降=オプション

@REM export_excel_to_pdf.exe %*

:: 入力フォルダ
set INPUT_DIR="work"

ExcelToPDF.exe %INPUT_DIR% %*

:: ExcelToPDF.exe work %*

endlocal
pause
