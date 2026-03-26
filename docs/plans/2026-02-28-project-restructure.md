# Project Restructure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reorganize arXiv-ai-Agent into an industry-standard open-source project layout that separates source code, scripts, documentation, and generated artifacts cleanly.

**Architecture:** Move all Python source modules into a `src/` package, consolidate scattered documentation into `docs/`, move utility scripts into `scripts/`, and ensure `output/` is the single location for generated reports.

**Tech Stack:** Python 3.11+, SQLAlchemy, Streamlit, APScheduler, uv

---

## Target Directory Structure

```
arXiv-ai-Agent/
├── README.md
├── QUICKSTART.md
├── CHANGELOG.md                  # New
├── requirements.txt
├── .env.example                  # New
├── .gitignore
│
├── main.py                       # Renamed from arxiv_daily_v3.py
├── arxiv_subjects.py             # Kept at root (standalone reference module)
│
├── src/                          # All source packages
│   ├── __init__.py
│   ├── config/
│   ├── models/
│   ├── core/
│   ├── pipeline/
│   ├── tools/
│   ├── database/
│   └── utils/
│
├── web/
│   └── app.py                    # Streamlit UI
│
├── scripts/                      # Executable scripts
│   ├── run.sh                    # Moved from root
│   ├── dev/                      # Dev/debug tools
│   │   └── test_direction_page.py
│   └── archive/                  # Existing archived scripts
│
├── docs/                         # All documentation
│   ├── guides/
│   │   ├── deployment.md         # From web/DEPLOYMENT_GUIDE.md
│   │   ├── color-guide.md        # From web/COLOR_GUIDE.md
│   │   └── dark-theme-guide.md   # From web/DARK_THEME_GUIDE.md
│   ├── plans/                    # This file lives here
│   └── archive/                  # Existing archived docs + root scattered docs
│
├── output/                       # All generated Markdown reports
│   └── (existing + moved from database/)
│
├── database/                     # Data layer only (no reports)
│   ├── __init__.py (will become src/database/__init__.py after move)
│   └── arxiv_papers.db
│
└── logs/                         # Log files
```

---

## Import Path Changes Required

After moving packages into `src/`, all imports change from:
```python
from config.settings import ...
from database.connection import ...
from core.scoring import ...
```
To:
```python
from src.config.settings import ...
from src.database.connection import ...
from src.core.scoring import ...
```

**Files requiring import updates:**
- `main.py` (renamed from `arxiv_daily_v3.py`) — 13 imports
- `web/app.py` — 5 imports
- `src/tools/call_jina.py` — 1 import (`config`)
- `src/tools/call_llm.py` — 2 imports (`config`, `models`)
- `src/tools/fetch_today.py` — 4 imports (`database`, `core`)
- `src/tools/rescore_papers.py` — imports to check
- `src/tools/import_historical_data.py` — imports to check
- `src/core/query_engine.py` — 4 imports (`database`, `core`)
- `src/core/scheduler.py` — imports to check
- `src/pipeline/stages.py` — 5 imports
- `src/pipeline/core.py` — imports to check

---

## Task 1: Create New Directory Structure

**Files:**
- Create: `src/__init__.py`
- Create: `scripts/dev/` directory
- Create: `docs/guides/` directory

**Step 1: Create src/ and subdirectories**

```bash
mkdir -p src
mkdir -p scripts/dev
mkdir -p docs/guides
touch src/__init__.py
```

**Step 2: Verify directories created**

```bash
ls src/ scripts/ docs/
```
Expected: directories exist

---

## Task 2: Move Source Packages into src/

**Files:**
- Move: `config/` → `src/config/`
- Move: `models/` → `src/models/`
- Move: `core/` → `src/core/`
- Move: `pipeline/` → `src/pipeline/`
- Move: `tools/` → `src/tools/`
- Move: `database/` → `src/database/` (Python files only, NOT the .db file)
- Move: `utils/` → `src/utils/`

**Step 1: Move Python source packages**

```bash
mv config src/config
mv models src/models
mv core src/core
mv pipeline src/pipeline
mv tools src/tools
mv utils src/utils
```

**Step 2: Move database Python package (keep .db file at root of database/)**

```bash
mkdir -p src/database
mv database/__init__.py src/database/
mv database/connection.py src/database/
mv database/models.py src/database/
mv database/repositories.py src/database/
```

**Step 3: Verify structure**

```bash
ls src/
```
Expected: `__init__.py config core database models pipeline tools utils`

---

## Task 3: Rename Entry Point and Move run.sh

