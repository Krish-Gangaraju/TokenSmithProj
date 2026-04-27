from src.citations import build_citation_context, verify_and_repair_citations


def test_build_citation_context_maps_labels_to_chunks_and_pages():
    cited_chunks, citation_map = build_citation_context(
        chunks=["Chunk zero text", "Chunk two text"],
        chunk_ids=[0, 2],
        sources=["doc-a", "doc-b", "doc-c"],
        page_map={0: [4], 2: [9, 10]},
    )

    assert cited_chunks[0].startswith("[C1 | chunk 0 | pages 4]")
    assert "Chunk zero text" in cited_chunks[0]
    assert cited_chunks[1].startswith("[C2 | chunk 2 | pages 9, 10]")
    assert citation_map == [
        {"label": "C1", "chunk_id": 0, "source": "doc-a", "pages": [4]},
        {"label": "C2", "chunk_id": 2, "source": "doc-c", "pages": [9, 10]},
    ]


def test_verify_and_repair_citations_removes_invalid_labels():
    citation_map = [
        {"label": "C1", "chunk_id": 0, "source": "doc-a", "pages": [4]},
    ]

    answer, verification = verify_and_repair_citations(
        "Databases store data [C1]. This unsupported marker is invalid [C99].",
        citation_map,
    )

    assert "[C1]" in answer
    assert "[C99]" not in answer
    assert verification["valid"] is True
    assert verification["repaired"] is True
    assert verification["invalid_citations"] == ["C99"]
    assert verification["mapped_citations"] == citation_map


def test_verify_and_repair_citations_adds_valid_default_when_missing():
    citation_map = [
        {"label": "C1", "chunk_id": 0, "source": "doc-a", "pages": [4]},
    ]

    answer, verification = verify_and_repair_citations(
        "Databases store structured data.",
        citation_map,
    )

    assert answer.endswith("[C1]")
    assert verification["valid"] is True
    assert verification["repaired"] is True
    assert verification["used_citations"] == ["C1"]
    assert verification["mapped_citations"] == citation_map
