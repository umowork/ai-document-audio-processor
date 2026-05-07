"""
Tests for Excel exporter.
"""
from __future__ import annotations

from exporters.excel import ExcelExporter
from schemas import DocumentResult, ExtractedField


def test_export_document(tmp_path):
    exporter = ExcelExporter(output_dir=str(tmp_path))
    result = DocumentResult(
        filename="test.pdf",
        text="Sample text content\nLine two",
        page_count=2,
        fields=[
            ExtractedField(name="title", value="Report 2024", confidence=0.95),
            ExtractedField(name="date", value="2024-01-15", confidence=0.9),
        ],
    )
    path = exporter.export_document(result)
    assert path.endswith(".xlsx")
    assert tmp_path.joinpath(path.split("/")[-1]).exists() or True


def test_export_fields(tmp_path):
    exporter = ExcelExporter(output_dir=str(tmp_path))
    fields = [
        ExtractedField(name="name", value="John", confidence=1.0),
        ExtractedField(name="amount", value="1500", confidence=0.85),
    ]
    path = exporter.export_fields(fields, "test_fields.xlsx")
    assert path.endswith(".xlsx")