**Files:**
- Rename: `arxiv_daily_v3.py` → `main.py`
- Delete: `arxiv_daily.py` (legacy, user confirmed)
- Move: `run.sh` → `scripts/run.sh`
- Move: `test_direction_page.py` → `scripts/dev/test_direction_page.py`

**Step 1: Rename main entry point**

```bash
mv arxiv_daily_v3.py main.py
rm arxiv_daily.py
```

**Step 2: Move scripts**

```bash
mv run.sh scripts/run.sh
mv test_direction_page.py scripts/dev/test_direction_page.py
```

**Step 3: Update run.sh to use new entry point name**

Edit `scripts/run.sh`: change `arxiv_daily.py` or `arxiv_daily_v3.py` to `main.py`

---

## Task 4: Update All Import Paths

Every file that imports from the moved packages needs `src.` prefix added.

**Step 1: Update main.py**

Change all bare module imports:
```python
# Before
from config.settings import get_settings
from database.connection import init_database, get_db_session
from database.repositories import PaperRepository
from core.scoring import MultiDimensionScorer, DEFAULT_DIRECTIONS
from core.scheduler import get_scheduler, init_default_schedule
from core.query_engine import PaperQueryEngine, TrendAnalyzer
from pipeline.core import Pipeline, PipelineContext
from pipeline.stages import FetchStage, ParseStage, GenerateReportStage, UploadStage, NotifyStage

# After
from src.config.settings import get_settings
from src.database.connection import init_database, get_db_session
from src.database.repositories import PaperRepository
from src.core.scoring import MultiDimensionScorer, DEFAULT_DIRECTIONS
from src.core.scheduler import get_scheduler, init_default_schedule
from src.core.query_engine import PaperQueryEngine, TrendAnalyzer
from src.pipeline.core import Pipeline, PipelineContext
from src.pipeline.stages import FetchStage, ParseStage, GenerateReportStage, UploadStage, NotifyStage
```

**Step 2: Update web/app.py**

```python
# Before
from database.connection import init_database, get_db_session
from database.repositories import PaperRepository
from core.query_engine import PaperQueryEngine, TrendAnalyzer, SearchCriteria
from core.scoring import ResearchDirection

# After
from src.database.connection import init_database, get_db_session
from src.database.repositories import PaperRepository
from src.core.query_engine import PaperQueryEngine, TrendAnalyzer, SearchCriteria
from src.core.scoring import ResearchDirection
```

**Step 3: Update src/tools/call_jina.py**

```python
# Before
from config.settings import get_settings
# After
from src.config.settings import get_settings
```

**Step 4: Update src/tools/call_llm.py**

```python
# Before
from config.settings import get_settings
from models.schemas import PaperAnalysis
# After
from src.config.settings import get_settings
from src.models.schemas import PaperAnalysis
```

**Step 5: Update src/tools/fetch_today.py**

```python
# Before
from database.connection import init_database, get_db_session
from database.repositories import PaperRepository
from database.models import PaperDB
from core.scoring import MultiDimensionScorer, DEFAULT_DIRECTIONS
# After
from src.database.connection import init_database, get_db_session
from src.database.repositories import PaperRepository
from src.database.models import PaperDB
from src.core.scoring import MultiDimensionScorer, DEFAULT_DIRECTIONS
```

**Step 6: Update src/core/query_engine.py**

```python
# Before
from database.connection import get_db_session
from database.models import PaperDB, DailyReportDB, UserFeedbackDB
from database.repositories import PaperRepository
from core.scoring import ResearchDirection
# After
from src.database.connection import get_db_session
from src.database.models import PaperDB, DailyReportDB, UserFeedbackDB
from src.database.repositories import PaperRepository
from src.core.scoring import ResearchDirection
```

**Step 7: Update src/pipeline/stages.py**

```python
# Before
from pipeline.core import PipelineStage, PipelineContext, Stage
from tools.call_jina import JinaReaderClient
from tools.call_llm import LLMClient
from database.connection import get_db_session
from database.repositories import PaperRepository
from models.schemas import ArxivPaper, PaperAnalysis
# After
from src.pipeline.core import PipelineStage, PipelineContext, Stage
from src.tools.call_jina import JinaReaderClient
from src.tools.call_llm import LLMClient
from src.database.connection import get_db_session
from src.database.repositories import PaperRepository
from src.models.schemas import ArxivPaper, PaperAnalysis
```

**Step 8: Check and update remaining files**

Check for any other cross-module imports in:
- `src/tools/rescore_papers.py`
- `src/tools/import_historical_data.py`
- `src/core/scheduler.py`
- `src/pipeline/core.py`

