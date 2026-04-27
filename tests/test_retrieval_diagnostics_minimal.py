import argparse
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.ranking.ranker import EnsembleRanker
from src.instrumentation.logging import RunLogger


class MinimalConfig(SimpleNamespace):
    def get_config_state(self):
        return self.__dict__.copy()


class MockRetriever:
    def __init__(self, name, scores):
        self.name = name
        self.scores = scores

    def get_scores(self, query, pool_size, chunks):
        return self.scores


def test_retrieval_diagnostics_minimal(tmp_path, monkeypatch):
    """Lightweight test that runs retrieval and checks the saved log contains diagnostics."""
    from src.main import get_answer

    cfg = MinimalConfig(
        top_k=2,
        num_candidates=5,
        ensemble_method="linear",
        ranker_weights={"faiss": 0.5, "bm25": 0.5},
        chunk_mode="recursive_sections",
        use_hyde=False,
        disable_chunks=False,
        rerank_mode="none",
        rerank_top_k=2,
        use_golden_chunks=True,
        use_indexed_chunks=False,
        gen_model="mock-model.gguf",
        max_gen_tokens=20,
        system_prompt_mode="baseline",
        use_double_prompt=False,
    )

    args = argparse.Namespace(system_prompt_mode="baseline", index_prefix="test_index")

    # Setup Dummy Data
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

    retrievers = [MockRetriever("faiss", faiss_scores), MockRetriever("bm25", bm25_scores)]

    ranker = EnsembleRanker(ensemble_method="linear", weights={"faiss": 0.5, "bm25": 0.5})

    artifacts = {"chunks": chunks, "sources": sources, "retrievers": retrievers, "ranker": ranker, "meta": [{"page_numbers": [1]} for _ in chunks]}

    # Mock the generator to avoid model loads
    def mock_stream_generator(*args, **kwargs):
        yield "Answer part A "
        yield "Answer part B"

    with patch("src.main.answer", side_effect=lambda *a, **k: mock_stream_generator()):
        # Put logs into a temp logs dir by monkeypatching RunLogger.logs_dir
        run_logger = RunLogger()
        tmp_logs = tmp_path / "logs"
        tmp_logs.mkdir()
        run_logger.logs_dir = tmp_logs

        # Call get_answer with golden chunk ids [0,2], but keep retrieval enabled
        # so diagnostics compare actual retrieved ids against the benchmark ids.
        cfg.use_golden_chunks = False
        ans_prod = get_answer(
            question="What is Python?",
            cfg=cfg,
            args=args,
            logger=run_logger,
            console=MagicMock(),
            artifacts=artifacts,
            golden_chunks=[0, 2],
            is_test_mode=False,
        )

        # Read most recent log file
        logs = list(tmp_logs.glob("chat_*.json"))
        assert logs, "No log files written"
        latest = sorted(logs)[-1]
        payload = json.loads(latest.read_text())

        # Validate diagnostics present
        assert "retrieved_chunks" in payload
        assert "raw_retriever_scores" in payload
        assert "rank_diagnostics" in payload
        assert "retrieval_metrics" in payload
        assert payload["retrieval_metrics"]["tp"] == 2
        assert payload["retrieval_metrics"]["fp"] == 0
        assert payload["retrieval_metrics"]["fn"] == 0
        assert payload["retrieval_metrics"]["precision_at_k"]["1"] == 1.0
        assert payload["retrieval_metrics"]["recall_at_k"]["1"] == 0.5
        assert payload["rank_diagnostics"]["returned"][0]["chunk_id"] in [0, 2]
