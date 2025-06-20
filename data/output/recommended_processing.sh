#!/bin/bash
# Recommended processing order based on analysis

# Step 1: Process PyMuPDF files (fastest)
./process_single_framework.sh actful # 13 PyMuPDF files
./process_single_framework.sh ap_guides # 40 PyMuPDF files
./process_single_framework.sh ap_guides_dl # 1 PyMuPDF files
./process_single_framework.sh briefs # 6 PyMuPDF files
./process_single_framework.sh c3_framework # 2 PyMuPDF files
./process_single_framework.sh common_core # 4 PyMuPDF files
./process_single_framework.sh common_core_ela # 6 PyMuPDF files
./process_single_framework.sh common_core_math # 2 PyMuPDF files
./process_single_framework.sh course_guides # 13 PyMuPDF files
./process_single_framework.sh isca # 1 PyMuPDF files
./process_single_framework.sh iste # 1 PyMuPDF files
./process_single_framework.sh ncas # 12 PyMuPDF files
./process_single_framework.sh ngss # 14 PyMuPDF files
./process_single_framework.sh p.e_ # 3 PyMuPDF files
./process_single_framework.sh student_guides # 3 PyMuPDF files

# Step 2: Process Docling files
./process_single_framework.sh course_guides # 10 Docling files
