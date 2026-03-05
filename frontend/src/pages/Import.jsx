import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { api } from '../services/api';

const BANK_PRESETS = [
  { value: '',          label: 'Detectar automaticamente' },
  { value: 'nubank',    label: '🟣 Nubank' },
  { value: 'itau',      label: '🟠 Itaú' },
  { value: 'bradesco',  label: '🔴 Bradesco' },
  { value: 'santander', label: '🔴 Santander' },
];

function Step({ number, title, active, done }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, opacity: done || active ? 1 : 0.4, transition: 'opacity 300ms' }}>
      <div style={{
        width: 32, height: 32, borderRadius: '50%',
        background: done ? 'var(--color-income)' : active ? 'var(--color-primary)' : 'var(--bg-elevated)',
        border: `2px solid ${done ? 'var(--color-income)' : active ? 'var(--color-primary)' : 'var(--border-subtle)'}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 14, fontWeight: 700, color: done || active ? 'white' : 'var(--text-muted)',
        transition: 'all 300ms', flexShrink: 0,
      }}>
        {done ? '✓' : number}
      </div>
      <span style={{ fontSize: 14, fontWeight: active ? 600 : 400, color: active ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
        {title}
      </span>
    </div>
  );
}

function DropZoneArea({ onFileDrop, accept, label }) {
  const [isDragActive, setIsDragActive] = useState(false);
  const onDrop = useCallback(files => { if (files[0]) onFileDrop(files[0]); }, [onFileDrop]);
  const { getRootProps, getInputProps } = useDropzone({
    onDrop,
    accept,
    multiple: false,
    onDragEnter: () => setIsDragActive(true),
    onDragLeave: () => setIsDragActive(false),
  });

  return (
    <div {...getRootProps()} className={`drop-zone ${isDragActive ? 'active' : ''}`}>
      <input {...getInputProps()} />
      <div className="drop-zone-icon">📂</div>
      <p className="drop-zone-title">{label}</p>
      <p className="drop-zone-sub">Arraste aqui ou clique para selecionar</p>
    </div>
  );
}

export default function Import() {
  const [tab, setTab]           = useState('ofx'); // 'ofx' | 'csv'
  const [file, setFile]         = useState(null);
  const [accountId, setAccountId] = useState('demo-account-001');
  const [bankPreset, setBankPreset] = useState('');
  const [step, setStep]         = useState(1);   // 1=select, 2=confirm, 3=done
  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState(null);
  const [error, setError]       = useState(null);

  const handleFile = (f) => {
    setFile(f);
    setStep(2);
    setResult(null);
    setError(null);
  };

  const handleImport = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      let res;
      if (tab === 'ofx') {
        res = await api.import.ofx(file, accountId);
      } else {
        res = await api.import.csv(file, accountId, bankPreset || undefined);
      }
      setResult(res);
      setStep(3);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setFile(null);
    setResult(null);
    setError(null);
    setStep(1);
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Importar Extrato</h1>
        <p className="page-subtitle">Importe seu extrato bancário (OFX ou CSV) com privacidade total</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 24, alignItems: 'start' }}>
        {/* Steps sidebar */}
        <div className="card">
          <p style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)', marginBottom: 20 }}>
            Progresso
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <Step number={1} title="Selecionar arquivo" active={step === 1} done={step > 1} />
            <Step number={2} title="Confirmar importação" active={step === 2} done={step > 2} />
            <Step number={3} title="Concluído!" active={step === 3} done={false} />
          </div>

          <div style={{ marginTop: 28, paddingTop: 20, borderTop: '1px solid var(--border-subtle)' }}>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6 }}>
              🔒 <strong>Seus dados ficam locais.</strong> Nenhuma informação é enviada para servidores externos.
            </p>
          </div>
        </div>

        {/* Main area */}
        <div>
          {step === 1 && (
            <div className="card">
              {/* Tabs */}
              <div style={{ display: 'flex', gap: 4, marginBottom: 24, background: 'var(--bg-elevated)', borderRadius: 10, padding: 4 }}>
                {['ofx', 'csv'].map(t => (
                  <button key={t} onClick={() => { setTab(t); reset(); }}
                    style={{
                      flex: 1, padding: '8px 16px', borderRadius: 7, border: 'none',
                      background: tab === t ? 'var(--color-primary)' : 'transparent',
                      color: tab === t ? 'white' : 'var(--text-muted)',
                      fontWeight: 600, fontSize: 14, cursor: 'pointer',
                      transition: 'all 200ms',
                    }}>
                    {t === 'ofx' ? '📄 OFX / QFX' : '📊 CSV'}
                  </button>
                ))}
              </div>

              {tab === 'ofx' ? (
                <DropZoneArea
                  onFileDrop={handleFile}
                  accept={{ 'application/x-ofx': ['.ofx', '.qfx'], 'application/octet-stream': ['.ofx', '.qfx'] }}
                  label="Arquivo OFX ou QFX"
                />
              ) : (
                <>
                  <div className="form-group" style={{ marginBottom: 16 }}>
                    <label className="form-label">Banco</label>
                    <select className="input" value={bankPreset} onChange={e => setBankPreset(e.target.value)}>
                      {BANK_PRESETS.map(b => (
                        <option key={b.value} value={b.value}>{b.label}</option>
                      ))}
                    </select>
                  </div>
                  <DropZoneArea
                    onFileDrop={handleFile}
                    accept={{ 'text/csv': ['.csv'], 'text/plain': ['.csv', '.txt'] }}
                    label="Arquivo CSV do banco"
                  />
                </>
              )}

              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 16, textAlign: 'center' }}>
                Formatos suportados: {tab === 'ofx' ? '.ofx, .qfx (OFX v1 e v2)' : '.csv (UTF-8, Latin-1)'}
              </p>
            </div>
          )}

          {step === 2 && file && (
            <div className="card">
              <p className="chart-title" style={{ marginBottom: 20 }}>Confirmar importação</p>

              <div style={{ background: 'var(--bg-elevated)', borderRadius: 10, padding: 20, marginBottom: 20 }}>
                <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                  <div style={{ fontSize: 40 }}>{tab === 'ofx' ? '📄' : '📊'}</div>
                  <div>
                    <p style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{file.name}</p>
                    <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>
                      {(file.size / 1024).toFixed(1)} KB · {tab.toUpperCase()}
                    </p>
                  </div>
                </div>
              </div>

              <div className="form-group" style={{ marginBottom: 20 }}>
                <label className="form-label">ID da conta</label>
                <input className="input" value={accountId} onChange={e => setAccountId(e.target.value)} placeholder="ID da conta bancária" />
              </div>

              {error && (
                <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 8, padding: '12px 16px', marginBottom: 16, color: 'var(--color-danger)', fontSize: 14 }}>
                  ⚠️ {error}
                </div>
              )}

              <div style={{ display: 'flex', gap: 12 }}>
                <button className="btn btn-ghost" onClick={reset}>← Voltar</button>
                <button className="btn btn-primary" onClick={handleImport} disabled={loading} style={{ flex: 1 }}>
                  {loading ? '⏳ Importando...' : '✓ Importar Agora'}
                </button>
              </div>
            </div>
          )}

          {step === 3 && result && (
            <div className="card" style={{ textAlign: 'center', padding: '48px 32px' }}>
              {/* Animated checkmark */}
              <div style={{ fontSize: 64, marginBottom: 20, animation: 'fadeIn 400ms ease' }}>✅</div>
              <p style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8 }}>
                Importação concluída!
              </p>
              <p style={{ color: 'var(--text-secondary)', marginBottom: 24, fontSize: 15 }}>
                {result.message}
              </p>
              <div style={{ display: 'flex', gap: 20, justifyContent: 'center', marginBottom: 32 }}>
                <div style={{ textAlign: 'center' }}>
                  <p style={{ fontSize: 32, fontWeight: 800, color: 'var(--color-income)' }}>
                    {result.imported_count}
                  </p>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>Importadas</p>
                </div>
                <div style={{ width: 1, background: 'var(--border-subtle)' }} />
                <div style={{ textAlign: 'center' }}>
                  <p style={{ fontSize: 32, fontWeight: 800, color: 'var(--color-expense)' }}>
                    {result.skipped_count}
                  </p>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>Duplicatas ignoradas</p>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
                <button className="btn btn-ghost" onClick={reset}>Importar outro arquivo</button>
                <a href="/transactions" className="btn btn-primary">Ver Transações →</a>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
