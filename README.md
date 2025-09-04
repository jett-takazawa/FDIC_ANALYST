# FDIC Data Agent

A production‑ready toolkit to **ingest, normalize, analyze, and narrate** U.S. banking market data using FDIC Summary of Deposits (SOD) and IRS ZIP‑code statistics. It combines a local analytics warehouse with LLM‑powered agents for natural‑language questions and automated reporting (the **Local + LLM** pattern).

I built a system that turns ad-hoc questions into board-ready visuals in minutes—not hours. During my internship, meetings often veered into new tangents and stakeholders asked for data we hadn’t prepped. This tool lets analysts use plain-English queries to instantly generate clean, on-brand PowerPoint decks, so conversations stay data-driven and momentum never stalls.

This project was built June of 2025 in Honolulu, HI, for the use of Bank of Hawaii. Built to only scan and transform data from HAWAII BASED BANKS. 

---

## TL;DR

* **Goal:** ZIP‑level market‑share and growth analysis for banks/credit unions; generate explainable briefs and exportables.
* **Stack:** Python • Pandas • PyArrow/Parquet • SQLAlchemy • DuckDB/SQLite/Postgres • (optional) GeoPandas • gspread • n8n hooks • OpenAI / Vertex AI.
* **Pattern:** Heavy work runs **locally** in SQL/dataframes; LLMs translate questions → safe SQL + prose.

---


## Query

"Show me the market distribution in Manoa"

# Result:

20250902_231214_Manoa Deposit Analysis in 2024.pptx
<img width="1549" height="872" alt="image" src="https://github.com/user-attachments/assets/b5a824a4-15bf-475a-bdfc-2df579ba5cb0" />

---

## Features

* **End‑to‑end ETL** for FDIC SOD and IRS SOI (ZIP) datasets with idempotent runs and caching.
* **Local warehouse** (DuckDB by default) with versioned schema & snapshotting.
* **Analytics library** for market share, YoY, CAGR, and ZIP/state rollups.
* **Agentic reporting** that writes Markdown/PDF briefs and Sheets exports.
* **Plugin system** (first‑party + optional) to add sources, storages, and exporters without touching core.

---

## Architecture

```
FDIC SOD files / API  ─┐
                       ├─► Ingestors ─► Normalizers ─► Local Warehouse (DuckDB/SQLite/Postgres)
IRS SOI ZIP datasets ──┘                                              │
                                                             Analytics / MatplotLIB
                                                                      │
                                         ┌─────────────── LLM Agents (QueryAgent, ReportAgent) ───────────────┐
                                         │   NL question → safe SQL → result frames → narrative & visuals     │
                                         └─────────────────────────────────────────────────────────────────────┘
                                                                      │
                                                  Exporters (Powerpoint.pptx)
```

**Local + LLM:** The database and analytics run on your machine/server; LLMs are used only for query composition and narrative writing, never as the source of numeric truth.

---

## Repository Structure

```
fdic_agent/
  __init__.py
  cli.py                      # `fdic-agent` entrypoint

  config/
    settings.example.yaml     # central config

  etl/
    ingest_fdic.py            # download/parse FDIC SOD (CSV/XLS/ZIP/API)
    ingest_irs.py             # download/parse IRS SOI ZIP datasets
    normalize.py              # type/column normalization, ZIP cleaning
    load.py                   # batch loaders into DB (UPSERTs)

  db/
    models.py                 # SQLAlchemy models
    schema.sql                # canonical DDL (for non‑ORM engines)
    queries.sql               # vetted SQL snippets used by agents

  analytics/
    market_share.py           # market share, YoY, CAGR, top N
    zip_rollups.py            # ZIP/state aggregations, crosswalk helpers
    metrics.py                # common KPIs & helpers

  agents/
    base.py                   # tool registry, safety rails, tracing
    query_agent.py            # NL → SQL tool; validates against `queries.sql`
    report_agent.py           # narrative report builder (Jinja2 templates)
    router.py                 # small policy router (when/which tool to use)

  plugins/                    # first‑party plugins (see matrix below)
    fdic_sod/
    irs_soi_zip/
    duckdb_storage/
    sqlite_storage/
    postgres_storage/
    sheets_exporter/
    markdown_reporter/
    pdf_reporter/
    geo_exporter/
    openai_llm/
    vertex_llm/
    n8n_tasks/

  app/
    api.py                    # optional FastAPI for programmatic calls
    ui_streamlit.py           # optional Streamlit UI

  notebooks/
    examples.ipynb

  tests/
    test_etl_*.py
    test_analytics_*.py
    test_agents_*.py

data/
  raw/        # downloaded archives
  interim/    # cleaned but not loaded
  processed/  # analytics outputs
  warehouse/  # DuckDB file / SQLite DB
```

