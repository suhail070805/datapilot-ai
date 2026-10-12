from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np
import os, io, json, re
from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
ALLOWED = {".csv", ".xlsx", ".xls", ".pdf"}

def read_upload(file):
    name = secure_filename(file.filename or "upload")
    ext = os.path.splitext(name)[1].lower()
    if ext not in ALLOWED:
        raise ValueError(f"{name}: unsupported file type")
    if ext == ".csv":
        df = pd.read_csv(file)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(file)
    else:
        reader = PdfReader(file)
        rows = []
        for page_no, page in enumerate(reader.pages, 1):
            content = page.extract_text() or ""
            for line in content.splitlines():
                line = line.strip()
                if line:
                    rows.append({"page": page_no, "text": line})
        df = pd.DataFrame(rows)
        if df.empty:
            raise ValueError(f"{name}: no extractable text found in PDF")
    df.columns = [str(c).strip() or f"column_{i+1}" for i, c in enumerate(df.columns)]
    df["__source_file"] = name
    return df

def profile(df):
    result = []
    for col in df.columns:
        s = df[col]
        result.append({
            "name": str(col),
            "dtype": str(s.dtype),
            "non_null": int(s.notna().sum()),
            "missing": int(s.isna().sum()),
            "unique": int(s.nunique(dropna=True)),
            "sample": [str(x)[:90] for x in s.dropna().head(3).tolist()],
            # Distinct values power the dynamic, searchable multi-select filters.
            "distinct_values": [str(x) for x in s.dropna().astype(str).value_counts().head(300).index.tolist()],
            "value_count": int(s.nunique(dropna=True)),
            "values_truncated": bool(s.nunique(dropna=True) > 300)
        })
    return result

def clean_dataframe(df, fill_missing=True, remove_duplicates=True, trim_text=True):
    out = df.copy()
    if trim_text:
        for c in out.select_dtypes(include=["object"]).columns:
            out[c] = out[c].map(lambda x: x.strip() if isinstance(x, str) else x)
            out[c] = out[c].replace(r"^\s*$", np.nan, regex=True)
    before = len(out)
    if remove_duplicates:
        out = out.drop_duplicates()
    duplicates_removed = before - len(out)
    missing_filled = 0
    if fill_missing:
        for c in out.columns:
            count = int(out[c].isna().sum())
            if count == 0:
                continue
            if pd.api.types.is_numeric_dtype(out[c]):
                value = out[c].median()
                if pd.isna(value): value = 0
            else:
                modes = out[c].mode(dropna=True)
                value = modes.iloc[0] if not modes.empty else "Unknown"
            out[c] = out[c].fillna(value)
            missing_filled += count
    return out, {"duplicates_removed": duplicates_removed, "missing_values_filled": missing_filled}

def prepare_dataframe(uploads, filters=None, clean_opts=None):
    """Read, merge, filter and clean the uploaded files using the chosen options."""
    frames = [read_upload(f) for f in uploads if f.filename]
    if not frames:
        raise ValueError("Upload files first.")
    df = pd.concat(frames, ignore_index=True, sort=False)
    filters = filters or {}
    clean_opts = clean_opts or {}
    for col, value in filters.items():
        if col not in df.columns or value in (None, "", []):
            continue
        values = value if isinstance(value, list) else [value]
        df = df[df[col].astype(str).isin([str(v) for v in values])]
    filtered_rows = len(df)
    df, stats = clean_dataframe(
        df,
        fill_missing=clean_opts.get("fill_missing", True),
        remove_duplicates=clean_opts.get("remove_duplicates", True),
        trim_text=clean_opts.get("trim_text", True)
    )
    return df, stats, filtered_rows

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/api/analyze")
def analyze():
    uploads = request.files.getlist("files")
    if not uploads or not any(f.filename for f in uploads):
        return jsonify(error="Choose at least one file."), 400
    frames, names, warnings = [], [], []
    try:
        for f in uploads:
            if not f.filename: continue
            df = read_upload(f)
            frames.append(df); names.append(secure_filename(f.filename))
        # Union of columns is retained when combining files with different schemas.
        merged = pd.concat(frames, ignore_index=True, sort=False)
        return jsonify({
            "files": names, "rows": int(len(merged)), "columns": int(len(merged.columns)),
            "column_profile": profile(merged),
            "preview": json.loads(merged.head(12).replace({np.nan: None}).to_json(orient="records", date_format="iso")),
            "missing_total": int(merged.isna().sum().sum()),
            "duplicate_rows": int(merged.duplicated().sum()),
            "numeric_summary": json.loads(merged.select_dtypes(include="number").describe().round(3).to_json()),
            "note": "Analysis uses column types, missingness, uniqueness, samples, and numeric summaries. PDF files are converted to extracted text rows."
        })
    except Exception as e:
        return jsonify(error=f"Could not read the uploaded data: {str(e)}"), 400

@app.post("/api/preview")
def preview():
    uploads = request.files.getlist("files")
    try:
        filters = json.loads(request.form.get("filters", "{}"))
        clean_opts = json.loads(request.form.get("clean_options", "{}"))
        df, stats, filtered_rows = prepare_dataframe(uploads, filters, clean_opts)
        preview_df = df.head(50).replace({np.nan: None})
        return jsonify({
            "rows": int(len(df)), "columns": int(len(df.columns)),
            "filtered_rows": int(filtered_rows),
            "missing_remaining": int(df.isna().sum().sum()),
            "duplicates_removed": int(stats["duplicates_removed"]),
            "missing_values_filled": int(stats["missing_values_filled"]),
            "column_profile": profile(df),
            "preview": json.loads(preview_df.to_json(orient="records", date_format="iso")),
            "preview_limit": 50
        })
    except Exception as e:
        return jsonify(error=f"Could not prepare preview: {str(e)}"), 400

@app.post("/api/export")
def export():
    uploads = request.files.getlist("files")
    fmt = request.form.get("format", "csv").lower()
    filters = json.loads(request.form.get("filters", "{}"))
    clean_opts = json.loads(request.form.get("clean_options", "{}"))
    try:
        df, stats, _filtered_rows = prepare_dataframe(uploads, filters, clean_opts)
        buf = io.BytesIO()
        if fmt == "xlsx":
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Cleaned data")
            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = "datapilot_cleaned_merged.xlsx"
        elif fmt == "pdf":
            c = canvas.Canvas(buf, pagesize=letter)
            width, height = letter
            y = height - 40
            c.setFont("Helvetica-Bold", 14); c.drawString(40, y, "DataPilot AI — Cleaned merged data")
            y -= 24; c.setFont("Helvetica", 8)
            c.drawString(40, y, f"Rows: {len(df)} | Columns: {len(df.columns)} | Removed duplicates: {stats['duplicates_removed']}")
            y -= 20
            cols = list(df.columns)[:5]
            for _, row in df.head(200).iterrows():
                line = " | ".join(f"{col}: {str(row[col])[:35]}" for col in cols)
                c.drawString(40, y, line[:130]); y -= 12
                if y < 40:
                    c.showPage(); y = height - 40; c.setFont("Helvetica", 8)
            c.save()
            mimetype = "application/pdf"; filename = "datapilot_cleaned_merged.pdf"
        else:
            df.to_csv(buf, index=False)
            mimetype = "text/csv"; filename = "datapilot_cleaned_merged.csv"
        buf.seek(0)
        return send_file(buf, mimetype=mimetype, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify(error=f"Export failed: {str(e)}"), 400

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
