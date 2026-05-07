# 03 — AI Document & Audio Processor

> 📄🎧 Обработка документов (PDF/изображения) и транскрибация аудио с экспортом в Excel и структурным извлечением данных.

## Что умеет

- 📄 Извлечение текста из PDF (pypdfium2) — 50 страниц/сек
- 🔍 OCR сканов PDF/изображений (pytesseract, rus+eng)
- 🎙️ Транскрибация аудио через OpenAI Whisper API
- 🧠 Структурированное извлечение полей (instructor-style) через OpenAI / GigaChat
- 📊 Экспорт в Excel (openpyxl) с отдельными листами: данные, поля, текст
- ⚙️ Фоновая очередь задач (in-process JobManager) с /status и /download
- 🖥️ CLI для обработки без веб-сервера: `python cli.py document --file invoice.pdf`

## Стек

- **API:** FastAPI + uvicorn
- **PDF:** pypdfium2 (текст), pytesseract (OCR)
- **Аудио:** OpenAI Whisper API (httpx)
- **Извлечение:** OpenAI GPT-4o-mini / GigaChat
- **Экспорт:** openpyxl
- **Чат:** CLI

## Запуск

```bash
cp .env.example .env
# fill keys or set MOCK_MODE=1
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## CLI

```bash
# Document processing
python cli.py document --file ~/invoice.pdf --extract --export
python cli.py document --file ~/scan.png --ocr
# Audio transcription
python cli.py audio --file ~/recording.mp3
# Text extraction
python cli.py text --file ~/report.txt --doc-type счёт --export
```

## Тесты

```bash
python -m pytest tests/ -v
```

## Деплой

```bash
docker compose up --build
```

## Структура

```
api/            # FastAPI endpoints (upload, status)
processors/     # pdf_text, pdf_ocr, audio_whisper, structured_extractor
exporters/      # Excel export
tasks/          # JobManager (in-process queue)
tests/          # 20 тестов
cli.py          # CLI runner
main.py         # FastAPI app
```
