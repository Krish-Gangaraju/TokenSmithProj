import re
from typing import Any, Dict, List, Tuple


_CITATION_RE = re.compile(r"\[C(\d+)\]")


def build_citation_context(
    chunks: List[str],
    chunk_ids: List[int],
    sources: List[str],
    page_map: Dict[int, Any],
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Label retrieved chunks with stable citation ids for generation."""
    cited_chunks: List[str] = []
    citation_map: List[Dict[str, Any]] = []

    for position, (chunk, chunk_id) in enumerate(zip(chunks, chunk_ids), start=1):
        chunk_id = int(chunk_id)
        pages = page_map.get(chunk_id, [1])
        if isinstance(pages, int):
            pages = [pages]
        if not pages:
            pages = [1]

        label = f"C{position}"
        source = sources[chunk_id] if chunk_id < len(sources) else None
        citation_map.append({
            "label": label,
            "chunk_id": chunk_id,
            "source": source,
            "pages": [int(page) for page in pages],
        })

        page_text = ", ".join(str(page) for page in pages)
        cited_chunks.append(
            f"[{label} | chunk {chunk_id} | pages {page_text}]\n{chunk}"
        )

    return cited_chunks, citation_map


def verify_and_repair_citations(
    answer: str,
    citation_map: List[Dict[str, Any]],
) -> Tuple[str, Dict[str, Any]]:
    """Ensure every citation marker in the answer maps to a retrieved chunk."""
    valid_labels = {entry["label"] for entry in citation_map}
    invalid_labels: List[str] = []
    repaired = False

    def replace_marker(match: re.Match) -> str:
        nonlocal repaired
        label = f"C{match.group(1)}"
        if label in valid_labels:
            return match.group(0)
        invalid_labels.append(label)
        repaired = True
        return ""

    cleaned = _CITATION_RE.sub(replace_marker, answer).strip()
    used_labels = [f"C{match}" for match in _CITATION_RE.findall(cleaned)]

    if citation_map and not used_labels and cleaned:
        cleaned = _append_default_citation(cleaned, citation_map[0]["label"])
        used_labels = [citation_map[0]["label"]]
        repaired = True

    unique_used = []
    for label in used_labels:
        if label not in unique_used:
            unique_used.append(label)

    citation_lookup = {entry["label"]: entry for entry in citation_map}
    mapped_citations = [
        citation_lookup[label]
        for label in unique_used
        if label in citation_lookup
    ]
    final_labels_are_valid = all(label in valid_labels for label in unique_used)

    verification = {
        "valid": final_labels_are_valid,
        "repaired": repaired,
        "invalid_citations": invalid_labels,
        "used_citations": unique_used,
        "mapped_citations": mapped_citations,
        "citation_map": citation_map,
    }
    return cleaned, verification


def _append_default_citation(answer: str, label: str) -> str:
    if answer.endswith((".", "!", "?")):
        return f"{answer} [{label}]"
    return f"{answer} [{label}]"
