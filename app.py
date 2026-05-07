"""
Streamlit UI for AI Document & Audio Processor.
Provides file upload, processing, and results display.

Usage:
    streamlit run app.py
"""
from __future__ import annotations

import asyncio

import streamlit as st

from config import Config
from exporters.excel import ExcelExporter
from processors.audio_whisper import AudioProcessor
from processors.docx_processor import DocxProcessor
from processors.pdf_ocr import OcrProcessor
from processors.pdf_text import PdfProcessor
from processors.structured_extractor import StructuredExtractor
from schemas import AudioResult, DocumentResult


def get_config() -> Config:
    """Get or create cached config."""
    return Config.from_env()


def run_async(coro):
    """Run an async function from sync Streamlit context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def process_document_file(
    filename: str,
    content: bytes,
    use_ocr: bool,
    config: Config,
) -> DocumentResult:
    """Process a document file (PDF, DOCX, image)."""
    pdf_proc = PdfProcessor(upload_dir=config.upload_dir)
    ocr_proc = OcrProcessor(upload_dir=config.upload_dir)
    docx_proc = DocxProcessor(upload_dir=config.upload_dir)
    extractor = StructuredExtractor(
        openai_api_key=config.openai_api_key,
        gigachat_api_key=config.gigachat_api_key,
        mock_mode=config.mock_mode,
    )

    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if suffix == "docx":
        result = run_async(docx_proc.extract_text(filename, content))
    elif suffix in ("jpg", "jpeg", "png", "webp"):
        result = run_async(ocr_proc.ocr_image(filename, content))
    elif use_ocr:
        result = run_async(ocr_proc.ocr_pdf(filename, content))
    else:
        result = run_async(pdf_proc.extract_text(filename, content))

    # Run structured extraction
    schema = run_async(extractor.extract(result.text))
    result.fields = schema.fields
    return result


def process_audio_file(
    filename: str,
    content: bytes,
    config: Config,
) -> AudioResult:
    """Transcribe an audio file."""
    audio_proc = AudioProcessor(
        openai_api_key=config.openai_api_key,
        upload_dir=config.upload_dir,
        mock_mode=config.mock_mode,
    )
    return run_async(audio_proc.transcribe(filename, content))


def main():
    st.set_page_config(
        page_title="AI Document & Audio Processor",
        page_icon="📄",
        layout="wide",
    )

    st.title("📄 AI Document & Audio Processor")
    st.caption("PDF → Excel, Audio → Text, OCR, Field Extraction")

    config = get_config()

    # Sidebar
    with st.sidebar:
        st.header("Settings")
        use_ocr = st.checkbox("Force OCR mode", value=False)
        export_excel = st.checkbox("Export to Excel", value=True)

        st.divider()
        st.subheader("Supported Formats")
        st.markdown(
            "- **Documents:** PDF, DOCX, JPG, PNG\n"
            "- **Audio:** MP3, WAV, MP4, M4A"
        )

        if config.mock_mode:
            st.info("🔧 Running in MOCK mode")

    # Main content
    tab_doc, tab_audio = st.tabs(["📄 Documents", "🎙 Audio"])

    with tab_doc:
        st.subheader("Upload Document")
        doc_file = st.file_uploader(
            "Choose a document",
            type=["pdf", "docx", "jpg", "jpeg", "png", "webp"],
            key="doc_uploader",
        )

        if doc_file is not None:
            st.info(f"📎 {doc_file.name} ({doc_file.size:,} bytes)")

            if st.button("Process Document", type="primary", key="btn_doc"):
                with st.spinner("Processing document..."):
                    content = doc_file.read()
                    result = process_document_file(
                        doc_file.name, content, use_ocr, config
                    )

                st.success(f"✅ Processed: {result.filename}")

                col1, col2, col3 = st.columns(3)
                col1.metric("Pages", result.page_count)
                col2.metric("Text Length", f"{len(result.text):,} chars")
                col3.metric("Fields Extracted", len(result.fields))

                # Extracted text
                with st.expander("📝 Extracted Text", expanded=False):
                    st.text_area(
                        "Text",
                        result.text,
                        height=300,
                        key="doc_text",
                    )

                # Extracted fields
                if result.fields:
                    st.subheader("Extracted Fields")
                    field_data = {
                        "Field": [f.name for f in result.fields],
                        "Value": [f.value for f in result.fields],
                        "Confidence": [f"{f.confidence:.0%}" for f in result.fields],
                    }
                    st.dataframe(field_data, use_container_width=True)

                # Excel export
                if export_excel and result.fields:
                    exporter = ExcelExporter(output_dir=config.results_dir)
                    xlsx_path = exporter.export_document(result)
                    with open(xlsx_path, "rb") as f:
                        st.download_button(
                            "⬇️ Download Excel",
                            f,
                            file_name=f"{result.filename}_extracted.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )

    with tab_audio:
        st.subheader("Upload Audio")
        audio_file = st.file_uploader(
            "Choose an audio file",
            type=["mp3", "wav", "mp4", "m4a", "ogg", "webm"],
            key="audio_uploader",
        )

        if audio_file is not None:
            st.info(f"📎 {audio_file.name} ({audio_file.size:,} bytes)")

            if st.button("Transcribe Audio", type="primary", key="btn_audio"):
                with st.spinner("Transcribing audio..."):
                    content = audio_file.read()
                    result = process_audio_file(audio_file.name, content, config)

                st.success(f"✅ Transcribed: {result.filename}")

                col1, col2 = st.columns(2)
                col1.metric("Duration", f"{result.duration:.1f}s")
                col2.metric("Segments", len(result.segments))

                # Full transcript
                st.subheader("Full Transcript")
                st.text_area(
                    "Transcript",
                    result.full_text,
                    height=200,
                    key="audio_text",
                )

                # Segments with timestamps
                if result.segments:
                    st.subheader("Segments")
                    seg_data = {
                        "Start": [f"{s.start:.1f}s" for s in result.segments],
                        "End": [f"{s.end:.1f}s" for s in result.segments],
                        "Text": [s.text for s in result.segments],
                    }
                    st.dataframe(seg_data, use_container_width=True)

                # Summary
                if result.summary:
                    st.subheader("Summary")
                    st.write(result.summary)


if __name__ == "__main__":
    main()
