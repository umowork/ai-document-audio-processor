# ROADMAP — 03 ai-document-audio-processor

## Шаг 1 — PDF pipeline

- [ ] FastAPI + Streamlit структура
- [ ] PyPDF / pypdfium2 для текстовых PDF
- [ ] Tesseract OCR fallback
- [ ] Pydantic схемы: Resume, Contract, Invoice
- [ ] GPT-4o-mini extraction через `instructor`

## Шаг 2 — Все шаблоны + кастомные схемы

- [ ] Шаблоны: Report, Medical, кастомный
- [ ] UI для создания кастомной схемы (поля + типы → Pydantic dynamic)
- [ ] Сохранение схем в БД
- [ ] Claude для длинных документов

## Шаг 3 — Audio pipeline

- [ ] Whisper API integration
- [ ] ffmpeg для конвертации форматов
- [ ] Sliding window для файлов > 25MB
- [ ] Export: TXT, SRT, VTT, DOCX
- [ ] GPT summary + action items

## Шаг 4 — Batch processing

- [ ] Загрузка ZIP / нескольких файлов
- [ ] asyncio.gather с semaphore (concurrency limit)
- [ ] Rate limiter для OpenAI
- [ ] Progress via SSE → Streamlit
- [ ] Recovery при ошибках отдельных файлов

## Шаг 5 — Excel export + диаризация

- [ ] Excel с авто-форматированием
- [ ] Один лист на тип документа
- [ ] pyannote.audio для разделения по спикерам (опционально)

## Шаг 6 — Polish + деплой

- [ ] Тесты: extraction, OCR, transcription
- [ ] Docker compose с tesseract + ffmpeg
- [ ] Deploy на Fly.io
- [ ] README с реальными метриками (точность, throughput, cost)
- [ ] Loom-демка
- [ ] Tag `v1.0.0`
