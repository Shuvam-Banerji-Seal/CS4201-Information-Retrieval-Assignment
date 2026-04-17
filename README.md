# CS4201 Information Retrieval Assignment

Author: Shuvam Banerji Seal  
Roll: 22MS076

This repository contains my complete CS4201 assignment workflow for large-scale XML cleaning, indexing, retrieval, evaluation, and submission packaging.

At the beginning, the dataset was treated as a provided course corpus with two English news collections. During evaluation setup, after topics and qrel discovery from the official task page, it was mapped to the FIRE 2012 English Adhoc track.

> [!WARNING]
> If you read this repo to do your assignment and do not give it a star, this poor dev gets sad 😢
> Help this poor dev and drop a star please ⭐🙏

## 0. Clone, Git LFS, and Reproduce from GitHub

This section is for direct evaluation from the GitHub repository.

### 0.1 Clone repository

```bash
git clone git@github.com:Shuvam-Banerji-Seal/CS4201-Information-Retrieval-Assignment.git
cd CS4201-Information-Retrieval-Assignment
```

### 0.2 Pull large files with Git LFS (JSONL files)

The combined JSONL files are tracked using Git LFS.

```bash
git lfs install
git lfs pull
git lfs ls-files
```

Expected LFS-tracked data files:

- `outputs/jsonl/combined_en_BDNews24.jsonl`
- `outputs/jsonl/combined_en_TheTelegraph_2001_2010.jsonl`

These two files are the cleaned/combined corpus artifacts used by the indexer.

### 0.3 Set up Python environment and dependencies

```bash
uv venv .venv --python 3.13
source .venv/bin/activate
uv pip install pandas lxml
```

### 0.4 Run the assignment pipeline

Indexing (BM25 baseline configuration):

```bash
python scripts/indexer.py \
  --source-format jsonl \
  --index-dir outputs/indexes/pylucene_en_docs \
  --open-mode create \
  --model bm25 \
  --k1 1.5 \
  --b 0.4
```

Retrieval (50 topics, top-100 per topic):

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

Optional evaluation against qrels (extra analysis beyond strict assignment requirement):

```bash
python scripts/evaluate_run.py \
  --run-file outputs/runs/final_bm25_k1_1.5_b_0.4_Shuvam_Banerji_Seal_22MS076.tsv \
  --qrel-file data/fire2012/adhoc/qrels/en.qrels.176-225.2012-v1.txt
```

### 0.5 What was done with qrels

- qrels v1 and v2 were downloaded and validated against the 50-topic set (`176..225`).
- qrels were used for evaluation (MAP, P@10, P@100, Recall@100) and BM25 sweep comparison.
- qrels were **not** used to generate the `RANK` column; rank is retrieval order from BM25 search results.

## 1. Assignment Deliverables

Required deliverables for submission:

1. Indexing code (PyLucene).
2. Retrieval code (configurable model/parameters; baseline BM25 with `k1=1.5`, `b=0.4`).
3. Final 6-column TSV run file:
	- `QID Q0 DOCID RANK SCORE RUNNAME`
4. Documentation of methodology and evaluation.

## 2. Repository Structure

- `scripts/indexer.py`: Indexer supporting JSONL and XML input modes.
- `scripts/retriever.py`: Retrieval pipeline with configurable model and analyzer.
- `scripts/evaluate_run.py`: Run-vs-qrel evaluator (MAP, P@10, P@100, Recall@100).
- `scripts/bm25_sweep.py`: Quick sweep for BM25 `k1,b` tuning.
- `notebooks/initial_analysis.ipynb`: XML analysis and repair notebook.
- `data/fire2012/adhoc/topics/`: Topics file.
- `data/fire2012/adhoc/qrels/`: qrels v1 and v2.
- `outputs/runs/`: run files (including final submission TSV).
- `outputs/analysis/`: analysis/sweep outputs.
- `reports/`: correction/analysis report artifacts.

## 3. Environment Setup with `uv`

## 3.1 Create virtual environment

```bash
uv venv .venv --python 3.13
source .venv/bin/activate
```

## 3.2 Install Python dependencies

```bash
uv pip install pandas lxml
```

`pandas` is used for analysis summaries and table processing. `lxml` is used for tolerant parser-based XML recovery in advanced repair steps.

## 3.3 PyLucene installation summary (Arch Linux path used in this project)

This repository uses a source-build installation workflow aligned with:
- PyLucene 10.0.0
- OpenJDK 21
- JCC source build

### Prerequisites

```bash
sudo pacman -S jdk21-openjdk ant make python
```

### JCC + PyLucene build outline

1. Set Java environment:
	- `JCC_JDK=/usr/lib/jvm/java-21-openjdk`
	- `JAVA_HOME=/usr/lib/jvm/java-21-openjdk`
2. In `jcc/setup.py`, update Linux library paths for modern OpenJDK layout:
	- use `lib` and `lib/server` paths.