---

## Plugins (Built‑In & Optional)

> Enable/disable via `config/settings.yaml` or environment variables. Most are optional.

| Plugin              | Type        | Purpose                                                     | Enable via                                           | Key env/config                                                |
| ------------------- | ----------- | ----------------------------------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------- |
| `fdic_sod`          | Data source | Pull FDIC Summary of Deposits releases (CSV/XLS/ZIP or API) | `plugins.sources.fdic_sod.enabled=true`              | `FDIC_SOD_URL` (optional override)                            |
| `irs_soi_zip`       | Data source | Pull IRS SOI ZIP‑code stats (returns, AGI, etc.)            | `plugins.sources.irs_soi_zip.enabled=true`           | `IRS_SOI_URL` (optional override)                             |
| `duckdb_storage`    | Storage     | Default local warehouse                                     | `warehouse.url=duckdb:///data/warehouse/fdic.duckdb` | —                                                             |
| `sqlite_storage`    | Storage     | Lightweight portable DB                                     | `warehouse.url=sqlite:///data/warehouse/fdic.sqlite` | —                                                             |
| `postgres_storage`  | Storage     | Remote or local Postgres                                    | `warehouse.url=postgresql+psycopg://...`             | `DATABASE_URL`                                                |
| `markdown_reporter` | Export      | Write Markdown briefs (Jinja2)                              | `plugins.export.markdown.enabled=true`               | `REPORT_DIR`                                                  |
| `pdf_reporter`      | Export      | Render PDFs from Markdown                                   | `plugins.export.pdf.enabled=true`                    | requires local PDF engine (e.g., wkhtmltopdf)                 |
| `sheets_exporter`   | Export      | Push tables to Google Sheets                                | `plugins.export.sheets.enabled=true`                 | `GSPREAD_SERVICE_ACCOUNT` or `GOOGLE_APPLICATION_CREDENTIALS` |
| `geo_exporter`      | Export      | GeoJSON/choropleths (ZIP)                                   | `plugins.export.geo.enabled=true`                    | installs `geopandas` extra                                    |
| `openai_llm`        | LLM         | Use OpenAI models for NL→SQL + narrative                    | `plugins.llm.provider=openai`                        | `OPENAI_API_KEY`                                              |
| `vertex_llm`        | LLM         | Use Gemini via `google.genai`                               | `plugins.llm.provider=vertex`                        | `GOOGLE_API_KEY` or Vertex creds                              |
| `n8n_tasks`         | Automation  | Webhook/run hooks for n8n                                   | `plugins.automation.n8n.enabled=true`                | `N8N_WEBHOOK_URL`                                             |

---

## Data Model (Core Tables)

* **`banks`**: `bank_id`, `name`, `rssd`, `fdic_cert`, `headquarters_state`, `active_flag` …
* **`branches`**: `branch_id`, `bank_id`, `address`, `city`, `state`, `zip`, `county_fips`, `lat`, `lon` …
* **`deposits_branch_year`**: `branch_id`, `year`, `deposits_usd`.
* **`zip_crosswalk`**: normalized ZIPs, aliasing (ZIP5), optional county/state joins.
* **`irs_zip_year`**: `zip`, `year`, `num_returns`, `agi_total`, other IRS ZIP metrics.
* **`zip_bank_year`** (fact): `zip`, `bank_id`, `year`, `deposits_usd`, `market_share_pct`, `yoy_pct`, `cagr_3y_pct` …

