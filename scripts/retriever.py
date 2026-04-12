#!/usr/bin/env python3
"""Run PyLucene retrieval over FIRE topics and export a TSV run file.

Author: Shuvam Banerji Seal

Output format (tab-separated):
QID    Q0    DOCID    RANK    SCORE    RUNNAME

The retriever supports configurable similarity model + parameters.
Default model is BM25 with k1=1.5 and b=0.4 as required.
"""

from __future__ import annotations

import argparse
import builtins
import ssl
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.request import urlretrieve
from xml.etree import ElementTree as ET

import lucene
from java.nio.file import Paths
from org.apache.lucene.analysis.en import EnglishAnalyzer
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.index import DirectoryReader
from org.apache.lucene.queryparser.classic import QueryParser
from org.apache.lucene.search import IndexSearcher
from org.apache.lucene.search.similarities import (
    BM25Similarity,
    ClassicSimilarity,
    LMDirichletSimilarity,
    LMJelinekMercerSimilarity,
)
from org.apache.lucene.store import MMapDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOPICS_URL = "https://www.isical.ac.in/~fire/data/topics/adhoc/en.topics.176-225.2012.txt"
DEFAULT_TOPICS_FILE = "data/fire2012/adhoc/topics/en.topics.176-225.2012.txt"
DEFAULT_INDEX_DIR = "outputs/indexes/pylucene_en_docs"
DEFAULT_RUN_FILE = "outputs/runs/bm25_k1_1.5_b_0.4.tsv"

AUTHOR_NAME = "Shuvam Banerji Seal"


def log_print(*args, **kwargs) -> None:
    builtins.print(f"[Author: {AUTHOR_NAME}]", *args, **kwargs)


print = log_print


@dataclass
class Topic:
    qid: str
    title: str
    desc: str
    narr: str


def init_vm() -> None:
    vm_env = lucene.getVMEnv()
    if vm_env is None:
        lucene.initVM(vmargs=["-Djava.awt.headless=true"])
    else:
        vm_env.attachCurrentThread()


def resolve_path(p: str) -> Path:
    candidate = Path(p)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.split())


def ensure_topics_file(path: Path, url: str, allow_insecure_ssl: bool) -> None:
    if path.exists():
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    if allow_insecure_ssl:
        ssl._create_default_https_context = ssl._create_unverified_context

    print(f"[INFO] Downloading topics from: {url}")
    urlretrieve(url, str(path))
    print(f"[INFO] Topics saved to: {path}")


def parse_topics(topics_file: Path) -> list[Topic]:
    tree = ET.parse(topics_file)
    root = tree.getroot()

    topics: list[Topic] = []
    for top in root.findall(".//top"):
        qid = normalize_text(top.findtext("num"))
        title = normalize_text(top.findtext("title"))
        desc = normalize_text(top.findtext("desc"))
        narr = normalize_text(top.findtext("narr"))
        if not qid:
            continue
        topics.append(Topic(qid=qid, title=title, desc=desc, narr=narr))

    return topics


def build_similarity(model: str, k1: float, b: float, mu: float, lambd: float):
    if model == "bm25":
        return BM25Similarity(float(k1), float(b))
    if model == "classic":
        return ClassicSimilarity()
    if model == "lm_dirichlet":
        return LMDirichletSimilarity(float(mu))
    if model == "lm_jelinek_mercer":
        return LMJelinekMercerSimilarity(float(lambd))
    raise ValueError(f"Unsupported model: {model}")


def build_analyzer(name: str):
    if name == "english":
        return EnglishAnalyzer()
    if name == "standard":
        return StandardAnalyzer()
    raise ValueError(f"Unsupported analyzer: {name}")


def topic_to_query_text(topic: Topic, query_mode: str) -> str:
    if query_mode == "title":
        return topic.title
    if query_mode == "title_desc":
        return normalize_text(f"{topic.title} {topic.desc}")
    if query_mode == "title_desc_narr":
        return normalize_text(f"{topic.title} {topic.desc} {topic.narr}")
    raise ValueError(f"Unsupported query mode: {query_mode}")


