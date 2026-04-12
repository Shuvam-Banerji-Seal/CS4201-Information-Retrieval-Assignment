# 🔍 PYLUCENE INFORMATION RETRIEVAL — MASTER SKILL FOR LLM AGENTS

> Repository Assignment Author: Shuvam Banerji Seal

> **Purpose**: This skill equips any LLM agent or agentic program with complete, production-grade knowledge to perform world-class Information Retrieval (IR) using PyLucene — the Python binding for Apache Lucene. Read every section before writing a single line of code.

---

## 📚 OFFICIAL DOCUMENTATION — ALWAYS CHECK THESE FIRST

| Resource | URL |
|---|---|
| Apache Lucene Core | https://lucene.apache.org/core/ |
| Lucene JavaDocs (latest) | https://lucene.apache.org/core/9_10_0/core/index.html |
| PyLucene Official Page | https://lucene.apache.org/pylucene/ |
| PyLucene JCC Build Docs | https://lucene.apache.org/pylucene/jcc/ |
| Lucene Analyzers Module | https://lucene.apache.org/core/9_10_0/analysis/common/index.html |
| Lucene QueryParser Docs | https://lucene.apache.org/core/9_10_0/queryparser/index.html |
| Lucene Similarities (Models) | https://lucene.apache.org/core/9_10_0/core/org/apache/lucene/search/similarities/package-summary.html |
| Lucene Index Writer Config | https://lucene.apache.org/core/9_10_0/core/org/apache/lucene/index/IndexWriterConfig.html |
| Lucene Query Syntax Guide | https://lucene.apache.org/core/9_10_0/queryparser/org/apache/lucene/queryparser/classic/package-summary.html |
| Lucene Highlight Module | https://lucene.apache.org/core/9_10_0/highlighter/index.html |
| BM25 Similarity JavaDoc | https://lucene.apache.org/core/9_10_0/core/org/apache/lucene/search/similarities/BM25Similarity.html |
| TF-IDF (Classic) JavaDoc | https://lucene.apache.org/core/9_10_0/core/org/apache/lucene/search/similarities/ClassicSimilarity.html |
| Lucene GitHub Repository | https://github.com/apache/lucene |
| PyLucene Mailing List Archive | https://lists.apache.org/list.html?pylucene-dev@lucene.apache.org |

> **AGENT RULE**: If you encounter an error, an unknown class, or an unfamiliar parameter — **go to the JavaDoc URL above first**. Do not guess. Lucene's API is stable and fully documented.

---

## ⚙️ ENVIRONMENT SETUP

### Installation

```bash
# PyLucene requires Java JDK 11+ and JCC
# Ubuntu/Debian
sudo apt-get install default-jdk python3-dev

# Install JCC first
pip install jcc

# Build PyLucene from source (recommended)
wget https://dlcdn.apache.org/lucene/pylucene/pylucene-9.10.0-src.tar.gz
tar xzf pylucene-9.10.0-src.tar.gz
cd pylucene-9.10.0

# Edit Makefile: set PREFIX_PYTHON, JCC, NUM_FILES
make
make install

# OR: use Docker with pre-built PyLucene
docker pull coady/pylucene
```

### Verify Installation

```python
import lucene
from org.apache.lucene.store import MMapDirectory
from org.apache.lucene.analysis.standard import StandardAnalyzer

lucene.initVM(vmargs=['-Djava.awt.headless=true'])
print("PyLucene version:", lucene.VERSION)
# Expected: PyLucene version: 9.10.0
```

> **CRITICAL**: `lucene.initVM()` MUST be called **once** at program startup, before any Lucene class is used. In multi-threaded programs, attach each thread with `lucene.getVMEnv().attachCurrentThread()`.

---

## 🏗️ ARCHITECTURE OVERVIEW

```
Raw Documents
     │
     ▼
[Analyzer Pipeline]
  ├─ Tokenizer        → splits text into tokens
  ├─ TokenFilters     → lowercase, stopwords, stemming, synonyms
  └─ CharFilters      → html strip, pattern replace
     │
     ▼
[IndexWriter + IndexWriterConfig]
  ├─ Similarity Model → BM25 / TF-IDF / LM / DFR / IB
  ├─ MergePolicy      → TieredMergePolicy (default)
  └─ RAMBufferSizeMB  → flush threshold
     │
     ▼
[Directory]  ←─────────────────────────────────────────────────┐
  ├─ FSDirectory / MMapDirectory (disk, production)            │
  └─ RAMDirectory (in-memory, testing only)                    │
     │                                                         │
     ▼                                                         │
[IndexReader]                                                  │
     │                                                         │
     ▼                                                         │
[IndexSearcher] ──── Similarity Model ──────────────────────────┘
     │
     ▼
[QueryParser / Query Builder]
  ├─ StandardQueryParser
  ├─ BooleanQuery
  ├─ PhraseQuery
  ├─ TermQuery
  ├─ FuzzyQuery
  ├─ WildcardQuery
  └─ SpanQuery
     │
     ▼
[TopDocs / ScoreDoc[]]
     │
     ▼
[Highlighter / Formatter]
     │
     ▼
Results + Context Snippets
```

---

## 📁 FILE AND DIRECTORY HANDLING

### Directory Types — Choose the Right One

```python
import lucene
from java.nio.file import Paths
from org.apache.lucene.store import (
    MMapDirectory,     # Best for production (uses OS memory mapping)
    FSDirectory,       # Generic disk-based directory
    ByteBuffersDirectory,  # RAM-only, replaces deprecated RAMDirectory
    NIOFSDirectory,    # NIO-based, good fallback for non-mmap systems
)

lucene.initVM()

# ── PRODUCTION: MMapDirectory ──────────────────────────────────
# Uses OS-level memory-mapped files. Fastest for large indexes.
# Lucene auto-selects MMapDirectory on Linux/macOS 64-bit.
index_path = "/var/data/my_index"
directory = MMapDirectory(Paths.get(index_path))

# ── IN-MEMORY (Testing / small corpora) ───────────────────────
# ByteBuffersDirectory replaces the old RAMDirectory (deprecated since 8.x)
from org.apache.lucene.store import ByteBuffersDirectory
directory = ByteBuffersDirectory()

# ── SAFE OPEN: check if index exists ──────────────────────────
from org.apache.lucene.index import DirectoryReader, IndexWriter
exists = DirectoryReader.indexExists(directory)
print("Index exists:", exists)

# ── LOCKING ───────────────────────────────────────────────────
# Lucene uses a write.lock file. Only ONE IndexWriter can open at a time.
# If a previous crash left a stale lock:
from org.apache.lucene.store import SimpleFSLockFactory
directory = MMapDirectory(Paths.get(index_path), SimpleFSLockFactory.INSTANCE)
# Then force-unlock ONLY if you are certain no writer is running:
# directory.obtainLock("write.lock").close()  # acquires then releases

# ── ALWAYS CLOSE DIRECTORIES ──────────────────────────────────
# Use try/finally or context patterns — Python GC is not reliable for Java objects.
try:
    # ... operations ...
    pass
finally:
    directory.close()
```

### File Format Reference

| File Extension | Purpose |
|---|---|
| `.si` | Segment info |
| `.fnm` | Field names |
| `.fdx` / `.fdt` | Stored field index / data |
| `.tim` / `.tip` | Term dictionary / index |
| `.doc` | Frequencies and skip data |
| `.pos` | Positions |
| `.pay` | Payloads and offsets |
| `segments_N` | Segment index (current commit) |
| `write.lock` | Write lock |

> Do **not** manually edit or delete these files. Use `IndexWriter.deleteAll()` or segment merge APIs.

---

## 🔬 ANALYZERS — COMPLETE REFERENCE

