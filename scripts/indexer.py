#!/usr/bin/env python3
"""Build a PyLucene index for the EN Docs collections.

Author: Shuvam Banerji Seal

This script supports two source modes:
1. jsonl (default): reads prepared JSONL collections in outputs/jsonl/
2. xml: recursively parses raw XML files under collection roots

Each indexed document stores:
- docno (StringField, stored)
- collection (StringField, stored)
- source_rel_path (StringField, stored)
- title (TextField, stored)
- content (TextField, indexed)
"""

from __future__ import annotations

import argparse
import builtins
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Optional
from xml.etree import ElementTree as ET

import lucene
from java.nio.file import Paths
from org.apache.lucene.analysis.en import EnglishAnalyzer
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.document import Document, Field, StringField, TextField
from org.apache.lucene.index import IndexWriter, IndexWriterConfig
from org.apache.lucene.search.similarities import BM25Similarity, ClassicSimilarity
from org.apache.lucene.store import MMapDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSONL_FILES = [
    "outputs/jsonl/combined_en_BDNews24.jsonl",
    "outputs/jsonl/combined_en_TheTelegraph_2001_2010.jsonl",
]
DEFAULT_XML_ROOTS = [
    "en_BDNews24",
    "en_TheTelegraph_2001-2010",
]

AUTHOR_NAME = "Shuvam Banerji Seal"


def log_print(*args, **kwargs) -> None:
    builtins.print(f"[Author: {AUTHOR_NAME}]", *args, **kwargs)


print = log_print


@dataclass
class SourceDoc:
    docno: str
    title: str
    content: str
    collection: str
    source_rel_path: str


def init_vm() -> None:
    """Initialize or attach to the PyLucene VM exactly once per process."""
    vm_env = lucene.getVMEnv()
    if vm_env is None:
        lucene.initVM(vmargs=["-Djava.awt.headless=true"])
    else:
        vm_env.attachCurrentThread()


def normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def build_similarity(model: str, k1: float, b: float):
    if model == "bm25":
        return BM25Similarity(float(k1), float(b))
    if model == "classic":
        return ClassicSimilarity()
    raise ValueError(f"Unsupported model: {model}")


def build_analyzer(analyzer_name: str):
    if analyzer_name == "english":
        return EnglishAnalyzer()
    if analyzer_name == "standard":
        return StandardAnalyzer()
    raise ValueError(f"Unsupported analyzer: {analyzer_name}")


def resolve_path(p: str) -> Path:
    candidate = Path(p)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate


def iter_jsonl_documents(jsonl_files: Iterable[Path]) -> Iterator[SourceDoc]:
    for jsonl_file in jsonl_files:
        if not jsonl_file.exists():
            print(f"[WARN] JSONL file missing: {jsonl_file}", file=sys.stderr)
            continue

        print(f"[INFO] Reading JSONL: {jsonl_file}")
        with jsonl_file.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as exc:
                    print(
                        f"[WARN] JSON decode failed: {jsonl_file}:{line_no}: {exc}",
                        file=sys.stderr,
                    )
                    continue

                docno = normalize_text(obj.get("docno"))
                title = normalize_text(obj.get("title"))
                content = normalize_text(obj.get("text") or obj.get("content"))
                collection = normalize_text(obj.get("collection"))
                source_rel_path = normalize_text(obj.get("source_rel_path"))

                if not docno or not content:
                    continue

                yield SourceDoc(
                    docno=docno,
                    title=title,
                    content=content,
                    collection=collection,
                    source_rel_path=source_rel_path,
                )


def extract_field_text(doc_elem: ET.Element, tags: list[str]) -> str:
    for tag in tags:
        node = doc_elem.find(tag)
        if node is not None:
            text = normalize_text(" ".join(node.itertext()))
            if text:
                return text
    return ""


def iter_xml_documents(xml_roots: Iterable[Path]) -> Iterator[SourceDoc]:
    for xml_root in xml_roots:
        if not xml_root.exists():
            print(f"[WARN] XML root missing: {xml_root}", file=sys.stderr)
            continue

        print(f"[INFO] Reading XML root: {xml_root}")
        for file_path in xml_root.rglob("*"):
            if not file_path.is_file() or file_path.name.startswith("."):
                continue

            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
            except ET.ParseError as exc:
                print(f"[WARN] XML parse failed: {file_path}: {exc}", file=sys.stderr)
                continue
            except Exception as exc:  # noqa: BLE001
                print(f"[WARN] XML read failed: {file_path}: {exc}", file=sys.stderr)
                continue

            doc_nodes = [root] if root.tag == "DOC" else list(root.findall(".//DOC"))
            if not doc_nodes:
                continue

            for doc_elem in doc_nodes:
                docno = extract_field_text(doc_elem, ["DOCNO", "docno"])
                title = extract_field_text(doc_elem, ["TITLE", "title"])
                content = extract_field_text(doc_elem, ["CONTENT", "TEXT", "content", "text"])
                if not content:
                    content = normalize_text(" ".join(doc_elem.itertext()))

                if not docno or not content:
                    continue

                try:
                    source_rel_path = str(file_path.relative_to(xml_root))
                except ValueError:
                    source_rel_path = file_path.name

                yield SourceDoc(
                    docno=docno,
                    title=title,
                    content=content,
                    collection=xml_root.name,
                    source_rel_path=source_rel_path,
                )


