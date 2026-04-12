#!/usr/bin/env python3
"""Evaluate a TREC/FIRE run file against qrels without external dependencies.

Author: Shuvam Banerji Seal

Run format (TSV or whitespace):
QID Q0 DOCID RANK SCORE RUNNAME

Qrel format:
QID Q0 DOCID REL
"""

from __future__ import annotations

import argparse
import builtins
from collections import defaultdict
from pathlib import Path


AUTHOR_NAME = "Shuvam Banerji Seal"


def log_print(*args, **kwargs) -> None:
    builtins.print(f"[Author: {AUTHOR_NAME}]", *args, **kwargs)


print = log_print


def parse_qrels(path: Path) -> dict[str, dict[str, int]]:
    qrels: dict[str, dict[str, int]] = defaultdict(dict)
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            qid, _, docid, rel = parts[0], parts[1], parts[2], parts[3]
            try:
                qrels[qid][docid] = int(rel)
            except ValueError:
                continue
    return qrels


def parse_run(path: Path) -> dict[str, list[str]]:
    run_docs: dict[str, list[tuple[int, str, float]]] = defaultdict(list)
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) < 6:
                continue
            qid, _, docid, rank, score, _ = parts[:6]
            try:
                rank_i = int(rank)
            except ValueError:
                rank_i = 10**9
            try:
                score_f = float(score)
            except ValueError:
                score_f = 0.0
            run_docs[qid].append((rank_i, docid, score_f))

    ranked: dict[str, list[str]] = {}
    for qid, rows in run_docs.items():
        rows.sort(key=lambda x: (x[0], -x[2]))
        ranked[qid] = [docid for _, docid, _ in rows]
    return ranked


def precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if k <= 0:
        return 0.0
    top = retrieved[:k]
    if not top:
        return 0.0
    hits = sum(1 for d in top if d in relevant)
    return hits / k


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    top = retrieved[:k]
    hits = sum(1 for d in top if d in relevant)
    return hits / len(relevant)


def average_precision(retrieved: list[str], relevant: set[str]) -> float:
    if not relevant:
        return 0.0
    hit_count = 0
    ap_sum = 0.0
    for i, docid in enumerate(retrieved, start=1):
        if docid in relevant:
            hit_count += 1
            ap_sum += hit_count / i
    return ap_sum / len(relevant)


def evaluate(qrels: dict[str, dict[str, int]], run: dict[str, list[str]], cutoff: int) -> dict[str, float]:
    qids = sorted(qrels.keys(), key=lambda x: int(x) if x.isdigit() else x)
    if not qids:
        return {
            "topics": 0.0,
            "MAP": 0.0,
            "P@10": 0.0,
            f"P@{cutoff}": 0.0,
            f"Recall@{cutoff}": 0.0,
        }

    map_scores = []
    p10_scores = []
    pk_scores = []
    rk_scores = []

    for qid in qids:
        rel_docs = {docid for docid, rel in qrels[qid].items() if rel > 0}
        retrieved = run.get(qid, [])

        map_scores.append(average_precision(retrieved, rel_docs))
        p10_scores.append(precision_at_k(retrieved, rel_docs, 10))
        pk_scores.append(precision_at_k(retrieved, rel_docs, cutoff))
        rk_scores.append(recall_at_k(retrieved, rel_docs, cutoff))

    n = len(qids)
    return {
        "topics": float(n),
        "MAP": sum(map_scores) / n,
        "P@10": sum(p10_scores) / n,
        f"P@{cutoff}": sum(pk_scores) / n,
        f"Recall@{cutoff}": sum(rk_scores) / n,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate FIRE run against qrels")
    parser.add_argument("--qrels", required=True, help="Path to qrels file")
    parser.add_argument("--run", required=True, help="Path to run file")
    parser.add_argument("--cutoff", type=int, default=100, help="Cutoff for P@k and Recall@k")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    qrels_path = Path(args.qrels)
    run_path = Path(args.run)

    qrels = parse_qrels(qrels_path)
    run = parse_run(run_path)
    metrics = evaluate(qrels, run, args.cutoff)

    print(f"qrels={qrels_path}")
    print(f"run={run_path}")
    for k, v in metrics.items():
        if k == "topics":
            print(f"{k}={int(v)}")
        else:
            print(f"{k}={v:.6f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