An Analyzer defines the full text processing pipeline. Choosing the wrong analyzer is the single most common IR mistake.

### Standard Analyzers

```python
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.analysis.core import (
    WhitespaceAnalyzer,   # splits on whitespace only, no lowercasing
    SimpleAnalyzer,        # splits on non-letters, lowercases
    StopAnalyzer,          # SimpleAnalyzer + stop word removal
    KeywordAnalyzer,       # entire string as single token (IDs, paths)
)
from org.apache.lucene.analysis.en import EnglishAnalyzer
from org.apache.lucene.analysis.miscellaneous import PerFieldAnalyzerWrapper

# ── StandardAnalyzer ──────────────────────────────────────────
# Pipeline: StandardTokenizer → LowerCaseFilter → StopFilter
# Best for: general English prose, web content
# Tokenizes: splits on whitespace and punctuation (Unicode-aware)
# Handles: URLs, emails, alphanumeric tokens
analyzer = StandardAnalyzer()

# With custom stop words:
from org.apache.lucene.analysis import CharArraySet
stop_words = CharArraySet(["the", "a", "an", "is"], True)  # True = ignore case
analyzer = StandardAnalyzer(stop_words)

# ── EnglishAnalyzer ───────────────────────────────────────────
# Pipeline: StandardTokenizer → EnglishPossessiveFilter → LowerCase
#           → StopFilter → PorterStemFilter
# Best for: English documents where morphological variants should match
# e.g., "running" → "run", "flies" → "fli" (Porter stem)
analyzer = EnglishAnalyzer()

# ── WhitespaceAnalyzer ────────────────────────────────────────
# Best for: code, log files, CSV tokens, already-preprocessed text
analyzer = WhitespaceAnalyzer()

# ── KeywordAnalyzer ───────────────────────────────────────────
# Best for: IDs, file paths, email addresses, exact-match fields
analyzer = KeywordAnalyzer()

# ── Per-Field Analyzer (RECOMMENDED for multi-field schemas) ──
# Different fields need different analyzers
field_analyzers = {
    "title":    EnglishAnalyzer(),       # stemmed English
    "body":     EnglishAnalyzer(),       # stemmed English
    "id":       KeywordAnalyzer(),        # exact match
    "tags":     WhitespaceAnalyzer(),     # split on space only
    "url":      KeywordAnalyzer(),        # treat full URL as token
}
default_analyzer = StandardAnalyzer()
analyzer = PerFieldAnalyzerWrapper(default_analyzer, field_analyzers)
```

### Custom Analyzer Pipeline

```python
from org.apache.lucene.analysis import Analyzer
from org.apache.lucene.analysis.core import LowerCaseFilter, StopFilter
from org.apache.lucene.analysis.standard import StandardTokenizer
from org.apache.lucene.analysis.en import PorterStemFilter
from org.apache.lucene.analysis.miscellaneous import ASCIIFoldingFilter
from org.apache.lucene.analysis import CharArraySet

class CustomEnglishAnalyzer(Analyzer):
    """
    Custom pipeline:
    StandardTokenizer → ASCIIFolding → LowerCase → StopFilter → PorterStem
    
    ASCIIFolding handles: café→cafe, naïve→naive, résumé→resume
    """
    def createComponents(self, fieldName):
        source = StandardTokenizer()
        result = ASCIIFoldingFilter(source)
        result = LowerCaseFilter(result)
        stop_words = StopFilter.makeStopSet(["the","a","an","in","on","at"])
        result = StopFilter(result, stop_words)
        result = PorterStemFilter(result)
        return self.TokenStreamComponents(source, result)

    def initReader(self, fieldName, reader):
        return reader  # no CharFilter needed here

# Inspect what tokens an analyzer produces — ALWAYS test your analyzer:
def inspect_analyzer(analyzer, field, text):
    from org.apache.lucene.analysis import TokenStream
    from org.apache.lucene.analysis.tokenattributes import CharTermAttribute

    stream = analyzer.tokenStream(field, text)
    attr = stream.addAttribute(CharTermAttribute.class_)
    stream.reset()
    tokens = []
    while stream.incrementToken():
        tokens.append(attr.toString())
    stream.end()
    stream.close()
    return tokens

# Example:
eng = EnglishAnalyzer()
print(inspect_analyzer(eng, "body", "The quick brown foxes are running"))
# Output: ['quick', 'brown', 'fox', 'run']
```

### Analyzer Selection Guide

| Scenario | Recommended Analyzer |
|---|---|
| General English text | `EnglishAnalyzer` |
| Multi-language content | `ICUTokenizer` + language-specific filters |
| Exact ID / SKU / URL matching | `KeywordAnalyzer` |
| Code / logs / structured text | `WhitespaceAnalyzer` |
| Case-insensitive exact match | `SimpleAnalyzer` |
| Accented languages (French, German) | `FrenchAnalyzer`, `GermanAnalyzer` |
| Auto-complete / prefix search | `EdgeNGramTokenFilter` |
| Phonetic search (sound-alike) | `BeiderMorseFilter` or `DoubleMetaphoneFilter` |
| HTML documents | `HTMLStripCharFilter` → `StandardTokenizer` |

---

## 📄 DOCUMENT SCHEMA AND FIELD TYPES

```python
from org.apache.lucene.document import (
    Document,
    Field,
    TextField,       # Analyzed, indexed, optionally stored
    StringField,     # NOT analyzed (exact), indexed, optionally stored
    StoredField,     # Stored only, NOT indexed
    IntPoint,        # Numeric range/exact queries (int)
    LongPoint,       # Numeric range/exact queries (long)
    FloatPoint,      # Numeric range/exact queries (float)
    DoublePoint,     # Numeric range/exact queries (double)
    NumericDocValuesField,   # Per-doc numeric values (sorting, faceting)
    SortedDocValuesField,    # Per-doc string values (sorting)
    BinaryDocValuesField,    # Per-doc binary values
    FieldType,
)
from org.apache.lucene.document import Field

# ── FIELD TYPE OPTIONS ────────────────────────────────────────
# Field.Store.YES  → store original text in index (retrievable)
# Field.Store.NO   → index only, cannot retrieve original
# TextField        → tokenized by analyzer
# StringField      → stored as-is, single token (no analysis)

def build_document(doc_id, title, body, url, pub_date_epoch, score_boost):
    """
    Build a richly typed Lucene Document.
    
    Args:
        doc_id:          str  — unique identifier
        title:           str  — document title
        body:            str  — main text content
        url:             str  — source URL
        pub_date_epoch:  int  — Unix timestamp (milliseconds)
        score_boost:     float — static relevance boost (stored as DocValue)
    """
    doc = Document()

    # Unique ID — exact match only, stored for retrieval
    doc.add(StringField("id", doc_id, Field.Store.YES))

    # Title — analyzed for search, stored for display
    doc.add(TextField("title", title, Field.Store.YES))

    # Body — analyzed for search, NOT stored (saves disk space)
    # Use StoredField("body", body) separately if you need to retrieve it
    doc.add(TextField("body", body, Field.Store.NO))

    # URL — exact, stored
    doc.add(StringField("url", url, Field.Store.YES))

    # Stored-only body for retrieval (separate from indexed field)
    doc.add(StoredField("body_stored", body))

    # Date as LongPoint for range queries: date:[20240101 TO 20241231]
    doc.add(LongPoint("pub_date", pub_date_epoch))
    # Also store as NumericDocValues for sorting
    doc.add(NumericDocValuesField("pub_date_dv", pub_date_epoch))
    # Store raw value for retrieval
    doc.add(StoredField("pub_date", pub_date_epoch))

    # Static boost stored as DocValues (used in custom scoring)
    from org.apache.lucene.document import FloatDocValuesField
    doc.add(FloatDocValuesField("quality_score", float(score_boost)))

    return doc


# ── CUSTOM FIELD TYPE (for positional/offset storage) ─────────
def make_full_field_type():
    """
    FieldType with positions + offsets stored.
    Required for Highlighter to work.
    """
    ft = FieldType()
    ft.setIndexOptions(
        # Options (in order of increasing storage cost):
        # DOCS                          — existence only
        # DOCS_AND_FREQS                — term frequency
        # DOCS_AND_FREQS_AND_POSITIONS  — positions (phrase queries)
        # DOCS_AND_FREQS_AND_POSITIONS_AND_OFFSETS — character offsets (highlighting)
        ft.IndexOptions.DOCS_AND_FREQS_AND_POSITIONS_AND_OFFSETS
    )
    ft.setStored(True)
    ft.setTokenized(True)
    ft.setStoreTermVectors(True)
    ft.setStoreTermVectorPositions(True)
    ft.setStoreTermVectorOffsets(True)
    ft.freeze()
    return ft

HIGHLIGHT_FIELD_TYPE = make_full_field_type()

# Usage:
# doc.add(Field("body", body_text, HIGHLIGHT_FIELD_TYPE))
```