3. Build/install JCC with the target Python environment.
4. Build/install PyLucene with configured `PYTHON`, `JCC`, `PREFIX_PYTHON`.
5. Verify with a simple in-memory index creation script.

Note: warnings about Java Vector API and foreign linker are non-blocking for this assignment.

## 4. Dataset Extraction

When starting from archives:

```bash
tar -xvf en.docs.2011.tar
tar -xzf en_BDNews24.tgz
tar -xzf en_TheTelegraph_2001-2010.tgz
```

Optional cleanup:

```bash
rm -f en_BDNews24.tgz en_TheTelegraph_2001-2010.tgz
```

## 5. XML Analysis and Repair Methodology

Primary workflow is documented in `notebooks/initial_analysis.ipynb`.

### 5.1 Scale and baseline quality

From the analysis pipeline:

- Total BDNews24 files scanned: `89,286`
- Valid before repair: `86,357`
- Invalid before repair: `2,929`
- Baseline validity: `96.72%`

So the malformed set is 2700+ files, requiring automated repair before robust indexing.

### 5.2 How invalid files were detected

For each file:

1. Parse with `xml.etree.ElementTree`.
2. If parse fails, capture parser exception and location details.
3. Run supplementary manual checks (bad tokens, malformed attributes, unbalanced tags, unescaped characters).
4. Record diagnostics in CSV and summary reports.

Main outputs:

- `outputs/analysis/invalid_files_details.csv`
- `reports/xml_analysis_report.txt`

### 5.3 Root-cause buckets identified

Notebook diagnostics (plus sampled error inspection) showed dominant patterns:

1. Invalid tokens / unescaped characters in text nodes.
2. Tag structure corruption (open/close mismatch in a subset).
3. Quoting and malformed attribute fragments.
4. A small fraction of severe corruption requiring structural rebuild.

### 5.4 Three-tier repair strategy

Implemented in notebook and then executed in batch:

1. Tier 1 (basic sanitization and escape fixes): highest-coverage pass.
2. Tier 2 (`lxml` HTML-tolerant recovery): handles parser-hostile malformed fragments.
3. Tier 3 (regex extraction + DOC reconstruction): fallback for heavily broken content.

Batch outcome:

- Invalid attempted: `2,929`
- Successfully repaired: `2,928`
- Remaining failed in automated pass: `1`

### 5.5 The one difficult file and final fix

Problem file:

- `en.2.298.332.2010.1.26`

Cause:

- XML-forbidden control byte (`0x03`) in content (invalid for XML 1.0 parsing).

Fix:

1. Detect control-range invalid characters.
2. Remove XML-disallowed control bytes.
3. Re-validate parse success.

This resolved the unsupported-character failure and closed the single-file gap.

## 6. Indexing

Baseline assignment indexing command:

```bash
python scripts/indexer.py \
  --source-format jsonl \
  --index-dir outputs/indexes/pylucene_en_docs \
  --open-mode create \
  --model bm25 \
  --k1 1.5 \
  --b 0.4
```

Alternative XML mode is available:

```bash
python scripts/indexer.py --source-format xml
```

## 7. Topics, Qrels, and Discovery Trail

Topics file:

- `data/fire2012/adhoc/topics/en.topics.176-225.2012.txt`

Qrels used:

- `data/fire2012/adhoc/qrels/en.qrels.176-225.2012-v1.txt`
- `data/fire2012/adhoc/qrels/en.qrels.176-225.2012-v2.txt`

### 7.1 How the exact qrels were found

1. Opened: `https://www.isical.ac.in/~fire/data.html`
2. Navigated to 2012 adhoc section.
3. Extracted English qrel links from the row corresponding to the 176-225 topic set.
4. Downloaded both versions and validated exact QID alignment with topics (`176..225`, 50 queries).

### 7.2 Meaning of v1 vs v2

- `v1`: initial released relevance-judgment set.
- `v2`: revised/updated relevance-judgment set for the same topics.

Reporting both gives a stable comparison across judgment versions.

## 8. Retrieval (Baseline Assignment Run)

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

Final run file:

- `outputs/runs/final_bm25_k1_1.5_b_0.4_Shuvam_Banerji_Seal_22MS076.tsv`

Format validation:

- Rows: `5000`
- Columns per row: `6`

## 9. Final Evaluation Metrics

Against qrels v1:

- MAP: `0.290033`
- P@10: `0.540000`
- P@100: `0.289400`
- Recall@100: `0.519894`

Against qrels v2:

- MAP: `0.288826`
- P@10: `0.546000`
- P@100: `0.291000`
- Recall@100: `0.517349`

## 10. BM25 Optimization and Findings

Quick sweep tool:

- `scripts/bm25_sweep.py`

Sweep result table:

- `outputs/analysis/bm25_sweep_results.csv`

Best quick-grid pair found:

