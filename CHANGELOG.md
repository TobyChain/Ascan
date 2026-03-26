# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Changed
- Restructured project to standard open-source layout with `src/` package
- Moved all Python source modules (`config/`, `models/`, `core/`, `pipeline/`, `tools/`, `database/`, `utils/`) into `src/`
- Renamed `arxiv_daily_v3.py` to `main.py` as the primary entry point
- Moved `run.sh` to `scripts/run.sh`
- Unified report output to `output/` directory
- Consolidated all documentation under `docs/`
- Archived development fix notes and summaries to `docs/archive/`
