#!/usr/bin/env python3
"""Minimal runner to exercise retrieval diagnostics and logging without pytest.
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Make sure project root is on sys.path when running this script directly
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Avoid importing full RAGConfig (pulls heavy optional deps). Use a lightweight config object.
class DummyCfg:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get_config_state(self):
        # Return a minimal serializable config state
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

from src.ranking.ranker import EnsembleRanker
from src.instrumentation.logging import RunLogger


def main():
    cfg = DummyCfg(
        top_k=2,
        num_candidates=5,
        ensemble_method="linear",
        ranker_weights={"faiss": 0.5, "bm25": 0.5},
        chunk_mode="recursive_sections",
        use_hyde=False,
        disable_chunks=False,
        rerank_mode="none",
        use_golden_chunks=True,
    )

    args = MagicMock()
    args.system_prompt_mode = "baseline"
    args.index_prefix = "test_index"

    # Dummy chunks and scores
    chunks = [
        "Chunk 0: Python is a programming language.",
        "Chunk 1: The sky is blue.",
        "Chunk 2: Machine learning uses statistics.",
        "Chunk 3: Databases store data.",
        "Chunk 4: API stands for Application Programming Interface.",
    ]
    sources = ["doc1", "doc1", "doc2", "doc3", "doc4"]

    faiss_scores = {0: 0.9, 2: 0.8, 1: 0.1, 3: 0.05, 4: 0.05}
    bm25_scores = {0: 0.8, 2: 0.9, 3: 0.2, 1: 0.05, 4: 0.05}

    class MockRetriever:
        def __init__(self, name, scores):
            self.name = name
            self.scores = scores

        def get_scores(self, query, pool_size, chunks):
            return self.scores

    retrievers = [MockRetriever("faiss", faiss_scores), MockRetriever("bm25", bm25_scores)]
    ranker = EnsembleRanker(ensemble_method="linear", weights={"faiss": 0.5, "bm25": 0.5})

    artifacts = {
        "chunks": chunks,
        "sources": sources,
        "retrievers": retrievers,
        "ranker": ranker,
        "meta": [{"page_numbers": [1]} for _ in chunks],
    }

    # Mock generator to avoid loading model
    def mock_stream_generator(*a, **k):
        yield "Answer part A "
        yield "Answer part B"

    # Import main module and temporarily replace the answer generator to avoid model loads
    import importlib
    main_mod = importlib.import_module("src.main")
    original_answer = getattr(main_mod, "answer", None)
    try:
        main_mod.answer = lambda *a, **k: mock_stream_generator()

        logger = RunLogger()
        # Put logs into a local temp folder 'logs/minimal_test'
        logdir = Path("logs") / "minimal_test"
        logdir.mkdir(parents=True, exist_ok=True)
        logger.logs_dir = logdir

        # Call get_answer with golden chunk ids
        from src.main import get_answer

        ans = get_answer(
            question="What is Python?",
            cfg=cfg,
            args=args,
            logger=logger,
            console=MagicMock(),
            artifacts=artifacts,
            golden_chunks=[0, 2],
            is_test_mode=False,
        )

        print("Generated answer:\n", ans)

        logs = sorted(logdir.glob("chat_*.json"))
        if not logs:
            print("No logs written")
            return

        latest = logs[-1]
        payload = json.loads(latest.read_text())
        print(f"Wrote log: {latest}")
        print(json.dumps(payload, indent=2))
    finally:
        # restore
        if original_answer is not None:
            main_mod.answer = original_answer


if __name__ == "__main__":
    main()
