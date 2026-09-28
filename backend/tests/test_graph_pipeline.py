"""Integration test verifying graph pipeline execution with normalize and validate."""

from app.ai.graph import app_graph


def test_graph_pipeline_execution():
    result = app_graph.invoke({"prompt": "find 2 backpacks under 50"})
    assert result.get("status") == "READY"
    final_records = result.get("final_records", [])
    assert len(final_records) > 0

    first = final_records[0]
    # Check normalized properties
    assert "_raw" in first
    assert "_notes" in first
    assert "_issues" in first
    assert "_is_valid" in first
    assert "_source_url" in first
    assert "_fetched_at" in first
    assert isinstance(first.get("price"), (int, float))
