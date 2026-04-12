#!/usr/bin/env python3
"""Quick BM25 parameter sweep for FIRE 2012 English topics.

Author: Shuvam Banerji Seal

This script runs retrieval for multiple (k1, b) pairs and evaluates MAP
against both qrel versions.
"""

from __future__ import annotations

import argparse
import builtins
import csv
import io
from contextlib import redirect_stdout
from pathlib import Path

from evaluate_run import evaluate, parse_qrels, parse_run
from retriever import parse_topics, run_retrieval


PROJECT_ROOT = Path(__file__).resolve().parents[1]

AUTHOR_NAME = "Shuvam Banerji Seal"


def log_print(*args, **kwargs) -> None:
    builtins.print(f"[Author: {AUTHOR_NAME}]", *args, **kwargs)


print = log_print


def resolve_path(path_value: str) -> Path:
    p = Path(path_value)
    if p.is_absolute():
        return p
    return PROJECT_ROOT / p


def parse_float_list(raw: str) -> list[float]:
    values: list[float] = []
    for part in raw.split(","):
        v = part.strip()
        if not v:
            continue
        values.append(float(v))
    return values


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BM25 sweep over k1 and b")
    parser.add_argument(
        "--index-dir",
        default="outputs/indexes/pylucene_en_docs",
        help="Path to Lucene index",
    )
    parser.add_argument(
        "--topics-file",
        default="data/fire2012/adhoc/topics/en.topics.176-225.2012.txt",
        help="Path to topics file",
    )
    parser.add_argument(
        "--qrels-v1",
        default="data/fire2012/adhoc/qrels/en.qrels.176-225.2012-v1.txt",
        help="Path to qrels v1",
    )
    parser.add_argument(
        "--qrels-v2",
        default="data/fire2012/adhoc/qrels/en.qrels.176-225.2012-v2.txt",
        help="Path to qrels v2",
    )
    parser.add_argument(
        "--k1-values",
        default="0.8,1.0,1.2,1.5,1.8,2.0",
        help="Comma-separated k1 values",
    )
    parser.add_argument(
        "--b-values",
        default="0.2,0.4,0.6,0.75,0.9",
        help="Comma-separated b values",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=100,
        help="Number of documents to retrieve per query",
    )
    parser.add_argument(
        "--query-mode",
        choices=["title", "title_desc", "title_desc_narr"],
        default="title",
        help="Topic text selection mode",
    )
    parser.add_argument(
        "--cutoff",
        type=int,
        default=100,
        help="Evaluation cutoff",
    )
    parser.add_argument(
        "--output-csv",
        default="outputs/analysis/bm25_sweep_results.csv",
        help="Where to store all sweep results",
    )
    parser.add_argument(
        "--temp-run",
        default="outputs/runs/_bm25_sweep_tmp.tsv",
        help="Temporary run file reused during sweep",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    index_dir = resolve_path(args.index_dir)
    topics_file = resolve_path(args.topics_file)
    qrels_v1_file = resolve_path(args.qrels_v1)
    qrels_v2_file = resolve_path(args.qrels_v2)
    output_csv = resolve_path(args.output_csv)
    temp_run = resolve_path(args.temp_run)

    k1_values = parse_float_list(args.k1_values)
    b_values = parse_float_list(args.b_values)

    if not k1_values or not b_values:
        raise ValueError("Both k1 and b value lists must be non-empty")

    topics = parse_topics(topics_file)
    qrels_v1 = parse_qrels(qrels_v1_file)
    qrels_v2 = parse_qrels(qrels_v2_file)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    temp_run.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, float]] = []

    total = len(k1_values) * len(b_values)
    done = 0

    for k1 in k1_values:
        for b in b_values:
            done += 1
            run_name = f"sweep_k1_{k1}_b_{b}"
            print(f"[{done}/{total}] k1={k1} b={b}")

            # Silence verbose per-run summaries while keeping sweep progress output.
            with redirect_stdout(io.StringIO()):
                run_retrieval(
                    topics=topics,
                    index_dir=index_dir,
                    output_file=temp_run,
                    model="bm25",
                    k1=k1,
                    b=b,
                    mu=2000.0,
                    lambd=0.2,
                    analyzer_name="english",
                    default_operator="OR",
                    query_mode=args.query_mode,
                    top_k=args.top_k,
                    run_name=run_name,
                )

            run = parse_run(temp_run)
            m1 = evaluate(qrels_v1, run, args.cutoff)
            m2 = evaluate(qrels_v2, run, args.cutoff)

            row = {
                "k1": k1,
                "b": b,
                "map_v1": m1["MAP"],
                "map_v2": m2["MAP"],
            }
            rows.append(row)
            print(
                f"    MAP(v1)={row['map_v1']:.6f} MAP(v2)={row['map_v2']:.6f}"
            )

    best_v1 = max(rows, key=lambda r: r["map_v1"])
    best_v2 = max(rows, key=lambda r: r["map_v2"])

    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["k1", "b", "map_v1", "map_v2"])
        writer.writeheader()
        writer.writerows(rows)

    print("\n=== BEST PARAMETERS ===")
    print(
        f"v1_best: k1={best_v1['k1']} b={best_v1['b']} MAP={best_v1['map_v1']:.6f}"
    )
    print(
        f"v2_best: k1={best_v2['k1']} b={best_v2['b']} MAP={best_v2['map_v2']:.6f}"
    )
    print(f"results_csv: {output_csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