---

## ✍️ INDEX WRITING — COMPLETE API

```python
import lucene
from java.nio.file import Paths
from org.apache.lucene.store import MMapDirectory
from org.apache.lucene.index import (
    IndexWriter,
    IndexWriterConfig,
    DirectoryReader,
    Term,
)
from org.apache.lucene.analysis.en import EnglishAnalyzer
from org.apache.lucene.search.similarities import BM25Similarity

lucene.initVM()

def create_index_writer(index_path, analyzer, similarity=None, ram_buffer_mb=256.0):
    """
    Create a production-grade IndexWriter.
    
    Parameters:
        index_path:    str   — filesystem path for the index
        analyzer:      Analyzer
        similarity:    Similarity object (default: BM25Similarity())
        ram_buffer_mb: float — RAM buffer before auto-flush (default 16MB, use 256MB+ for batch)
    
    Returns: (directory, writer) — MUST be closed in finally block
    """
    directory = MMapDirectory(Paths.get(index_path))
    config = IndexWriterConfig(analyzer)

    # OpenMode options:
    # CREATE             — always create fresh, deletes existing
    # APPEND             — open existing index, fail if none
    # CREATE_OR_APPEND   — create if absent, append if exists (RECOMMENDED)
    config.setOpenMode(IndexWriterConfig.OpenMode.CREATE_OR_APPEND)

    # Similarity / retrieval model
    if similarity is None:
        similarity = BM25Similarity()  # default since Lucene 8.0
    config.setSimilarity(similarity)

    # RAM buffer: larger = fewer segment flushes = faster batch indexing
    # Rule of thumb: set to 10-25% of available heap
    config.setRAMBufferSizeMB(ram_buffer_mb)

    # Max buffered docs (alternative flush trigger, -1 = disabled when RAM buffer active)
    config.setMaxBufferedDocs(IndexWriterConfig.DISABLE_AUTO_FLUSH)

    # Merge policy: TieredMergePolicy is default and recommended
    from org.apache.lucene.index import TieredMergePolicy
    merge_policy = TieredMergePolicy()
    merge_policy.setMaxMergeAtOnce(10)          # max segments merged at once
    merge_policy.setSegmentsPerTier(10)          # ideal segments per tier
    merge_policy.setMaxMergedSegmentMB(5 * 1024) # 5GB max merged segment
    config.setMergePolicy(merge_policy)

    writer = IndexWriter(directory, config)
    return directory, writer


def index_documents(writer, documents):
    """
    Bulk index a list of dicts.
    
    documents: list of {id, title, body, url, pub_date, quality_score}
    """
    for raw in documents:
        doc = build_document(
            doc_id=raw["id"],
            title=raw["title"],
            body=raw["body"],
            url=raw["url"],
            pub_date_epoch=raw["pub_date"],
            score_boost=raw.get("quality_score", 1.0),
        )
        # updateDocument: delete existing doc with same "id", then add new one
        # This achieves upsert semantics — preferred over add + manual delete
        writer.updateDocument(Term("id", raw["id"]), doc)

    # Commit makes changes visible to new readers
    writer.commit()
    print(f"Indexed {writer.getDocStats().numDocs} documents")


def delete_document(writer, doc_id):
    """Delete document by unique ID."""
    writer.deleteDocuments(Term("id", doc_id))
    writer.commit()


def optimize_index(writer):
    """
    Force merge to 1 segment (expensive! only for static indexes).
    Improves query speed significantly for read-heavy workloads.
    """
    writer.forceMerge(1)
    writer.commit()
    print("Index optimized to 1 segment")


# ── FULL INDEXING WORKFLOW ────────────────────────────────────
if __name__ == "__main__":
    analyzer = EnglishAnalyzer()
    directory, writer = create_index_writer(
        index_path="/var/data/my_index",
        analyzer=analyzer,
        similarity=BM25Similarity(k1=1.2, b=0.75),
        ram_buffer_mb=512.0,
    )
    try:
        documents = [
            {
                "id": "doc_001",
                "title": "Introduction to Information Retrieval",
                "body": "Information retrieval is the activity of obtaining resources...",
                "url": "https://example.com/ir-intro",
                "pub_date": 1704067200000,  # 2024-01-01 in ms
                "quality_score": 0.9,
            },
            # ... more documents
        ]
        index_documents(writer, documents)
    finally:
        writer.close()
        directory.close()
```

---

## 🧮 RETRIEVAL MODELS — MATHEMATICS AND PARAMETERS

### 1. BM25Similarity (DEFAULT — Use This Unless You Have a Reason Not To)

**Mathematical Formula:**

```
                          f(qi, D) · (k1 + 1)
BM25(D, Q) = Σ IDF(qi) · ─────────────────────────────────────────
              i            f(qi, D) + k1 · (1 − b + b · |D|/avgdl)

Where:
  IDF(qi) = log(1 + (N − n(qi) + 0.5) / (n(qi) + 0.5))
  f(qi, D)  = term frequency of qi in document D
  |D|       = length of D in words
  avgdl     = average document length across corpus
  N         = total number of documents
  n(qi)     = number of documents containing qi
  k1        = term frequency saturation parameter
  b         = length normalization parameter
```

**Parameter Tuning:**

| Parameter | Default | Range | Effect |
|---|---|---|---|
| `k1` | 1.2 | 0.0 – 3.0 | Controls TF saturation. Higher → TF matters more. `k1=0` → pure IDF. |
| `b` | 0.75 | 0.0 – 1.0 | Length normalization. `b=0` → no normalization. `b=1` → full normalization. |

```python
from org.apache.lucene.search.similarities import BM25Similarity

# Default (recommended starting point)
sim = BM25Similarity()                    # k1=1.2, b=0.75

# Short documents (tweets, titles): reduce b — length matters less
sim = BM25Similarity(1.2, 0.3)

# Long technical documents: increase b — penalize verbose docs more
sim = BM25Similarity(1.5, 0.9)

# High-repetition queries (keyword stuffing prevention): lower k1
sim = BM25Similarity(0.8, 0.75)

# Pure IDF scoring (keyword occurrence only):
sim = BM25Similarity(0.0, 0.0)

# Lucene's BM25 IDF (slightly different from classic Okapi BM25 IDF):
# IDF = log(1 + (docCount - docFreq + 0.5) / (docFreq + 0.5))
# Note: Lucene adds 1 inside the log to prevent negative IDF
```

