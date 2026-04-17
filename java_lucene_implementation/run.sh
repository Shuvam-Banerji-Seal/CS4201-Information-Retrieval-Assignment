#!/usr/bin/env bash
# ============================================================
# CS4201 Java Lucene — build + run script
# Author: Shuvam Banerji Seal (22MS076)
#
# Usage (from java_lucene_implementation/):
#   chmod +x run.sh
#   ./run.sh index      # Build Lucene index from JSONL
#   ./run.sh retrieve   # Run BM25 retrieval over FIRE topics
#   ./run.sh all        # Do both in sequence
#   ./run.sh compare    # Diff Java TSV vs Python TSV
#
# The script always builds the fat jar first (mvn package -q).
# ============================================================
set -euo pipefail

# Resolve script directory so it works from any CWD
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JAR="${SCRIPT_DIR}/target/java-lucene-ir-1.0-SNAPSHOT.jar"
PYTHON_TSV="${SCRIPT_DIR}/../outputs/runs/final_bm25_k1_1.5_b_0.4_Shuvam_Banerji_Seal_22MS076.tsv"
JAVA_TSV="${SCRIPT_DIR}/../outputs/runs/java_bm25_k1_1.5_b_0.4_Shuvam_Banerji_Seal_22MS076.tsv"

build() {
    echo "[run.sh] Building fat jar (mvn package -q) ..."
    cd "${SCRIPT_DIR}"
    mvn package -q
    echo "[run.sh] Build complete: ${JAR}"
}

run_indexer() {
    echo "[run.sh] Running Java Indexer ..."
    java -Xmx4g -cp "${JAR}" cs4201.Indexer
}

run_retriever() {
    echo "[run.sh] Running Java Retriever ..."
    java -Xmx2g -cp "${JAR}" cs4201.Retriever
}

compare_tsv() {
    if [[ ! -f "${PYTHON_TSV}" ]]; then
        echo "[compare] Python TSV not found: ${PYTHON_TSV}"
        exit 1
    fi
    if [[ ! -f "${JAVA_TSV}" ]]; then
        echo "[compare] Java TSV not found: ${JAVA_TSV}"
        echo "[compare] Run './run.sh retrieve' first."
        exit 1
    fi

    echo "=== Row counts ==="
    echo "Python: $(wc -l < "${PYTHON_TSV}") rows"
    echo "Java:   $(wc -l < "${JAVA_TSV}") rows"

    echo ""
    echo "=== Topics in Python TSV ==="
    awk '{print $1}' "${PYTHON_TSV}" | sort -nu | tr '\n' ' '
    echo ""

    echo "=== Topics in Java TSV ==="
    awk '{print $1}' "${JAVA_TSV}" | sort -nu | tr '\n' ' '
    echo ""

    echo ""
    echo "=== Top-10 Java results for first topic ==="
    FIRST_TOPIC=$(awk 'NR==1{print $1}' "${JAVA_TSV}")
    awk -v t="${FIRST_TOPIC}" '$1==t{print}' "${JAVA_TSV}" | head -10

    echo ""
    echo "=== Shared doc IDs in rank 1-10 for topic ${FIRST_TOPIC} ==="
    PY_TOP10=$(awk -v t="${FIRST_TOPIC}" '$1==t && $4<=10{print $3}' "${PYTHON_TSV}" | sort)
    JV_TOP10=$(awk -v t="${FIRST_TOPIC}" '$1==t && $4<=10{print $3}' "${JAVA_TSV}"   | sort)
    comm -12 <(echo "${PY_TOP10}") <(echo "${JV_TOP10}")

    echo ""
    echo "Compare done. Both files use the same BM25 params + EnglishAnalyzer,"
    echo "so top-ranked docs should largely overlap (minor score differences expected"
    echo "due to index-time IDF computed over identical corpora)."
}

case "${1:-all}" in
    build)    build ;;
    index)    build && run_indexer ;;
    retrieve) build && run_retriever ;;
    all)      build && run_indexer && run_retriever ;;
    compare)  compare_tsv ;;
    *)
        echo "Usage: $0 {build|index|retrieve|all|compare}"
        exit 1
        ;;
esac
