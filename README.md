# Upwork JD Analyzer (Marketing + Sales focus)

This repo now includes a runnable Python script to analyze your Google Sheet (or CSV export) of Upwork job descriptions.

## What it does

Given columns:
- `Title`
- `URL`
- `Description`
- `Budget`
- `Skills Set`

it will:

1. **Filter** job descriptions related to **marketing/sales** using title + description keyword matching.
2. **Analyze** the filtered rows to extract:
   - client pain patterns (recurring pain keywords/phrases),
   - tools/apps/SaaS/platform mentions,
   - pairwise tool co-mentions (how often two tools appear in the same JD).
3. **Visualize** findings:
   - top tools bar chart,
   - tool co-mention heatmap,
   - top pain points bar chart.

## File

- `analyze_upwork_jds.py` — main script.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install pandas matplotlib seaborn
```

## Run

### Option A: Use local CSV export

```bash
python analyze_upwork_jds.py --csv /path/to/your_sheet.csv --outdir analysis_output
```

### Option B: Read directly from public Google Sheet

```bash
python analyze_upwork_jds.py --sheet-id YOUR_SHEET_ID --gid 0 --outdir analysis_output
```

> Note: direct Sheet read works only if the sheet is shared publicly (or otherwise accessible without auth).

## Outputs

Inside `analysis_output/`:

- `filtered_marketing_sales_jds.csv`
- `tool_counts.csv`
- `tool_cooccurrence.csv`
- `pain_points.csv`
- `top_tools.png`
- `tool_cooccurrence_heatmap.png` (when enough co-occurrences exist)
- `pain_points.png`

## Recommendation for your case

For ~1600 rows, this script is lightweight and should run quickly on your machine.

- If you want **one-time or occasional analysis**: run this script locally.
- If you want **continuous automation** (new rows daily/weekly): wrap this logic into an **n8n workflow** (Google Sheets trigger -> Code node/Python service -> save report).

If you want, next step I can generate:
1. an n8n workflow JSON template, or
2. a version that uses OpenAI for richer pain-point summarization.