Run: `grep -r "^from config\|^from database\|^from core\|^from pipeline\|^from tools\|^from models\|^from utils" src/ main.py web/`

Expected: No matches (all should now use `src.` prefix)

---

## Task 5: Move Reports and Docs

**Step 1: Move database Markdown reports to output/**

```bash
mv database/*.md output/ 2>/dev/null || true
```

**Step 2: Move database/index.json to output/**

```bash
mv database/index.json output/ 2>/dev/null || true
```

**Step 3: Move web guide docs to docs/guides/**

```bash
mv web/COLOR_GUIDE.md docs/guides/color-guide.md
mv web/DARK_THEME_GUIDE.md docs/guides/dark-theme-guide.md
mv web/DEPLOYMENT_GUIDE.md docs/guides/deployment.md
```

**Step 4: Move root-level scattered fix/summary docs to docs/archive/**

```bash
mv ABSTRACT_FIX_SUMMARY.md docs/archive/
mv ABSTRACT_FORMAT_FIX.md docs/archive/
mv COLOR_FIX_REPORT.md docs/archive/
mv DARK_THEME_FIX.md docs/archive/
mv DIRECTION_FIX_FINAL.md docs/archive/
mv DIRECTION_FIX_REPORT.md docs/archive/
mv DIRECTION_FIX_SUMMARY.md docs/archive/
mv DIRECTION_FIX_V2.md docs/archive/
mv OPTIMIZATION_REPORT.md docs/archive/
mv FINAL_OPTIMIZATION_SUMMARY.md docs/archive/
```

**Step 5: Verify root is clean**

```bash
ls *.md
```
Expected: Only `README.md`, `QUICKSTART.md`, `CHANGELOG.md`

---

## Task 6: Create Missing Root Files

**Step 1: Create CHANGELOG.md**

```markdown
# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Changed
- Restructured project to standard open-source layout with `src/` package
- Moved all documentation into `docs/`
- Moved all scripts into `scripts/`
- Unified report output to `output/` directory
```

**Step 2: Create .env.example**

Copy `.env` and replace all secret values with placeholder strings like `YOUR_VALUE_HERE`.

**Step 3: Update .gitignore**

Ensure these entries exist:
```
database/arxiv_papers.db
output/
logs/
.venv/
__pycache__/
*.pyc
.env
```

---

## Task 7: Update README.md

**Step 1: Update project structure diagram in README**

The README currently shows the old directory structure. Update it to reflect the new `src/` layout and new script locations.

**Step 2: Update any commands in README**

If README references `arxiv_daily_v3.py`, change to `main.py`.
If README references `run.sh`, change path to `scripts/run.sh`.

---

## Task 8: Verify Everything Works

**Step 1: Test main.py imports**

```bash
cd /path/to/arXiv-ai-Agent
python -c "import main" 2>&1 | head -20
```
Expected: No ImportError

**Step 2: Test web/app.py imports**

```bash
python -c "import sys; sys.path.insert(0, '.'); exec(open('web/app.py').read().split('st.')[0])" 2>&1 | head -5
```

Or more simply:
```bash
python -c "
import sys
sys.path.insert(0, '.')
from src.database.connection import init_database
from src.core.scoring import ResearchDirection
print('OK')
"
```
Expected: `OK`

**Step 3: Check for any remaining bare imports**

```bash
grep -r "^from config\|^from database\|^from core\|^from pipeline\|^from tools\|^from models" . --include="*.py" --exclude-dir=.venv --exclude-dir=scripts/archive
```
Expected: No output

---

## Summary of File Operations

| Operation | Source | Destination |
|-----------|--------|-------------|
| Move | `config/` | `src/config/` |
| Move | `models/` | `src/models/` |
| Move | `core/` | `src/core/` |
| Move | `pipeline/` | `src/pipeline/` |
| Move | `tools/` | `src/tools/` |
| Move | `utils/` | `src/utils/` |
| Move | `database/*.py` | `src/database/` |
| Rename | `arxiv_daily_v3.py` | `main.py` |
| Delete | `arxiv_daily.py` | — |
| Move | `run.sh` | `scripts/run.sh` |
| Move | `test_direction_page.py` | `scripts/dev/` |
| Move | `database/*.md` | `output/` |
| Move | `web/*_GUIDE.md` | `docs/guides/` |
| Move | Root `*_FIX*.md`, `*_SUMMARY*.md`, `*_REPORT*.md` | `docs/archive/` |
| Create | `src/__init__.py` | — |
| Create | `CHANGELOG.md` | — |
| Create | `.env.example` | — |
