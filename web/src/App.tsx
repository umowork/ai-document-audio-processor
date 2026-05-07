import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';

const API = '/api';

export default function App() {
  const [tab, setTab] = useState<'document' | 'audio'>('document');
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<string>('');
  const [loading, setLoading] = useState(false);

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    const form = new FormData();
    form.append('file', file);
    const endpoint = tab === 'document' ? `${API}/process/document` : `${API}/process/audio`;
    try {
      const r = await fetch(endpoint, { method: 'POST', body: form });
      const data = await r.json();
      setResult(JSON.stringify(data, null, 2));
    } catch (e: any) {
      setResult(`Ошибка: ${e.message}`);
    }
    setLoading(false);
  };

  return (
    <div style={{ maxWidth: 700, margin: '0 auto', padding: 24, fontFamily: '-apple-system, sans-serif' }}>
      <h1 style={{ fontSize: 24, marginBottom: 8 }}>📋 Document & Audio Processor</h1>
      <p style={{ color: '#666', marginBottom: 32 }}>OCR + Транскрипция + Извлечение данных</p>

      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        <button onClick={() => setTab('document')}
          style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid #e5e7eb',
            background: tab === 'document' ? '#2563eb' : '#fff',
            color: tab === 'document' ? '#fff' : '#000', cursor: 'pointer' }}>
          📄 Документы
        </button>
        <button onClick={() => setTab('audio')}
          style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid #e5e7eb',
            background: tab === 'audio' ? '#2563eb' : '#fff',
            color: tab === 'audio' ? '#fff' : '#000', cursor: 'pointer' }}>
          🎵 Аудио
        </button>
      </div>

      <div style={{ border: '2px dashed #e5e7eb', borderRadius: 12, padding: 32, textAlign: 'center' }}>
        <input type="file" onChange={e => setFile(e.target.files?.[0] || null)}
          style={{ marginBottom: 16 }} />
        <br />
        <button onClick={handleUpload} disabled={!file || loading}
          style={{ background: loading ? '#9ca3af' : '#2563eb', color: 'white',
            border: 'none', borderRadius: 8, padding: '10px 24px', cursor: 'pointer' }}>
          {loading ? 'Обработка...' : 'Загрузить и обработать'}
        </button>
      </div>

      {result && (
        <div style={{ background: '#f3f4f6', borderRadius: 8, padding: 16, marginTop: 24 }}>
          <pre style={{ fontSize: 13, whiteSpace: 'pre-wrap', margin: 0 }}>{result}</pre>
        </div>
      )}
    </div>
  );
}