def build_lucene_document(source_doc: SourceDoc) -> Document:
    doc = Document()
    doc.add(StringField("docno", source_doc.docno, Field.Store.YES))
    doc.add(StringField("collection", source_doc.collection, Field.Store.YES))
    doc.add(StringField("source_rel_path", source_doc.source_rel_path, Field.Store.YES))
    doc.add(TextField("title", source_doc.title, Field.Store.YES))

    # Index title + content together to make title terms retrievable in the main field.
    full_content = f"{source_doc.title} {source_doc.content}".strip()
    doc.add(TextField("content", full_content, Field.Store.NO))
    return doc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index EN Docs corpus with PyLucene")
    parser.add_argument(
        "--source-format",
        choices=["jsonl", "xml"],
        default="jsonl",
        help="Input source format for documents",
    )
    parser.add_argument(
        "--jsonl-files",
        nargs="+",
        default=DEFAULT_JSONL_FILES,
        help="JSONL source files (used when --source-format=jsonl)",
    )
    parser.add_argument(
        "--xml-roots",
        nargs="+",
        default=DEFAULT_XML_ROOTS,
        help="XML root folders (used when --source-format=xml)",
    )
    parser.add_argument(
        "--index-dir",
        default="outputs/indexes/pylucene_en_docs",
        help="Directory where Lucene index files are stored",
    )
    parser.add_argument(
        "--open-mode",
        choices=["create", "create_or_append"],
        default="create",
        help="Lucene index open mode",
    )
    parser.add_argument(
        "--analyzer",
        choices=["english", "standard"],
        default="english",
        help="Analyzer used at indexing time",
    )
    parser.add_argument(
        "--model",
        choices=["bm25", "classic"],
        default="bm25",
        help="Similarity model used at indexing time",
    )
    parser.add_argument(
        "--k1",
        type=float,
        default=1.5,
        help="BM25 k1 parameter (only for --model=bm25)",
    )
    parser.add_argument(
        "--b",
        type=float,
        default=0.4,
        help="BM25 b parameter (only for --model=bm25)",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=10000,
        help="Progress logging frequency",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    init_vm()

    index_dir = resolve_path(args.index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)

    analyzer = build_analyzer(args.analyzer)
    similarity = build_similarity(args.model, args.k1, args.b)

    directory = MMapDirectory(Paths.get(str(index_dir)))
    config = IndexWriterConfig(analyzer)
    if args.open_mode == "create":
        config.setOpenMode(IndexWriterConfig.OpenMode.CREATE)
    else:
        config.setOpenMode(IndexWriterConfig.OpenMode.CREATE_OR_APPEND)
    config.setSimilarity(similarity)

    writer = IndexWriter(directory, config)

    indexed = 0
    skipped = 0

    try:
        if args.source_format == "jsonl":
            jsonl_paths = [resolve_path(p) for p in args.jsonl_files]
            source_iter = iter_jsonl_documents(jsonl_paths)
        else:
            xml_roots = [resolve_path(p) for p in args.xml_roots]
            source_iter = iter_xml_documents(xml_roots)

        for source_doc in source_iter:
            if not source_doc.docno or not source_doc.content:
                skipped += 1
                continue

            lucene_doc = build_lucene_document(source_doc)
            writer.addDocument(lucene_doc)
            indexed += 1

            if args.progress_every > 0 and indexed % args.progress_every == 0:
                print(f"[INFO] Indexed {indexed} documents...")

        writer.commit()
        print("\n=== INDEXING COMPLETE ===")
        print(f"index_dir: {index_dir}")
        print(f"source_format: {args.source_format}")
        print(f"indexed_docs: {indexed}")
        print(f"skipped_docs: {skipped}")
        return 0
    finally:
        writer.close()
        directory.close()


if __name__ == "__main__":
    raise SystemExit(main())
