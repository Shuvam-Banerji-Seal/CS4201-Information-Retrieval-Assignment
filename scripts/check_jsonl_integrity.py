#!/usr/bin/env python3
"""Validate JSONL completeness and structural integrity.

Author: Shuvam Banerji Seal
"""

import builtins
import json
from pathlib import Path

BASE = Path('/home/shuvam/Downloads/sem8/CS4201__Information_Retrieval_and_Web_Search/en.docs.2011')

AUTHOR_NAME = "Shuvam Banerji Seal"


def log_print(*args, **kwargs) -> None:
    builtins.print(f"[Author: {AUTHOR_NAME}]", *args, **kwargs)


print = log_print

collections = [
    ('en_BDNews24', BASE / 'en_BDNews24', BASE / 'outputs' / 'jsonl' / 'combined_en_BDNews24.jsonl'),
    ('en_TheTelegraph_2001-2010', BASE / 'en_TheTelegraph_2001-2010', BASE / 'outputs' / 'jsonl' / 'combined_en_TheTelegraph_2001_2010.jsonl'),
]

for name, source_root, jsonl_path in collections:
    print('=' * 90)
    print(name)
    print('source_root=', source_root)
    print('jsonl_path=', jsonl_path)

    if not jsonl_path.exists():
        print('STATUS=FAIL jsonl_missing')
        continue

    source_paths = set()
    for p in source_root.rglob('*'):
        if p.is_file() and not p.name.startswith('.'):
            source_paths.add(str(p.relative_to(source_root)))

    line_count = 0
    blank_lines = 0
    json_errors = 0
    first_json_error = None
    missing_docno = 0
    missing_text = 0
    missing_source_rel_path = 0

    jsonl_paths = set()
    duplicate_source_rel_path = 0

    with jsonl_path.open('r', encoding='utf-8') as f:
        for ln, line in enumerate(f, start=1):
            line_count += 1
            if not line.strip():
                blank_lines += 1
                continue
            try:
                obj = json.loads(line)
            except Exception as e:
                json_errors += 1
                if first_json_error is None:
                    first_json_error = (ln, str(e))
                continue

            rel = obj.get('source_rel_path', '')
            if not rel:
                missing_source_rel_path += 1
            else:
                if rel in jsonl_paths:
                    duplicate_source_rel_path += 1
                jsonl_paths.add(rel)

            if not obj.get('docno'):
                missing_docno += 1
            if not obj.get('text'):
                missing_text += 1

    missing_in_jsonl = source_paths - jsonl_paths
    extra_in_jsonl = jsonl_paths - source_paths

    print('source_file_count=', len(source_paths))
    print('jsonl_line_count=', line_count)
    print('json_errors=', json_errors)
    print('blank_lines=', blank_lines)
    print('missing_source_rel_path=', missing_source_rel_path)
    print('duplicate_source_rel_path=', duplicate_source_rel_path)
    print('missing_docno=', missing_docno)
    print('missing_text=', missing_text)
    print('missing_in_jsonl=', len(missing_in_jsonl))
    print('extra_in_jsonl=', len(extra_in_jsonl))
    if first_json_error:
        print('first_json_error=', first_json_error)

    ok = (
        len(source_paths) == line_count and
        json_errors == 0 and
        blank_lines == 0 and
        missing_source_rel_path == 0 and
        duplicate_source_rel_path == 0 and
        len(missing_in_jsonl) == 0 and
        len(extra_in_jsonl) == 0
    )
    print('STATUS=', 'PASS' if ok else 'FAIL')