**When to use BM25:**
- General-purpose text retrieval
- Web search
- Document ranking
- Default choice for any new IR system

---

### 2. ClassicSimilarity (TF-IDF — Lucene's Original Model)

**Mathematical Formula:**

```
                                     tf(t in d)  ·  idf(t)²  ·  t.getBoost()  ·  norm(t, d)
score(q, d) = coord(q,d) · queryNorm(q) · Σ ────────────────────────────────────────────────
                                           t∈q

Where:
  tf(t in d)   = sqrt(termFrequency)
  idf(t)       = 1 + log(numDocs / (docFreq + 1))
  coord(q,d)   = overlap / maxOverlap   (fraction of query terms found)
  queryNorm(q) = 1 / sqrt(Σ idf(t)²)   (normalizes scores across queries)
  norm(t, d)   = 1 / sqrt(numTerms)     (field length normalization)
```

```python
from org.apache.lucene.search.similarities import ClassicSimilarity

sim = ClassicSimilarity()

# When to use:
# - Legacy systems migrating from Lucene < 8.0
# - When you need coord() factor (rewards docs matching more query terms)
# - Academic baselines comparing against classic TF-IDF
# - Generally INFERIOR to BM25 for most tasks
```

---

### 3. LMDirichletSimilarity (Language Model with Dirichlet Smoothing)

**Mathematical Formula:**

```
                      c(w; d) + μ · P(w | C)
P(w | M_d) = ─────────────────────────────────
                         |d| + μ

           n
score = Σ  log P(qi | M_d)
          i=1

Where:
  c(w; d)    = count of word w in document d
  |d|        = document length
  μ (mu)     = Dirichlet smoothing parameter (prior strength)
  P(w | C)   = P(word | collection) = c(w,C) / |C| (collection language model)
```

**Parameter Tuning:**

| Parameter | Default | Tuning Guide |
|---|---|---|
| `mu` (μ) | 2000 | Short docs: 500–1000. Long docs: 2000–5000. Increases smoothing. |

```python
from org.apache.lucene.search.similarities import LMDirichletSimilarity

# Default mu=2000
sim = LMDirichletSimilarity()

# For short query/document pairs (titles, abstracts)
sim = LMDirichletSimilarity(500.0)

# For long documents (books, legal documents)
sim = LMDirichletSimilarity(5000.0)

# When to use:
# - Probabilistic IR tasks
# - Query likelihood model requirements
# - Often outperforms BM25 on TREC collections
# - Medical/legal document retrieval
```

---

### 4. LMJelinekMercerSimilarity (Language Model with JM Smoothing)

**Mathematical Formula:**

```
P(w | M_d) = (1 - λ) · P(w | d)  +  λ · P(w | C)

Where:
  λ (lambda) = interpolation weight between doc and collection model
  P(w | d)   = c(w; d) / |d|
  P(w | C)   = collection language model probability
```

| Parameter | Range | Effect |
|---|---|---|
| `lambda` (λ) | 0.0 – 1.0 | Higher → more smoothing toward collection. Typical: 0.1–0.5 |

```python
from org.apache.lucene.search.similarities import LMJelinekMercerSimilarity

# λ=0.1: trust document more (good for long queries)
sim = LMJelinekMercerSimilarity(0.1)

# λ=0.5: equal weighting
sim = LMJelinekMercerSimilarity(0.5)

# When to use:
# - Long verbose queries
# - When collection language model is well-estimated
```

---

### 5. DFRSimilarity (Divergence From Randomness)

**Mathematical Formula:**

```
score(d, q) = tf_norm · [ -log P1(tf; λ) + log(1 + P2(tf+1; λ)) ]

Where:
  P1 = probability model (e.g., Poisson, Binomial)
  P2 = after-effect model (e.g., Laplace, BetraBinomial)
  tf_norm = normalized term frequency by normalization model
```

```python
from org.apache.lucene.search.similarities import (
    DFRSimilarity,
    BasicModelIF,      # If model (inverse frequency)
    BasicModelIn,      # In model
    BasicModelIne,     # Ine model
    BasicModelG,       # Geometric model
    AfterEffectB,      # Bose-Einstein after-effect
    AfterEffectL,      # Laplace after-effect
    NormalizationH1,   # Normalization 1: tf * (avgdl/dl)
    NormalizationH2,   # Normalization 2: tf · log(1 + avgdl/dl)
    NormalizationH3,   # Normalization 3: tf / (tf + 1 + (dl/avgdl)^slope)
    NormalizationZ,    # Pareto-Zipf normalization
)

# Common configuration: IF.B.H1 (used in TREC experiments)
sim = DFRSimilarity(BasicModelIF(), AfterEffectB(), NormalizationH1())

# Alternative: In.L.H2
sim = DFRSimilarity(BasicModelIn(), AfterEffectL(), NormalizationH2())

# When to use:
# - Competitive IR research
# - When BM25 has been tuned and you need marginal gains
# - Heterogeneous document collections
```

---

### 6. IBSimilarity (Information-Based Models)

```python
from org.apache.lucene.search.similarities import (
    IBSimilarity,
    DistributionLL,   # Log-logistic distribution
    DistributionSPL,  # Smoothed power-law distribution
    LambdaDF,         # DF-based lambda
    LambdaTTF,        # TTF-based lambda
    NormalizationH1,
    NormalizationH2,
)

# Log-logistic with DF lambda and H1 normalization
sim = IBSimilarity(DistributionLL(), LambdaDF(), NormalizationH1())

# When to use: Research/academic IR, niche domain retrieval
```

---

### 7. MultiSimilarity (Combine Multiple Models)

```python
from org.apache.lucene.search.similarities import MultiSimilarity

# Combine BM25 and LMDirichlet (scores are summed)
sim = MultiSimilarity([
    BM25Similarity(1.2, 0.75),
    LMDirichletSimilarity(2000.0),
])

# When to use: Ensemble retrieval when single model underperforms
# Note: scores from different models are on different scales — normalize first
```

---

### 8. PerFieldSimilarityWrapper

```python
from org.apache.lucene.search.similarities import PerFieldSimilarityWrapper

class FieldSimilarity(PerFieldSimilarityWrapper):
    def __init__(self):
        super().__init__()
        self.default = BM25Similarity(1.2, 0.75)
        self.title_sim = BM25Similarity(1.5, 0.3)  # short fields, low b
        self.id_sim = BM25Similarity(0.0, 0.0)     # exact term match only

    def get(self, fieldName):
        if fieldName == "title":
            return self.title_sim
        elif fieldName == "id":
            return self.id_sim
        return self.default

# Use with IndexWriterConfig AND IndexSearcher:
sim = FieldSimilarity()
config.setSimilarity(sim)
searcher.setSimilarity(sim)
```

---

## 🔍 QUERY BUILDING — COMPLETE API

### Query Parser (Human-Readable Query Strings)

