"""
CLI entry point for 03-ai-document-audio-processor.
Allows processing files directly from command line without web server.

Usage:
    python cli.py process document --file invoice.pdf
    python cli.py process audio --file recording.mp3
    python cli.py process text --file report.txt --extract
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from config import Config
from exporters.excel import ExcelExporter
from processors.audio_whisper import AudioProcessor
from processors.docx_processor import DocxProcessor
from processors.pdf_ocr import OcrProcessor
from processors.pdf_text import PdfProcessor
from processors.structured_extractor import StructuredExtractor


async def process_document(args):
    config = Config.from_env()
    pdf_proc = PdfProcessor(upload_dir=config.upload_dir)
    ocr_proc = OcrProcessor(upload_dir=config.upload_dir)
    docx_proc = DocxProcessor(upload_dir=config.upload_dir)
    extractor = StructuredExtractor(
        openai_api_key=config.openai_api_key,
        gigachat_api_key=config.gigachat_api_key,
        mock_mode=config.mock_mode,
    )
    exporter = ExcelExporter(output_dir=config.results_dir)

    content = Path(args.file).read_bytes()
    filename = Path(args.file).name

    suffix = Path(args.file).suffix.lower()
    if suffix == ".docx":
        result = await docx_proc.extract_text(filename, content)
    elif suffix in (".jpg", ".jpeg", ".png", ".webp"):
        result = await ocr_proc.ocr_image(filename, content)
    elif args.ocr:
        result = await ocr_proc.ocr_pdf(filename, content)
    else:
        result = await pdf_proc.extract_text(filename, content)

    print(f"--- {filename} ---")
    print(f"Pages: {result.page_count}")
    print(f"Text length: {len(result.text)} chars")
    print(f"Preview: {result.text[:200]}...")

    if args.extract:
        schema = await extractor.extract(result.text)
        print(f"Document type: {schema.document_type}")
        print(f"Summary: {schema.summary}")
        for field in schema.fields:
            print(f"  {field.name}: {field.value} (conf={field.confidence})")
        result.fields = schema.fields
        xlsx_path = exporter.export_document(result)
        print(f"Excel: {xlsx_path}")


async def process_audio(args):
    config = Config.from_env()
    audio_proc = AudioProcessor(
        openai_api_key=config.openai_api_key,
        upload_dir=config.upload_dir,
        mock_mode=config.mock_mode,
    )

    content = Path(args.file).read_bytes()
    filename = Path(args.file).name

    result = await audio_proc.transcribe(filename, content)
    print(f"--- {filename} ---")
    print(f"Duration: {result.duration:.1f}s")
    print(f"Segments: {len(result.segments)}")
    print(f"Full text: {result.full_text[:300]}...")
    print(f"Summary: {result.summary}")


async def process_text(args):
    config = Config.from_env()
    extractor = StructuredExtractor(
        openai_api_key=config.openai_api_key,
        gigachat_api_key=config.gigachat_api_key,
        mock_mode=config.mock_mode,
    )
    exporter = ExcelExporter(output_dir=config.results_dir)

    text = Path(args.file).read_text("utf-8", errors="replace")
    schema = await extractor.extract(text, doc_type=args.doc_type)

    print(f"--- {Path(args.file).name} ---")
    print(f"Document type: {schema.document_type}")
    print(f"Summary: {schema.summary}")
    for field in schema.fields:
        print(f"  {field.name}: {field.value} (conf={field.confidence})")

    if args.export:
        from schemas import DocumentResult
        doc = DocumentResult(
            filename=Path(args.file).name,
            text=text,
            fields=schema.fields,
            page_count=1,
        )
        xlsx_path = exporter.export_document(doc)
        print(f"Excel: {xlsx_path}")


def main():
    parser = argparse.ArgumentParser(description="Document & Audio Processor CLI")
    subparsers = parser.add_subparsers(dest="command", help="Sub-command")

    doc_parser = subparsers.add_parser("document", help="Process a document file")
    doc_parser.add_argument("--file", "-f", required=True, help="Path to document file")
    doc_parser.add_argument("--ocr", action="store_true", help="Force OCR mode")
    doc_parser.add_argument(
        "--extract", "-e", action="store_true", help="Run structured extraction"
    )

    audio_parser = subparsers.add_parser("audio", help="Transcribe an audio file")
    audio_parser.add_argument("--file", "-f", required=True, help="Path to audio file")

    text_parser = subparsers.add_parser("text", help="Extract data from text file")
    text_parser.add_argument("--file", "-f", required=True, help="Path to text file")
    text_parser.add_argument("--doc-type", "-t", help="Document type hint")
    text_parser.add_argument("--export", "-x", action="store_true", help="Export to Excel")

    args = parser.parse_args()

    if args.command == "document":
        asyncio.run(process_document(args))
    elif args.command == "audio":
        asyncio.run(process_audio(args))
    elif args.command == "text":
        asyncio.run(process_text(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
