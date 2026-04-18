from typing import Dict, List, Set, Any


def compute_retrieval_metrics(topk: List[int], golden_chunks: List[Any], topk_ks: List[int] = None) -> Dict[str, Any]:
    """Compute simple retrieval metrics (precision@k, recall@k, TP/FP/FN) given
    the returned top-k chunk indices and the golden chunks.

    golden_chunks may be a list of ints (chunk ids) or list of chunk text strings;
    callers should translate strings to indices before calling when possible.
    """
    if topk_ks is None:
        topk_ks = [1, 3, 5, 10]

    # Normalize golden set to ints if already provided as ints
    golden_set: Set[int] = set()
    for g in golden_chunks or []:
        if isinstance(g, int):
            golden_set.add(g)

    metrics: Dict[str, Any] = {
        "precision_at_k": {},
        "recall_at_k": {},
        "tp": 0,
        "fp": 0,
        "fn": 0,
    }

    if not golden_set:
        # Nothing to compare against
        return metrics

    # Compute TP/FP/FN for the full returned topk
    returned_set = set(topk)
    tp_set = returned_set & golden_set
    metrics["tp"] = len(tp_set)
    metrics["fp"] = len(returned_set - golden_set)
    metrics["fn"] = len(golden_set - returned_set)

    for k in topk_ks:
        if k > len(topk):
            continue
        topk_slice = set(topk[:k])
        prec = len(topk_slice & golden_set) / float(k) if k > 0 else 0.0
        rec = len(topk_slice & golden_set) / float(len(golden_set)) if len(golden_set) > 0 else 0.0
        metrics["precision_at_k"][k] = prec
        metrics["recall_at_k"][k] = rec

    return metrics


def compute_rank_diagnostics(raw_scores: Dict[str, Dict[int, float]], ordered_ids: List[int], topk: List[int]) -> Dict[str, Any]:
    """Produce a compact diagnostics structure describing per-retriever ranks for
    each returned candidate and the fused rank.
    """
    # Build per-retriever rank maps
    per_retriever_ranks = {}
    for retriever, scores in (raw_scores or {}).items():
        # sort by score descending
        sorted_ids = sorted(scores.keys(), key=lambda i: scores.get(i, 0), reverse=True)
        ranks = {idx: rank for rank, idx in enumerate(sorted_ids, start=1)}
        per_retriever_ranks[retriever] = ranks

    fused_ranks = {idx: rank for rank, idx in enumerate(ordered_ids, start=1)}

    entries = []
    for pos, idx in enumerate(topk, start=1):
        entry = {
            "fused_rank": fused_ranks.get(idx, None),
            "chunk_id": int(idx),
            "per_retriever_ranks": {},
        }
        for retriever, ranks in per_retriever_ranks.items():
            entry["per_retriever_ranks"][retriever] = ranks.get(idx, None)

        entries.append(entry)

    return {
        "per_retriever_ranks": per_retriever_ranks,
        "fused_ranks": fused_ranks,
        "returned": entries,
    }
