#!/bin/bash
# 引数: $1=input_dir, $2以降=オプション

source .venv/Scripts/activate
python export_excel_to_pdf.py "$@"
deactivate