```python
from org.apache.lucene.queryparser.classic import QueryParser, MultiFieldQueryParser
from org.apache.lucene.queryparser.flexible.standard import StandardQueryParser
from org.apache.lucene.analysis.en import EnglishAnalyzer

analyzer = EnglishAnalyzer()

# ── Single-Field QueryParser ──────────────────────────────────
parser = QueryParser("body", analyzer)

# Parse simple query
query = parser.parse("information retrieval")

# Phrase query (exact phrase)
query = parser.parse('"information retrieval"')

# Boolean
query = parser.parse("python AND lucene NOT java")
query = parser.parse("python OR elasticsearch OR lucene")

# Wildcard (? = single char, * = zero or more)
# WARNING: leading wildcards disabled by default — very expensive
query = parser.parse("run*")          # running, runs, runner
query = parser.parse("colo?r")        # color, colour

# Fuzzy (edit distance)
query = parser.parse("retrival~")     # matches "retrieval" (edit distance 1)
query = parser.parse("retrival~2")    # edit distance ≤ 2

# Proximity (within N words)
query = parser.parse('"information retrieval"~5')  # within 5 words

# Boost specific terms
query = parser.parse("python^3 OR java")   # python weighted 3x

# Range queries
query = parser.parse("pub_date:[20240101 TO 20241231]")
query = parser.parse("pub_date:{20240101 TO 20241231}")  # exclusive

# ── Parser Configuration ──────────────────────────────────────
parser.setDefaultOperator(QueryParser.Operator.AND)   # AND by default
parser.setAllowLeadingWildcard(True)                   # enable *term (expensive!)
parser.setFuzzyMinSim(0.7)                             # fuzzy threshold
parser.setFuzzyPrefixLength(2)                         # fuzzy prefix chars
parser.setPhraseSlop(2)                                # default phrase slop

# ── Multi-Field QueryParser ───────────────────────────────────
# Search across multiple fields simultaneously
fields = ["title", "body", "tags"]
boosts = {"title": 2.0, "body": 1.0, "tags": 1.5}  # field boosts

# Using HashMap for boosts
from java.util import HashMap
boost_map = HashMap()
boost_map.put("title", 2.0)
boost_map.put("body", 1.0)
boost_map.put("tags", 1.5)

multi_parser = MultiFieldQueryParser(fields, analyzer, boost_map)
query = multi_parser.parse("neural network training")

# ── StandardQueryParser (flexible, newer API) ─────────────────
std_parser = StandardQueryParser(analyzer)
std_parser.setDefaultOperator(
    std_parser.ConfigurationKeys.DEFAULT_OPERATOR
)
query = std_parser.parse("machine learning", "body")
```

### Programmatic Query Building

```python
from org.apache.lucene.search import (
    BooleanQuery,
    BooleanClause,
    TermQuery,
    PhraseQuery,
    FuzzyQuery,
    WildcardQuery,
    PrefixQuery,
    RangeQuery,
    BoostQuery,
    MatchAllDocsQuery,
    MatchNoDocsQuery,
    ConstantScoreQuery,
)
from org.apache.lucene.index import Term
from org.apache.lucene.document import IntPoint, LongPoint, FloatPoint

# ── TermQuery — exact token match ─────────────────────────────
q = TermQuery(Term("body", "python"))

# ── PhraseQuery — exact ordered phrase ────────────────────────
pq = PhraseQuery.Builder()
pq.add(Term("body", "information"))
pq.add(Term("body", "retrieval"))
pq.setSlop(0)   # 0 = exact phrase, N = allow N word gaps
query = pq.build()

# Slop example: "retrieval information"~2 would match "information retrieval"
pq2 = PhraseQuery.Builder()
pq2.add(Term("body", "retrieval"))
pq2.add(Term("body", "information"))
pq2.setSlop(2)

# ── BooleanQuery — combine queries ────────────────────────────
# Occur options:
#   MUST     → term must appear (AND)
#   SHOULD   → term should appear (OR, boosts score)
#   MUST_NOT → term must NOT appear (NOT, does not affect score)
#   FILTER   → must appear, does NOT affect score (pure filter)

bq = BooleanQuery.Builder()
bq.add(TermQuery(Term("body", "python")),    BooleanClause.Occur.MUST)
bq.add(TermQuery(Term("body", "lucene")),    BooleanClause.Occur.SHOULD)
bq.add(TermQuery(Term("body", "java")),      BooleanClause.Occur.MUST_NOT)
query = bq.build()

# Minimum should match: at least 2 SHOULD clauses must match
bq_builder = BooleanQuery.Builder()
bq_builder.setMinimumNumberShouldMatch(2)
bq_builder.add(TermQuery(Term("tags", "ml")),         BooleanClause.Occur.SHOULD)
bq_builder.add(TermQuery(Term("tags", "nlp")),        BooleanClause.Occur.SHOULD)
bq_builder.add(TermQuery(Term("tags", "python")),     BooleanClause.Occur.SHOULD)

# ── FuzzyQuery — edit distance matching ───────────────────────
# maxEdits: 0, 1, or 2 (Damerau-Levenshtein distance)
fq = FuzzyQuery(Term("body", "retrival"), 2)   # edit distance ≤ 2
fq = FuzzyQuery(Term("body", "retrival"), 1, 3)  # ed≤1, prefix of 3 chars must match

# ── WildcardQuery ─────────────────────────────────────────────
wq = WildcardQuery(Term("body", "run*"))    # running, runs, runner
wq = WildcardQuery(Term("body", "colo?r")) # color, colour

# ── PrefixQuery — starts with ─────────────────────────────────
pq = PrefixQuery(Term("body", "comput"))  # computer, computing, computed

# ── Numeric Range Queries ─────────────────────────────────────
# For IntPoint, LongPoint, FloatPoint, DoublePoint fields:
# Inclusive range
date_range = LongPoint.newRangeQuery("pub_date", 1704067200000, 1735689600000)

# Exact value
exact_date = LongPoint.newExactQuery("pub_date", 1704067200000)

# Set of values
date_set = LongPoint.newSetQuery("pub_date", [1704067200000, 1706745600000])

# ── BoostQuery — weight a query ───────────────────────────────
boosted = BoostQuery(TermQuery(Term("title", "python")), 3.0)

# ── ConstantScoreQuery — filter without scoring ───────────────
# Use when you want a filter that doesn't affect relevance score
filter_q = ConstantScoreQuery(TermQuery(Term("status", "published")))

# ── Combined Filter + Relevance Query ────────────────────────
main_query = MultiFieldQueryParser(["title", "body"], analyzer).parse("machine learning")
filter_query = ConstantScoreQuery(TermQuery(Term("category", "tech")))

final = BooleanQuery.Builder()
final.add(main_query, BooleanClause.Occur.MUST)
final.add(filter_query, BooleanClause.Occur.FILTER)
query = final.build()

# ── MatchAllDocsQuery — retrieve everything ───────────────────
all_q = MatchAllDocsQuery()
```

---

## 🔎 SEARCHING — COMPLETE API

