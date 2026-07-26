from ai_takehome.rag.cost import build_cost_comparison


def test_cost_model_covers_required_scales_and_reconciles_totals() -> None:
    report = build_cost_comparison()
    rows = report["rows"]
    assert [row["vectors"] for row in rows] == [100_000, 1_000_000, 10_000_000]
    for row in rows:
        expected = (
            row["chroma_compute_usd_month"] + row["chroma_ebs_usd_month"]
        )
        assert abs(row["chroma_total_usd_month"] - expected) < 0.01
        assert row["pinecone_serverless_standard_usd_month"] >= 50