def run_retrieval(
    *,
    topics: Iterable[Topic],
    index_dir: Path,
    output_file: Path,
    model: str,
    k1: float,
    b: float,
    mu: float,
    lambd: float,
    analyzer_name: str,
    default_operator: str,
    query_mode: str,
    top_k: int,
    run_name: str,
) -> None:
    init_vm()

    analyzer = build_analyzer(analyzer_name)
    similarity = build_similarity(model, k1, b, mu, lambd)

    directory = MMapDirectory(Paths.get(str(index_dir)))
    reader = DirectoryReader.open(directory)

    try:
        searcher = IndexSearcher(reader)
        searcher.setSimilarity(similarity)

        parser = QueryParser("content", analyzer)
        if default_operator == "AND":
            parser.setDefaultOperator(QueryParser.Operator.AND)
        else:
            parser.setDefaultOperator(QueryParser.Operator.OR)

        output_file.parent.mkdir(parents=True, exist_ok=True)

        query_count = 0
        written_rows = 0

        stored_fields = searcher.storedFields()

        with output_file.open("w", encoding="utf-8") as out:
            for topic in topics:
                query_count += 1
                query_text = topic_to_query_text(topic, query_mode)
                escaped_query = QueryParser.escape(query_text)
                if not escaped_query:
                    continue

                lucene_query = parser.parse(escaped_query)
                top_docs = searcher.search(lucene_query, top_k)

                for rank, score_doc in enumerate(top_docs.scoreDocs, start=1):
                    doc = stored_fields.document(score_doc.doc)
                    docid = doc.get("docno") or f"LUCENE_DOC_{score_doc.doc}"
                    out.write(
                        f"{topic.qid}\tQ0\t{docid}\t{rank}\t{score_doc.score:.6f}\t{run_name}\n"
                    )
                    written_rows += 1

        print("\n=== RETRIEVAL COMPLETE ===")
        print(f"index_dir: {index_dir}")
        print(f"topics_processed: {query_count}")
        print(f"rows_written: {written_rows}")
        print(f"run_file: {output_file}")
        print(f"model: {model}")
        if model == "bm25":
            print(f"bm25_k1: {k1}")
            print(f"bm25_b: {b}")
    finally:
        reader.close()
        directory.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retrieve documents from PyLucene index")
    parser.add_argument("--index-dir", default=DEFAULT_INDEX_DIR, help="Path to Lucene index")
    parser.add_argument("--topics-file", default=DEFAULT_TOPICS_FILE, help="Path to FIRE topics XML")
    parser.add_argument("--topics-url", default=DEFAULT_TOPICS_URL, help="Topics download URL")
    parser.add_argument(
        "--download-topics-if-missing",
        action="store_true",
        help="Download topics file if --topics-file does not exist",
    )
    parser.add_argument(
        "--allow-insecure-ssl",
        action="store_true",
        help="Allow unverified SSL certificate while downloading topics",
    )
    parser.add_argument("--output-run", default=DEFAULT_RUN_FILE, help="Output TSV run file")
    parser.add_argument("--run-name", default="shuvam", help="Run name for the 6th column")
    parser.add_argument("--top-k", type=int, default=100, help="Number of docs to retrieve per topic")

    parser.add_argument(
        "--model",
        choices=["bm25", "classic", "lm_dirichlet", "lm_jelinek_mercer"],
        default="bm25",
        help="Retrieval similarity model",
    )
    parser.add_argument("--k1", type=float, default=1.5, help="BM25 k1")
    parser.add_argument("--b", type=float, default=0.4, help="BM25 b")
    parser.add_argument("--mu", type=float, default=2000.0, help="LM Dirichlet mu")
    parser.add_argument("--lambda", dest="lambd", type=float, default=0.2, help="LM JM lambda")

    parser.add_argument(
        "--analyzer",
        choices=["english", "standard"],
        default="english",
        help="Query analyzer",
    )
    parser.add_argument(
        "--default-operator",
        choices=["OR", "AND"],
        default="OR",
        help="Default boolean operator in QueryParser",
    )
    parser.add_argument(
        "--query-mode",
        choices=["title", "title_desc", "title_desc_narr"],
        default="title",
        help="How to build query text from topic fields",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    index_dir = resolve_path(args.index_dir)
    if not index_dir.exists():
        raise FileNotFoundError(f"Index directory not found: {index_dir}")

    topics_file = resolve_path(args.topics_file)
    if not topics_file.exists():
        if args.download_topics_if_missing:
            ensure_topics_file(topics_file, args.topics_url, args.allow_insecure_ssl)
        else:
            raise FileNotFoundError(
                f"Topics file not found: {topics_file}. "
                "Pass --download-topics-if-missing to fetch automatically."
            )

    topics = parse_topics(topics_file)
    if len(topics) != 50:
        print(f"[WARN] Expected 50 topics, found {len(topics)}")

    output_file = resolve_path(args.output_run)

    run_retrieval(
        topics=topics,
        index_dir=index_dir,
        output_file=output_file,
        model=args.model,
        k1=args.k1,
        b=args.b,
        mu=args.mu,
        lambd=args.lambd,
        analyzer_name=args.analyzer,
        default_operator=args.default_operator,
        query_mode=args.query_mode,
        top_k=args.top_k,
        run_name=args.run_name,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