- v1 best: `k1=0.8`, `b=0.4`, MAP `0.306830`
- v2 best: `k1=0.8`, `b=0.4`, MAP `0.305550`

Interpretation:

- This dataset favors lower TF saturation (`k1`) with moderate document-length normalization (`b`).
- Assignment-required baseline settings (`1.5`, `0.4`) are preserved in final submission run for compliance.

## 11. Git and LFS Policy

- Git repository initialized.
- Git LFS enabled for:
  - `outputs/jsonl/*.jsonl`
- `.gitignore` excludes raw corpora and archive-heavy artifacts.
- qrels are intentionally tracked for reproducible evaluation.

## 12. Submission Bundle

1. Code:
	- `scripts/indexer.py`
	- `scripts/retriever.py`
2. Final run:
	- `outputs/runs/final_bm25_k1_1.5_b_0.4_Shuvam_Banerji_Seal_22MS076.tsv`
3. Supporting docs:
	- `CS4201-Information-Retrieval-Assignment.md`
	- `docs/SUBMISSION_CHECKLIST.md`

---

## 13. Java Lucene Implementation

The Java Lucene approach for this assignment was originally introduced and demonstrated by **Dr. Dwaipayan Roy** (Course Instructor, CS4201) as guidance for the implementation. This is a fresh, independently written implementation by **Shuvam Banerji Seal (22MS076)**, submitted in accordance with the course rules regarding LLM-assisted work.

The implementation uses **Apache Lucene 9.12.0 (Java)** and is provided under `java_lucene_implementation/`. It mirrors the Python/PyLucene implementation — same BM25 parameters, same analyzer, same output format.

### Project Structure

```
java_lucene_implementation/
├── pom.xml                          # Maven build: Lucene 9.12.0 + Gson 2.11.0
├── run.sh                           # Convenience build+run script
└── src/main/java/cs4201/
    ├── Indexer.java                 # Reads JSONL → builds Lucene index
    └── Retriever.java               # BM25 search over FIRE topics → TSV
```

> **Note:** The `target/` directory (compiled classes, fat JAR) is generated by Maven and is not committed to the repository. See the build instructions below.

### Configuration

| Parameter | Value |
|-----------|-------|
| Similarity | BM25 (k1=1.5, b=0.4) |
| Analyzer | EnglishAnalyzer (Porter stemming + stopwords) |
| Query mode | Title-only |
| Default operator | OR |
| Top-K | 100 |
| Output | 6-col TSV: `QID Q0 DOCID RANK SCORE RUNNAME` |

### Prerequisites

- **Java 17+** (OpenJDK or equivalent)
- **Maven 3.6+**

On Arch Linux: `sudo pacman -S jdk17-openjdk maven`  
On Ubuntu/Debian: `sudo apt install openjdk-17-jdk maven`

Maven will **automatically download all required Lucene JARs** (~7 MB) from Maven Central on the first `mvn package` run. No manual JAR management is needed.

### Build & Run

```bash
cd java_lucene_implementation/

# Build fat JAR (downloads Lucene + Gson from Maven Central on first run)
mvn package -q

# The working JAR is:
#   target/java-lucene-ir-1.0-SNAPSHOT.jar   (produced by maven-shade-plugin)
# Do NOT use:
#   target/java-lucene-ir-1.0-SNAPSHOT-jar-with-dependencies.jar  (broken SPI)

# Step 1 — Index (reads both JSONL files, writes Lucene index)
java -Xmx4g -cp target/java-lucene-ir-1.0-SNAPSHOT.jar cs4201.Indexer

# Step 2 — Retrieve (runs 50 FIRE topics, writes TSV run file)
java -Xmx2g -cp target/java-lucene-ir-1.0-SNAPSHOT.jar cs4201.Retriever

# Or use the convenience script (build + index + retrieve + compare)
chmod +x run.sh
./run.sh all
```

### Why maven-shade-plugin (not maven-assembly-plugin)?

Apache Lucene uses Java SPI (`META-INF/services/` files) for codec discovery. The assembly plugin **overwrites** service files when bundling JARs, which causes the runtime error `"Lucene912 PostingsFormat does not exist"`. The shade plugin with `ServicesResourceTransformer` **appends** service files correctly. The `pom.xml` is configured accordingly.

### Output

- Index: `outputs/indexes/java_lucene_en_docs/`
- Run file: `outputs/runs/java_bm25_k1_1.5_b_0.4_Shuvam_Banerji_Seal_22MS076.tsv`

### Document Field Schema

| Field | Type | Stored | Description |
|-------|------|--------|-------------|
| `docno` | StringField | Yes | Unique document ID |
| `collection` | StringField | Yes | Corpus name |
| `source_rel_path` | StringField | Yes | Relative path within corpus |
| `title` | TextField | Yes | Article headline |
| `content` | TextField | No | title + body (indexed only) |
