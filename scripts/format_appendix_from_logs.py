#!/usr/bin/env python3
"""Format appendix entries by reading the most recent chat JSON logs.

Usage:
  python3 scripts/format_appendix_from_logs.py --n 5 --out appendix.md

This reads the latest N chat_*.json files from logs/ and creates a simple
Markdown appendix where each entry contains the question and the top 1-2
text chunks (with source and page_number) as the "Correct textbook chunk(s)".
"""
import argparse
import json
from pathlib import Path
from typing import List


def find_latest_logs(logs_dir: Path, n: int) -> List[Path]:
    files = sorted(logs_dir.glob("chat_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:n]


def format_entry(log_path: Path) -> str:
    data = json.loads(log_path.read_text(encoding="utf-8"))
    q = data.get("query", "(no query)")
    retrieved = data.get("retrieved_chunks") or data.get("retrieved_chunks", [])

    lines = []
    lines.append(f"Question: {q}\n")
    lines.append("Correct textbook chunk(s):\n")

    # If retrieved_chunks is present as list of dicts
    if isinstance(retrieved, list) and len(retrieved) > 0:
        # take top 2
        for i, ch in enumerate(retrieved[:2], start=1):
            idx = ch.get("idx", ch.get("chunk_id", "?"))
            source = ch.get("source", "?")
            page = ch.get("page_number", ch.get("page", "?"))
            chunk_text = ch.get("chunk") or ch.get("text") or "(no chunk text)"
            # sanitize newlines
            snippet = chunk_text.strip().replace('\n', ' ')
            lines.append(f"- Chunk rank {i} (idx: {idx}, source: {source}, page: {page}):\n  \"{snippet}\"\n")
    else:
        # fallback: try top_idxs and chunks arrays if present
        top_idxs = data.get("top_idxs") or []
        chunks = data.get("chunks") or []
        if top_idxs and chunks:
            for i, idx in enumerate(top_idxs[:2], start=1):
                try:
                    chunk_text = chunks[idx]
                except Exception:
                    chunk_text = "(chunk not found)"
                snippet = str(chunk_text).strip().replace('\n', ' ')
                lines.append(f"- Chunk rank {i} (idx: {idx}):\n  \"{snippet}\"\n")
        else:
            lines.append("(no retrieved chunks found in log)\n")

    lines.append("---\n")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=5, help="number of recent chat logs to process")
    parser.add_argument("--logs", default="logs", help="logs directory")
    parser.add_argument("--out", default="appendix_two_phase_locking.md", help="output markdown file")
    args = parser.parse_args()

    logs_dir = Path(args.logs)
    if not logs_dir.exists():
        print(f"Logs directory not found: {logs_dir}")
        return

    latest = find_latest_logs(logs_dir, args.n)
    if not latest:
        print("No chat logs found in logs/ (chat_*.json)")
        return

    out_lines = ["# Appendix: Study Session (auto-generated)\n"]
    for p in reversed(latest):
        try:
            out_lines.append(format_entry(p))
        except json.JSONDecodeError:
            print(f"Warning: skipping malformed JSON log: {p}")
        except Exception as e:
            print(f"Warning: skipping log {p}: {e}")

    out_path = Path(args.out)
    out_path.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"Wrote appendix to: {out_path.resolve()}")


if __name__ == "__main__":
    main()