```python
from org.apache.lucene.index import DirectoryReader
from org.apache.lucene.search import (
    IndexSearcher,
    Sort,
    SortField,
    SortedNumericSortField,
    TopDocs,
    ScoreDoc,
)
from org.apache.lucene.search.similarities import BM25Similarity


def create_searcher(directory, similarity=None):
    """
    Create an IndexSearcher from an existing index directory.
    
    IMPORTANT: DirectoryReader is the bottleneck.
    - Reuse readers! Opening a new reader is expensive.
    - Use DirectoryReader.openIfChanged() for near-real-time search.
    """
    reader = DirectoryReader.open(directory)
    searcher = IndexSearcher(reader)
    if similarity:
        searcher.setSimilarity(similarity)
    return reader, searcher


def basic_search(searcher, query, top_n=10):
    """
    Basic search returning TopDocs.
    
    Returns: list of (score, doc_id, stored_fields_dict)
    """
    top_docs = searcher.search(query, top_n)
    results = []
    for score_doc in top_docs.scoreDocs:
        doc = searcher.doc(score_doc.doc)          # retrieve stored fields
        fields = {
            "score":   score_doc.score,
            "doc_id":  score_doc.doc,              # internal Lucene doc ID
            "id":      doc.get("id"),              # stored StringField
            "title":   doc.get("title"),
            "url":     doc.get("url"),
        }
        results.append(fields)
    return results, top_docs.totalHits.value


def paginated_search(searcher, query, page=0, page_size=10):
    """
    Paginate results using searchAfter().
    
    NOTE: Do NOT use from=(page * page_size) — that's O(n) and wastes CPU.
    Use searchAfter() for efficient deep pagination.
    """
    if page == 0:
        top_docs = searcher.search(query, page_size)
        after = None
    else:
        # Fetch first page to get "after" ScoreDoc
        # In production: cache the last ScoreDoc of each page
        first = searcher.search(query, page * page_size)
        if len(first.scoreDocs) == 0:
            return [], 0
        after = first.scoreDocs[-1]
        top_docs = searcher.searchAfter(after, query, page_size)

    results = []
    for sd in top_docs.scoreDocs:
        doc = searcher.doc(sd.doc)
        results.append({"score": sd.score, "id": doc.get("id"), "title": doc.get("title")})
    return results, top_docs.totalHits.value


def sorted_search(searcher, query, sort_field="pub_date_dv", top_n=10):
    """
    Sort results by a DocValues field instead of (or in addition to) score.
    """
    # Sort by date descending, then by score descending
    sort = Sort(
        SortField(sort_field, SortField.Type.LONG, True),  # True = reverse (descending)
        SortField.FIELD_SCORE,                              # secondary: relevance
    )
    top_docs = searcher.search(query, top_n, sort, True)   # True = trackMaxScore
    results = []
    for sd in top_docs.scoreDocs:
        doc = searcher.doc(sd.doc)
        results.append({"score": sd.score, "id": doc.get("id")})
    return results


def explain_score(searcher, query, doc_id):
    """
    Debug scoring for a specific document.
    ALWAYS use this when scores seem wrong.
    """
    explanation = searcher.explain(query, doc_id)
    print(explanation.toString())
    # Example output:
    # 1.234 = weight(body:python in 42) [BM25Similarity], result of:
    #   1.234 = score(freq=3.0), computed from:
    #     1.567 = idf, computed from:
    #       docFreq=125, docCount=5000
    #     0.789 = tf, computed from:
    #       freq=3.0 = termFreq=3.0
    #       k1=1.2, b=0.75, avgdl=150.0, dl=98.0
    return explanation


def near_real_time_search(directory, writer):
    """
    NRT search: see changes immediately after writer.commit() (or even without commit).
    """
    # DirectoryReader.open(writer) opens a near-real-time reader
    nrt_reader = DirectoryReader.open(writer)
    nrt_searcher = IndexSearcher(nrt_reader)

    # After updates, check if reader needs refresh:
    new_reader = DirectoryReader.openIfChanged(nrt_reader)
    if new_reader is not None:
        nrt_reader.close()
        nrt_reader = new_reader
        nrt_searcher = IndexSearcher(nrt_reader)

    return nrt_reader, nrt_searcher
```

---

## 🎯 HIGHLIGHTING — EXTRACT CONTEXT SNIPPETS

```python
from org.apache.lucene.search.highlight import (
    Highlighter,
    QueryScorer,
    SimpleHTMLFormatter,
    SimpleSpanFragmenter,
    TextFragment,
)
from org.apache.lucene.search.highlight import SimpleFragmenter


def highlight_results(searcher, analyzer, query, doc_text, field="body"):
    """
    Highlight matching terms in result snippets.
    
    Requires: Field indexed with DOCS_AND_FREQS_AND_POSITIONS_AND_OFFSETS
    OR: using term vectors (setStoreTermVectors=True)
    
    Returns: HTML string with <B> tags around matches, or None
    """
    # Rewrite query for multi-term queries (fuzzy, wildcard)
    reader = searcher.getIndexReader()
    rewritten_query = query.rewrite(reader)

    scorer = QueryScorer(rewritten_query, field)

    # Formatter: wraps matches in HTML tags
    formatter = SimpleHTMLFormatter(
        "<mark>",   # pre-tag  (default: <B>)
        "</mark>",  # post-tag (default: </B>)
    )

    highlighter = Highlighter(formatter, scorer)

    # Fragmenter: how to split text into snippets
    # SimpleFragmenter: fixed-size character fragments
    highlighter.setTextFragmenter(SimpleFragmenter(150))  # 150 chars per fragment

    # SimpleSpanFragmenter: smarter, uses term positions
    # highlighter.setTextFragmenter(SimpleSpanFragmenter(scorer, 150))

    # Maximum number of fragments to return
    max_fragments = 3

    token_stream = analyzer.tokenStream(field, doc_text)
    fragments = highlighter.getBestFragments(token_stream, doc_text, max_fragments, "...")
    return fragments   # "...python is a <mark>language</mark> for <mark>information</mark>..."


def highlight_with_fast_vector_highlighter(searcher, query, doc_id, field="body"):
    """
    FastVectorHighlighter: uses term vectors for speed.
    Requires: setStoreTermVectors=True, setStoreTermVectorPositions=True,
              setStoreTermVectorOffsets=True on the field.
    """
    from org.apache.lucene.search.highlight import FastVectorHighlighter, FieldQuery

    fvh = FastVectorHighlighter()
    field_query = fvh.getFieldQuery(query, searcher.getIndexReader())
    result = fvh.getBestFragment(
        field_query,
        searcher.getIndexReader(),
        doc_id,
        field,
        150,  # fragment size chars
    )
    return result
```

---

## 🧠 CONTEXT BUILDING FOR LLM RAG PIPELINES

```python
def build_rag_context(searcher, analyzer, query_text, top_n=5, max_chars_per_doc=800):
    """
    Full RAG context builder:
    1. Parse query
    2. Retrieve top-N documents
    3. Highlight relevant passages
    4. Format context string for LLM prompt
    
    Returns: (context_string, sources_list)
    """
    # Parse the natural language query
    from org.apache.lucene.queryparser.classic import MultiFieldQueryParser
    from java.util import HashMap
    
    boosts = HashMap()
    boosts.put("title", 2.0)
    boosts.put("body", 1.0)

    parser = MultiFieldQueryParser(["title", "body"], analyzer, boosts)
    parser.setDefaultOperator(MultiFieldQueryParser.Operator.AND)

    try:
        query = parser.parse(query_text)
    except Exception:
        # Fallback: escape special chars and retry
        from org.apache.lucene.queryparser.classic import QueryParser
        escaped = QueryParser.escape(query_text)
        query = MultiFieldQueryParser(["title", "body"], analyzer, boosts).parse(escaped)

    # Search
    top_docs = searcher.search(query, top_n)

    context_parts = []
    sources = []

    for rank, score_doc in enumerate(top_docs.scoreDocs, 1):
        doc = searcher.doc(score_doc.doc)
        title = doc.get("title") or "Untitled"
        url = doc.get("url") or ""
        body = doc.get("body_stored") or ""

        # Highlight
        snippet = highlight_results(searcher, analyzer, query, body)
        if not snippet:
            # Fallback: first N characters
            snippet = body[:max_chars_per_doc]

        context_parts.append(
            f"[{rank}] {title}\n"
            f"Source: {url}\n"
            f"Relevance Score: {score_doc.score:.4f}\n"
            f"Excerpt: {snippet}\n"
        )
        sources.append({"rank": rank, "title": title, "url": url, "score": score_doc.score})

    context_string = "\n---\n".join(context_parts)
    return context_string, sources


def build_prompt_with_context(question, context_string):
    """
    Standard RAG prompt template.
    """
    return f"""You are a helpful assistant. Answer the question using ONLY the provided context.
If the context does not contain the answer, say "I don't have enough information."

CONTEXT:
{context_string}

QUESTION: {question}

ANSWER:"""
```

---

## 📊 FACETING AND AGGREGATION

