# Submission Checklist - FIRE 2012 English Adhoc

Author: Shuvam Banerji Seal

Student: Shuvam Banerji Seal (22MS076)

## 1) Required code files

- `scripts/indexer.py`
- `scripts/retriever.py`

## 2) Final run file

- `outputs/runs/final_bm25_k1_1.5_b_0.4_Shuvam_Banerji_Seal_22MS076.tsv`

Validation snapshot:
- rows: 5000 (50 topics x 100 docs)
- columns per row: 6 (QID, Q0, DOCID, RANK, SCORE, RUNNAME)

Evaluation snapshot on final run:
- v1 (first official qrel release): MAP=0.290033, P@10=0.540000
- v2 (revised official qrel release): MAP=0.288826, P@10=0.546000

## 3) Topics and qrels used

Topics:
- `data/fire2012/adhoc/topics/en.topics.176-225.2012.txt`

Qrels:
- `data/fire2012/adhoc/qrels/en.qrels.176-225.2012-v1.txt`
- `data/fire2012/adhoc/qrels/en.qrels.176-225.2012-v2.txt`

Qrel discovery method:
- Checked FIRE data page: `https://www.isical.ac.in/~fire/data.html`
- Extracted 2012 ADHOC English qrel links from the English row.
- Verified qrels cover exactly QID range 176..225 (50 topics), matching the topics file.

## 4) BM25 optimization notes

Quick sweep script:
- `scripts/bm25_sweep.py`

Results file:
- `outputs/analysis/bm25_sweep_results.csv`

Best observed MAP in quick grid:
- v1 best: k1=0.8, b=0.4, MAP=0.306830
- v2 best: k1=0.8, b=0.4, MAP=0.305550

Project baseline submission run (as requested in assignment):
- BM25 with k1=1.5, b=0.4

## 5) Git / LFS setup

- Repository initialized with git
- Git LFS enabled and configured for JSONL files
- `.gitignore` excludes raw XML corpora and archive files
- Qrel files are intentionally tracked (not ignored)

## 6) Repro commands

Build index:

```bash
python scripts/indexer.py \
  --source-format jsonl \
  --index-dir outputs/indexes/pylucene_en_docs \
  --open-mode create \
  --model bm25 \
  --k1 1.5 \
  --b 0.4
```

Generate final run:

```bash
python scripts/retriever.py \
  --index-dir outputs/indexes/pylucene_en_docs \
  --topics-file data/fire2012/adhoc/topics/en.topics.176-225.2012.txt \
  --model bm25 \
  --k1 1.5 \
  --b 0.4 \
  --query-mode title \
  --top-k 100 \
  --run-name Shuvam_Banerji_Seal_22MS076 \
  --output-run outputs/runs/final_bm25_k1_1.5_b_0.4_Shuvam_Banerji_Seal_22MS076.tsv
```

Evaluate against qrels:

```bash
python scripts/evaluate_run.py --qrels data/fire2012/adhoc/qrels/en.qrels.176-225.2012-v1.txt --run outputs/runs/final_bm25_k1_1.5_b_0.4_Shuvam_Banerji_Seal_22MS076.tsv --cutoff 100
python scripts/evaluate_run.py --qrels data/fire2012/adhoc/qrels/en.qrels.176-225.2012-v2.txt --run outputs/runs/final_bm25_k1_1.5_b_0.4_Shuvam_Banerji_Seal_22MS076.tsv --cutoff 100
```
