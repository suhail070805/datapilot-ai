# DataPilot AI — Data Studio

A premium dark dashboard for multi-file data profiling, filtering, cleaning, merging and export. Built for local use in VS Code with Flask + pandas.

## Requirements
- Python 3.10 or newer
- Internet connection on first run to install Python packages (the app itself runs locally afterward)

## Run on Windows (one click)
1. Extract this ZIP.
2. Open the extracted folder in VS Code.
3. Double-click `run.bat`, or run `run.bat` from the VS Code terminal.
4. The script creates a virtual environment, installs dependencies, starts the server and opens `http://127.0.0.1:5000`.

If Windows blocks the script, open the VS Code terminal and run:
```powershell
.\run.bat
```

## Run on macOS / Linux
```bash
chmod +x run.sh
./run.sh
```

## Features
- Multi-file upload: CSV, XLSX, XLS, text-based PDF.
- Dataset profiling: rows, columns, inferred data types, missing values, unique counts, sample values and numeric summaries.
- Dynamic column-aware filters (up to eight conditions): discover actual distinct values, search the list, and select multiple brands/providers/values per condition. Multiple values within one column use OR; separate column conditions use AND.
- Review-before-download workflow: upload files, analyze the columns, choose filters and cleaning options, generate a cleaned/merged preview (up to 50 rows), confirm that the preview looks correct, and only then unlock CSV/Excel/PDF downloads. Any filter or cleaning-option change locks downloads until a fresh preview is generated and confirmed.
- Cleaning options: trim whitespace, turn blank text into missing values, fill missing values (numeric median / categorical mode), remove duplicate rows.
- Merge files by stacking rows and aligning columns by column name; different schemas are preserved with blank values where a column is absent.
- Download the merged and cleaned result as CSV, Excel workbook or PDF report.

## Important limitations
- PDF support extracts selectable text into page/text rows. It does not perform OCR on scanned-image PDFs and does not recover complex tables reliably.
- The built-in “AI-style” analysis is deterministic statistical profiling and rule-based cleaning; it does not call a cloud AI model. It avoids sending uploaded data to a third-party AI service.
- Filters are exact value matches. Multiple selected values within the same column are ORed; separate column conditions are ANDed. A condition with no checked values is ignored.
- PDF export is a compact report (up to 200 rows and the first five columns). CSV and Excel export all filtered/cleaned data.
- Excel files are merged by column names; files with different columns are aligned into one union schema.
- This is a local development project, not a hardened public production deployment. Do not expose it to the public internet without adding authentication, CSRF protection, stricter file validation and deployment hardening.