```python
from org.apache.lucene.facet import FacetsConfig, FacetField, Facets, FacetResult
from org.apache.lucene.facet.taxonomy import FastTaxonomyFacetCounts
from org.apache.lucene.facet.taxonomy.directory import DirectoryTaxonomyWriter, DirectoryTaxonomyReader
from org.apache.lucene.facet.sortedset import SortedSetDocValuesFacetCounts, SortedSetDocValuesFacetField


def index_with_facets(index_dir, taxonomy_dir, documents):
    """
    Index documents with facet support (category drilldown).
    Requires a separate taxonomy directory.
    """
    from org.apache.lucene.store import MMapDirectory
    from java.nio.file import Paths

    index_path = MMapDirectory(Paths.get(index_dir))
    taxo_path = MMapDirectory(Paths.get(taxonomy_dir))

    config = FacetsConfig()
    config.setHierarchical("category", True)    # hierarchical facets
    config.setMultiValued("tags", True)          # allow multiple values per doc

    analyzer = EnglishAnalyzer()
    iw_config = IndexWriterConfig(analyzer)
    iw_config.setSimilarity(BM25Similarity())

    with IndexWriter(index_path, iw_config) as iw:
        with DirectoryTaxonomyWriter(taxo_path) as tw:
            for raw in documents:
                doc = Document()
                doc.add(TextField("title", raw["title"], Field.Store.YES))
                doc.add(TextField("body", raw["body"], Field.Store.NO))

                # Facet fields
                doc.add(FacetField("category", raw["category"]))  # e.g., "Science/Physics"
                for tag in raw.get("tags", []):
                    doc.add(FacetField("tags", tag))

                enriched = config.build(tw, doc)
                iw.addDocument(enriched)


def search_with_facets(index_dir, taxonomy_dir, query, top_n=10, top_facets=5):
    """
    Search with facet counting.
    Returns: (results, facets_by_category)
    """
    from org.apache.lucene.facet import DrillDownQuery, DrillSideways

    index_path = MMapDirectory(Paths.get(index_dir))
    taxo_path = MMapDirectory(Paths.get(taxonomy_dir))

    reader = DirectoryReader.open(index_path)
    searcher = IndexSearcher(reader)
    taxo_reader = DirectoryTaxonomyReader(taxo_path)

    config = FacetsConfig()

    # DrillSideways: compute facet counts even for filtered results
    ds = DrillSideways(searcher, config, taxo_reader)
    result = ds.search(query, top_n)

    facets = result.facets
    category_facets = facets.getTopChildren(top_facets, "category")
    tag_facets = facets.getTopChildren(top_facets, "tags")

    return result.hits, {
        "category": [(l.label, l.value) for l in category_facets.labelValues],
        "tags":     [(l.label, l.value) for l in tag_facets.labelValues],
    }
```

---

## 🔄 COMPLETE PIPELINE — PRODUCTION EXAMPLE

```python
"""
Production-grade IR pipeline with:
- Proper JVM initialization
- EnglishAnalyzer with custom stop words
- BM25Similarity (k1=1.2, b=0.75)
- PerFieldAnalyzerWrapper
- IndexWriter with upsert semantics
- NRT search
- Multi-field query with boosts
- Score explanation
- Highlighted snippets
- RAG context assembly
"""

import lucene
from java.nio.file import Paths
from java.util import HashMap

# Lucene classes
from org.apache.lucene.store import MMapDirectory, ByteBuffersDirectory
from org.apache.lucene.analysis.en import EnglishAnalyzer
from org.apache.lucene.analysis.core import KeywordAnalyzer, WhitespaceAnalyzer
from org.apache.lucene.analysis.miscellaneous import PerFieldAnalyzerWrapper
from org.apache.lucene.analysis import CharArraySet
from org.apache.lucene.index import (
    IndexWriter, IndexWriterConfig, DirectoryReader, Term
)
from org.apache.lucene.document import (
    Document, Field, TextField, StringField, StoredField,
    LongPoint, NumericDocValuesField
)
from org.apache.lucene.search import (
    IndexSearcher, BooleanQuery, BooleanClause, BoostQuery, ConstantScoreQuery
)
from org.apache.lucene.search.similarities import BM25Similarity
from org.apache.lucene.queryparser.classic import MultiFieldQueryParser, QueryParser


class LuceneIRPipeline:
    """
    A fully encapsulated IR pipeline.
    Thread safety: attach each thread to JVM before use.
    """

    def __init__(self, index_path=None, in_memory=False):
        # Initialize JVM — safe to call multiple times (no-op if already running)
        lucene.initVM(vmargs=['-Djava.awt.headless=true'])

        # Directory
        if in_memory:
            self.directory = ByteBuffersDirectory()
        else:
            self.directory = MMapDirectory(Paths.get(index_path))

        # Analyzer
        stop_words = CharArraySet(
            ["the","a","an","in","on","at","to","for","of","and","or","but"], True
        )
        self.field_analyzers = {
            "title":  EnglishAnalyzer(stop_words),
            "body":   EnglishAnalyzer(stop_words),
            "id":     KeywordAnalyzer(),
            "url":    KeywordAnalyzer(),
            "tags":   WhitespaceAnalyzer(),
        }
        self.analyzer = PerFieldAnalyzerWrapper(
            EnglishAnalyzer(stop_words), self.field_analyzers
        )

        # Similarity
        self.similarity = BM25Similarity(1.2, 0.75)

        # Writer
        config = IndexWriterConfig(self.analyzer)
        config.setOpenMode(IndexWriterConfig.OpenMode.CREATE_OR_APPEND)
        config.setSimilarity(self.similarity)
        config.setRAMBufferSizeMB(256.0)
        self.writer = IndexWriter(self.directory, config)

        # Reader/Searcher (NRT)
        self._reader = DirectoryReader.open(self.writer)
        self._searcher = IndexSearcher(self._reader)
        self._searcher.setSimilarity(self.similarity)

    def _refresh_reader(self):
        """Refresh the NRT reader if the index has changed."""
        new_reader = DirectoryReader.openIfChanged(self._reader)
        if new_reader is not None:
            self._reader.close()
            self._reader = new_reader
            self._searcher = IndexSearcher(self._reader)
            self._searcher.setSimilarity(self.similarity)

    def index(self, doc_id, title, body, url="", tags=None, pub_date_ms=0):
        """Upsert a document."""
        doc = Document()
        doc.add(StringField("id", doc_id, Field.Store.YES))
        doc.add(TextField("title", title, Field.Store.YES))
        doc.add(TextField("body", body, Field.Store.NO))
        doc.add(StoredField("body_stored", body))
        doc.add(StringField("url", url, Field.Store.YES))
        doc.add(LongPoint("pub_date", pub_date_ms))
        doc.add(NumericDocValuesField("pub_date_dv", pub_date_ms))
        if tags:
            for tag in tags:
                doc.add(StringField("tags", tag, Field.Store.YES))
        self.writer.updateDocument(Term("id", doc_id), doc)

    def commit(self):
        self.writer.commit()
        self._refresh_reader()

    def search(self, query_text, top_n=10, filter_tags=None):
        """
        Full search pipeline.
        
        Args:
            query_text:  Natural language query
            top_n:       Number of results
            filter_tags: Optional list of tags to filter on (AND)
        
        Returns: list of result dicts with score, id, title, url, snippet
        """
        self._refresh_reader()

        # Build multi-field query with boosts
        boosts = HashMap()
        boosts.put("title", 3.0)
        boosts.put("body", 1.0)

        parser = MultiFieldQueryParser(["title", "body"], self.analyzer, boosts)
        parser.setDefaultOperator(MultiFieldQueryParser.Operator.OR)

        try:
            main_query = parser.parse(QueryParser.escape(query_text))
        except Exception as e:
            print(f"Query parse error: {e}")
            return []

        # Optional tag filter
        if filter_tags:
            bq = BooleanQuery.Builder()
            bq.add(main_query, BooleanClause.Occur.MUST)
            for tag in filter_tags:
                from org.apache.lucene.search import TermQuery
                from org.apache.lucene.index import Term as LTerm
                tag_q = ConstantScoreQuery(TermQuery(LTerm("tags", tag)))
                bq.add(tag_q, BooleanClause.Occur.FILTER)
            final_query = bq.build()
        else:
            final_query = main_query

        top_docs = self._searcher.search(final_query, top_n)

        results = []
        for sd in top_docs.scoreDocs:
            doc = self._searcher.doc(sd.doc)
            body = doc.get("body_stored") or ""
            snippet = highlight_results(self._searcher, self.analyzer, final_query, body) or body[:300]
            results.append({
                "rank":    len(results) + 1,
                "score":   round(sd.score, 4),
                "id":      doc.get("id"),
                "title":   doc.get("title"),
                "url":     doc.get("url"),
                "snippet": snippet,
            })

        return results, top_docs.totalHits.value

    def get_rag_context(self, question, top_n=5):
        """Retrieve and format context for LLM RAG."""
        context, sources = build_rag_context(
            self._searcher, self.analyzer, question, top_n=top_n
        )
        return build_prompt_with_context(question, context), sources

    def close(self):
        self._reader.close()
        self.writer.close()
        self.directory.close()


# ── USAGE EXAMPLE ─────────────────────────────────────────────
if __name__ == "__main__":
    pipeline = LuceneIRPipeline(in_memory=True)

    # Index documents
    pipeline.index(
        doc_id="001",
        title="BM25 Information Retrieval Model",
        body="BM25 is a ranking function used in information retrieval. "
             "It is based on probabilistic retrieval framework and improves "
             "on classical TF-IDF by adding document length normalization.",
        tags=["ir", "ranking", "bm25"],
    )
    pipeline.index(
        doc_id="002",
        title="Neural Information Retrieval",
        body="Dense retrieval uses neural embeddings to represent queries and "
             "documents in a shared vector space, enabling semantic search.",
        tags=["ir", "neural", "embeddings"],
    )
    pipeline.commit()

    # Search
    results, total = pipeline.search("probabilistic ranking model", top_n=5)
    for r in results:
        print(f"[{r['rank']}] {r['title']} (score={r['score']})")
        print(f"    {r['snippet']}\n")

    # RAG
    prompt, sources = pipeline.get_rag_context("What is BM25?")
    print("RAG Prompt:\n", prompt)

    pipeline.close()
```

