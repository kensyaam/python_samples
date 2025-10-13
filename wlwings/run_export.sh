#!/bin/bash
# 引数: $1=input_dir, $2=output_dir(任意), $3以降=オプション

source .venv/Scripts/activate
python export_excel_to_pdf.py "$@"
deactivate