All numeric outputs used by agents are derived from this warehouse (never hallucinated).

---

## Installation

**Prereqs**

* [ ] Python ≥ 3.11
* [ ] `wkhtmltopdf` (only if using `pdf_reporter`)
* [ ] (optional) Postgres client libraries

```bash
# clone
git clone <your-repo-url> fdic-data-agent && cd fdic-data-agent

# create env
python -m venv .venv && source .venv/bin/activate

# install (core)
pip install -e .

# or with extras for geo, sheets, llm, dev
pip install -e ".[geo,sheets,openai,vertex,dev]"

# copy config
echo "(copying example settings)" && \
  cp fdic_agent/config/settings.example.yaml fdic_agent/config/settings.yaml
```

**Environment variables** (set as needed)

```bash
export DATABASE_URL="duckdb:///$(pwd)/data/warehouse/fdic.duckdb"
export OPENAI_API_KEY="sk-..."                    # if using OpenAI
export GOOGLE_API_KEY="..."                       # if using Vertex/GenAI
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/sa.json"  # Sheets/Vertex
export GSPREAD_SERVICE_ACCOUNT="/path/to/sa.json"
export REPORT_DIR="$(pwd)/reports"
```

## Code Walkthrough

* **`etl/ingest_fdic.py`**: Downloads/parses FDIC SOD releases; normalizes column names, types, and ZIPs. Handles annual versions & schema drift.
* **`etl/ingest_irs.py`**: Pulls IRS SOI ZIP files; normalizes ZIP/ZIP+4 down to ZIP5, casts numerics.
* **`etl/normalize.py`**: Dedupes branches, fixes malformed ZIPs, and creates crosswalks.
* **`etl/load.py`**: Batch UPSERT into target DB (chooses engine from `warehouse.url`).
* **`analytics/market_share.py`**: Computes market share by ZIP/year, YoY deltas, CAGR windows; outputs tidy frames.
* **`agents/query_agent.py`**: Validates user NL against an allow‑listed SQL library in `db/queries.sql`, then executes via SQLAlchemy.
* **`agents/report_agent.py`**: Renders human‑readable briefs (Markdown) from analytic frames; optional PDF rendering.
* **`plugins/*`**: First‑party plugin modules registered via a simple `register()` convention and discovered on startup.
* **`cli.py`**: Click/Typer‑based CLI wiring the above into cohesive commands.

---

## Safety & Reliability

* **SQL allow‑list** & schema introspection to gate LLM‑generated queries.
* **Deterministic ETL**: idempotent downloads, checksum caching, schema snapshots.
* **Traceability**: run metadata (source URLs, timestamps, hashes) stored in `_runs` tables.

---

## FAQ

**What is ETL?**

> **E**xtract (download data), **T**ransform (clean/normalize), **L**oad (write to the warehouse). This repo provides reproducible ETL for FDIC/IRS data.

**What does “Local + LLM” mean?**

> Compute lives **locally** (your DB & analytics). An **LLM** assists with query intent and summarization. Numbers always come from your warehouse.

**Can I use Postgres instead of DuckDB?**

> Yes—set `DATABASE_URL` (or `warehouse.url`) to your Postgres URI.

**Where do the raw files live?**

> Under `data/raw/` by default; intermediate cleaned assets in `data/interim/`.

---

## Roadmap

* [ ] HDMA/CRA overlays for lending & community assessments
* [ ] SBA 7(a)/504 overlays for small‑biz ecosystems
* [ ] Choropleth map UI for ZIP and county views
* [ ] Auto‑refresh via n8n (yearly SOD release)
* [ ] Packaged Docker image + compose

