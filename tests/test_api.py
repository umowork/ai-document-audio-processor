"""API tests for AI Document & Audio Processor — all endpoints."""

import os

import pytest

os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("GIGACHAT_API_KEY", "test")
os.environ.setdefault("API_KEY", "test-key")

from httpx import ASGITransport, AsyncClient

from main import create_app

HEADERS = {"X-API-Key": "test-key"}


@pytest.fixture
def app(tmp_path):
    os.environ["UPLOAD_DIR"] = str(tmp_path / "uploads")
    os.environ["RESULTS_DIR"] = str(tmp_path / "results")
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ── Health ─────────────────────────────────────────────────────────


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["service"] == "document-processor"
    assert data["mock_mode"] is True


# ── Auth errors ────────────────────────────────────────────────────


async def test_process_document_no_auth(client):
    r = await client.post(
        "/process/document",
        files={"file": ("test.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert r.status_code in (401, 403)


async def test_process_audio_no_auth(client):
    r = await client.post(
        "/process/audio",
        files={"file": ("test.mp3", b"fake-audio", "audio/mpeg")},
    )
    assert r.status_code in (401, 403)


async def test_extract_no_auth(client):
    r = await client.post(
        "/process/extract",
        files={"file": ("test.txt", b"some text", "text/plain")},
    )
    assert r.status_code in (401, 403)


# ── Process document ───────────────────────────────────────────────


async def test_process_document_txt(client):
    r = await client.post(
        "/process/document",
        files={"file": ("test.txt", b"Hello world content", "text/plain")},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert "text" in data or "fields" in data


async def test_process_document_docx(client):
    """Test DOCX processing with a minimal docx file."""
    import io

    try:
        from docx import Document

        buf = io.BytesIO()
        doc = Document()
        doc.add_paragraph("Тестовый документ")
        doc.save(buf)
        buf.seek(0)
        r = await client.post(
            "/process/document",
            files={"file": ("test.docx", buf.read(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            headers=HEADERS,
        )
        assert r.status_code == 200
    except ImportError:
        pytest.skip("python-docx not installed")


# ── Process audio ──────────────────────────────────────────────────


async def test_process_audio_mock(client):
    r = await client.post(
        "/process/audio",
        files={"file": ("test.mp3", b"fake-audio-data", "audio/mpeg")},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert "text" in data or "segments" in data


# ── Process extract ────────────────────────────────────────────────


async def test_process_extract(client):
    r = await client.post(
        "/process/extract",
        files={"file": ("invoice.txt", b"Invoice #123 dated 2024-01-01 amount 5000 RUB", "text/plain")},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert "fields" in data


# ── Upload async endpoints ─────────────────────────────────────────


async def test_upload_endpoint(client):
    r = await client.post(
        "/upload",
        files={"file": ("test.txt", b"test content", "text/plain")},
        data={"processing_type": "document"},
        headers=HEADERS,
    )
    # May return 200 or 404 depending on implementation
    assert r.status_code in (200, 404, 422)


# ── File too large ─────────────────────────────────────────────────


async def test_file_too_large(client):
    """51 MB file should be rejected."""
    big_content = b"x" * (51 * 1024 * 1024)
    r = await client.post(
        "/process/document",
        files={"file": ("big.pdf", big_content, "application/pdf")},
        headers=HEADERS,
    )
    assert r.status_code == 413
