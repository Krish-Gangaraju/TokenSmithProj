#!/usr/bin/env python3
"""Generate a sample log file using the diagnostics helpers to validate structure.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.instrumentation.diagnostics import compute_retrieval_metrics, compute_rank_diagnostics
from src.instrumentation.logging import RunLogger


def main():
    # sample data
    topk = [0, 2]
    raw_scores = {
        "faiss": {0: 0.9, 2: 0.8, 1: 0.1},
        "bm25": {0: 0.8, 2: 0.9, 3: 0.2}
    }
    ordered = [0, 2, 1, 3]
    golden = [0, 2]

    rd = compute_rank_diagnostics(raw_scores, ordered, topk)
    rm = compute_retrieval_metrics(topk, golden)

    logger = RunLogger()
    outdir = Path("logs") / "sample_diag"
    outdir.mkdir(parents=True, exist_ok=True)
    logger.logs_dir = outdir

    # call save_chat_log with synthesized fields
    logger.save_chat_log(
        query="What is Python?",
        config_state={"top_k": 2},
        ordered_scores=[1.0, 0.9],
        chat_request_params={"system_prompt": "baseline", "max_tokens": 200},
        top_idxs=topk,
        chunks=["Chunk 0 text", "Chunk 2 text"],
        sources=["doc1", "doc2"],
        page_map={0: 5, 2: 12},
        full_response="This is a dummy answer.",
        top_k=len(topk),
        additional_log_info={
            "raw_retriever_scores": raw_scores,
            "rank_diagnostics": rd,
            "retrieval_metrics": rm,
        },
    )

    latest = sorted(outdir.glob("chat_*.json"))[-1]
    print(f"Wrote sample log: {latest}\n")
    print(latest.read_text())


if __name__ == "__main__":
    main()