---

## 🐛 DEBUGGING AND DIAGNOSTICS

```python
def diagnose_index(directory):
    """Print index health statistics."""
    from org.apache.lucene.index import DirectoryReader, CheckIndex

    reader = DirectoryReader.open(directory)
    print(f"Total documents:   {reader.numDocs()}")
    print(f"Max documents:     {reader.maxDoc()}")
    print(f"Deleted documents: {reader.numDeletedDocs()}")
    print(f"Number of leaves:  {reader.leaves().size()}")

    for ctx in reader.leaves():
        lreader = ctx.reader()
        print(f"  Segment: {lreader.toString()}")
        print(f"    Docs: {lreader.numDocs()}, MaxDoc: {lreader.maxDoc()}")

    reader.close()


def check_index_integrity(directory):
    """Run Lucene's CheckIndex tool — detects corruption."""
    from org.apache.lucene.index import CheckIndex
    import java.io.PrintStream

    checker = CheckIndex(directory)
    status = checker.checkIndex()
    if status.clean:
        print("✅ Index is clean")
    else:
        print(f"❌ Index has problems: {status.totLoseDocCount} docs lost")
    return status.clean


def get_term_stats(reader, field, term_text):
    """Get corpus statistics for a specific term."""
    from org.apache.lucene.index import Term

    term = Term(field, term_text)
    df = reader.docFreq(term)       # number of docs containing term
    ttf = reader.totalTermFreq(term) # total occurrences across all docs
    print(f"Term '{term_text}' in field '{field}':")
    print(f"  Document Frequency: {df}")
    print(f"  Total Term Frequency: {ttf}")
    return df, ttf


def dump_terms(reader, field, max_terms=50):
    """Dump all terms in a field (useful for debugging tokenization)."""
    from org.apache.lucene.index import MultiTerms
    terms = MultiTerms.getTerms(reader, field)
    if terms is None:
        print(f"No terms in field '{field}'")
        return
    enum = terms.iterator()
    count = 0
    while enum.next() is not None and count < max_terms:
        print(enum.term().utf8ToString())
        count += 1
```

---

## ⚠️ COMMON ERRORS AND FIXES

| Error | Cause | Fix |
|---|---|---|
| `JVMNotFoundException` | JVM not initialized | Call `lucene.initVM()` before any Lucene import usage |
| `AlreadyClosedException` | Using closed reader/writer | Never cache readers — refresh with `openIfChanged()` |
| `LockObtainFailedException` | Two writers on same index | Ensure only one IndexWriter open. Delete stale `write.lock` |
| `TooManyClauses` | BooleanQuery clause limit | Set `BooleanQuery.setMaxClauseCount(4096)` before querying |
| `QueryParserError` | Special chars in query | Use `QueryParser.escape(queryText)` before parsing |
| Empty results | Analyzer mismatch | Ensure same analyzer at index and search time |
| Score = 0.0 | Field not analyzed, using TermQuery | Verify token with `inspect_analyzer()` |
| NegativeArraySizeException | Numeric field queried as text | Use `IntPoint.newRangeQuery()` not `TermQuery` for numerics |
| Stale results | Reader not refreshed | Call `DirectoryReader.openIfChanged()` after commit |
| OutOfMemoryError | RAMBuffer too large or too many docs cached | Reduce `setRAMBufferSizeMB()`, increase JVM heap |

---

## 📐 QUICK REFERENCE: SIMILARITY COMPARISON

| Model | Strengths | Weaknesses | Best For |
|---|---|---|---|
| **BM25** | Robust, well-tuned defaults, saturation | No semantic understanding | General IR, web search (DEFAULT) |
| **TF-IDF (Classic)** | Simple, predictable | No length norm saturation | Legacy systems, baselines |
| **LM Dirichlet** | Probabilistic, handles zero-freq | Needs good μ tuning | Medical, legal, TREC tasks |
| **LM JM** | Good for long queries | Sensitive to λ | Verbose query retrieval |
| **DFR** | Competitive, many configurations | Complex tuning | Research, heterogeneous corpora |
| **IB** | Principled information theory | Academic, rarely outperforms BM25 | Research only |

---

## 🔗 QUICK LINKS (BOOKMARK THESE)

- **BM25 Paper**: Robertson & Zaragoza (2009) — https://www.staff.city.ac.uk/~sb317/papers/foundations_bm25_review.pdf
- **Lucene in Action Book**: https://www.manning.com/books/lucene-in-action-second-edition
- **TREC Benchmarks**: https://trec.nist.gov/
- **PyLucene Examples**: https://svn.apache.org/repos/asf/lucene/pylucene/trunk/samples/
- **Lucene Demo (Java reference)**: https://lucene.apache.org/core/9_10_0/demo/index.html
- **Lucene Similarity JavaDoc**: https://lucene.apache.org/core/9_10_0/core/org/apache/lucene/search/similarities/Similarity.html
- **Apache Lucene Issue Tracker (JIRA)**: https://issues.apache.org/jira/projects/LUCENE

---

*SKILL VERSION: 1.0.0 | Compatible with PyLucene 9.x | Last validated: 2025*
*When in doubt, check the JavaDoc. The source of truth is always the official Apache Lucene documentation.*
