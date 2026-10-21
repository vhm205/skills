import { useCallback, useEffect, useRef, useState } from 'react';
import type { Artifact, Feature, CopilotModel } from '../src/types';
import type { CopilotContext, ContextSource, ProviderStatus } from '../src/copilot';
import { api, featurePath, fetchCopilotModels, type FeatureResponse } from './api';
import { Markdown } from './Markdown';
import type { SourceSelection } from './Source';

interface Settings { provider: string; model: string; endpoint: string; hasKey: boolean }
interface Answer { question: string; answer: string; revision: string; sources: ContextSource[]; warnings: string[]; provider: string; digest: string }

interface PendingTurn {
  question: string;
  statusText: string;
  startTime: number;
}

interface StreamingTurn extends Answer {
  streamedLength: number;
}

interface Preset {
  label: string;
  provider: string;
  endpoint: string;
  defaultModel?: string;
  badge?: string;
}

const PRESETS: Preset[] = [
  { label: 'Antigravity CLI', provider: 'antigravity', endpoint: '', badge: 'Local CLI' },
  { label: 'Ollama (Local)', provider: 'api', endpoint: 'http://localhost:11434/v1', badge: 'Local AI' },
  { label: 'LM Studio', provider: 'api', endpoint: 'http://localhost:1234/v1', badge: 'Local AI' },
  { label: 'OpenAI', provider: 'api', endpoint: 'https://api.openai.com/v1', defaultModel: 'gpt-4o' },
  { label: 'Gemini (OpenAI API)', provider: 'api', endpoint: 'https://generativelanguage.googleapis.com/v1beta/openai/', defaultModel: 'gemini-1.5-pro' },
  { label: 'OpenRouter', provider: 'api', endpoint: 'https://openrouter.ai/api/v1' },
  { label: 'DeepSeek', provider: 'api', endpoint: 'https://api.deepseek.com/v1', defaultModel: 'deepseek-chat' },
  { label: 'Groq', provider: 'api', endpoint: 'https://api.groq.com/openai/v1', defaultModel: 'llama-3.3-70b-versatile' },
];

export function CopilotPanel({ feature, contextDocs, source, contextEpoch }: { feature: Feature; contextDocs: Artifact[]; source: (selection: SourceSelection) => void; contextEpoch: number }) {
  const [settings, setSettings] = useState<Settings>({ provider: 'antigravity', model: '', endpoint: '', hasKey: false });
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [key, setKey] = useState('');
  const [configured, setConfigured] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [scope, setScope] = useState<'feature' | 'project'>('feature');
  const [paths, setPaths] = useState(feature.artifacts.filter(a => ['spec.md', 'plan.md', 'tasks.md'].includes(a.path)).map(a => a.path));
  const [context, setContext] = useState<CopilotContext | null>(null);
  const [contextLoading, setContextLoading] = useState(false);
  const [contextTick, setContextTick] = useState(0);
  const [question, setQuestion] = useState('');
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [handoff, setHandoff] = useState('');
  const [pendingTurn, setPendingTurn] = useState<PendingTurn | null>(null);
  const [streaming, setStreaming] = useState<StreamingTurn | null>(null);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  // Auto-fetch models state
  const [models, setModels] = useState<CopilotModel[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState('');

  const request = useRef<AbortController | null>(null);
  const keyDebounce = useRef<NodeJS.Timeout | null>(null);
  const streamIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const statusIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (pendingTurn || streaming || answers.length) {
      chatBottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [pendingTurn, streaming?.streamedLength, answers.length]);

  useEffect(() => {
    return () => {
      if (streamIntervalRef.current) clearInterval(streamIntervalRef.current);
      if (statusIntervalRef.current) clearInterval(statusIntervalRef.current);
    };
  }, []);

  const fetchModels = useCallback(async (prov: string, ep: string, apiKey: string, isManual = false) => {
    setModelsLoading(true);
    if (isManual) setModelsError('');
    try {
      const res = await fetchCopilotModels(prov, ep || undefined, apiKey || undefined);
      setModels(res.models || []);
      if (res.models?.length > 0) {
        setSettings(s => (s.model ? s : { ...s, model: res.models[0].id }));
      }
    } catch (err) {
      if (isManual) {
        setModelsError((err as Error).message);
      }
    } finally {
      setModelsLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void api<{ settings: Settings; providers: ProviderStatus[] }>('/api/copilot', undefined, controller.signal).then(data => {
      setSettings(data.settings);
      setProviders(data.providers);
      const isConfigured = data.settings.provider !== 'api' || !!data.settings.model;
      setConfigured(isConfigured);
      setSettingsOpen(!isConfigured);
      // Fetch models initially for the current provider
      void fetchModels(data.settings.provider, data.settings.endpoint, '');
    }).catch(e => {
      if (e.name !== 'AbortError') setError(e.message);
    });
    return () => { controller.abort(); request.current?.abort(); };
  }, []);

  const pathKey = JSON.stringify(paths);
  useEffect(() => {
    const controller = new AbortController();
    setContextLoading(true);
    setContext(null);
    setHandoff('');
    void api<CopilotContext>(featurePath(feature.id) + '/context', { scope, paths: JSON.parse(pathKey) }, controller.signal)
      .then(setContext)
      .catch(e => { if (e.name !== 'AbortError') setError(e.message); })
      .finally(() => { if (!controller.signal.aborted) setContextLoading(false); });
    return () => controller.abort();
  }, [feature.id, feature.revision, scope, pathKey, contextTick, contextEpoch]);

  const handleKeyChange = (val: string) => {
    setKey(val);
    setConfigured(false);
    if (keyDebounce.current) clearTimeout(keyDebounce.current);
    keyDebounce.current = setTimeout(() => {
      if (val.trim().length > 3 || ['127.0.0.1', 'localhost'].some(h => settings.endpoint.includes(h))) {
        void fetchModels(settings.provider, settings.endpoint, val.trim());
      }
    }, 600);
  };

  const applyPreset = (preset: Preset) => {
    const ep = preset.provider === 'api' ? (preset.endpoint || 'https://api.openai.com/v1') : '';
    const newSettings: Settings = {
      ...settings,
      provider: preset.provider,
      endpoint: ep,
      model: preset.defaultModel || ''
    };
    setSettings(newSettings);
    setConfigured(preset.provider !== 'api' || !!newSettings.model);
    void fetchModels(preset.provider, ep, key);
    void api<Settings>('/api/copilot/config', { ...newSettings, apiKey: key || undefined }).catch(() => undefined);
  };

  async function save() {
    setError(''); setMessage('');
    try {
      const value = await api<Settings>('/api/copilot/config', { ...settings, apiKey: key || undefined });
      setSettings(value);
      setKey('');
      setConfigured(true);
      setSettingsOpen(false);
      setMessage('Kết nối đã cấu hình cho phiên server này. Đã sẵn sàng tư vấn từ docs.');
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function forget() {
    try {
      const value = await api<Settings>('/api/copilot/config', { provider: 'api', model: '', endpoint: 'https://api.openai.com/v1', apiKey: '' });
      setSettings(value);
      setKey('');
      setConfigured(false);
      setModels([]);
      setMessage('Đã xóa key và cấu hình khỏi bộ nhớ server.');
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const finishStreaming = useCallback(() => {
    if (streamIntervalRef.current) clearInterval(streamIntervalRef.current);
    setStreaming(curr => {
      if (curr) {
        const finished: Answer = {
          question: curr.question,
          answer: curr.answer,
          revision: curr.revision,
          sources: curr.sources,
          warnings: curr.warnings,
          provider: curr.provider,
          digest: curr.digest
        };
        setAnswers(old => [...old, finished].slice(-20));
      }
      return null;
    });
    setBusy(false);
  }, []);

  const cancelAsk = useCallback(() => {
    request.current?.abort();
    void api('/api/copilot/cancel', {}).catch(() => undefined);
    if (statusIntervalRef.current) clearInterval(statusIntervalRef.current);
    if (streamIntervalRef.current) clearInterval(streamIntervalRef.current);
    if (pendingTurn) {
      setQuestion(pendingTurn.question);
    }
    setPendingTurn(null);
    setStreaming(null);
    setBusy(false);
  }, [pendingTurn]);

  const copyAnswer = useCallback((index: number, text: string) => {
    void navigator.clipboard.writeText(text).then(() => {
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    });
  }, []);

  async function ask() {
    if (!context || busy || !question.trim()) return;
    const input = question.trim();
    const captured = context;
    setBusy(true); setError(''); setMessage('');
    setQuestion('');

    const startTime = Date.now();
    const provLabel = settings.provider === 'antigravity' ? 'Antigravity CLI' : settings.provider.toUpperCase();
    const initialStatus = `Đang kết nối ${provLabel}…`;
    setPendingTurn({ question: input, statusText: initialStatus, startTime });

    if (statusIntervalRef.current) clearInterval(statusIntervalRef.current);
    statusIntervalRef.current = setInterval(() => {
      const elapsed = Date.now() - startTime;
      let nextStatus = initialStatus;
      if (elapsed > 12000) {
        nextStatus = 'Đang hoàn thiện phản hồi chi tiết từ tài liệu…';
      } else if (elapsed > 6000) {
        nextStatus = 'Đang đối chiếu thông tin và tổng hợp câu trả lời…';
      } else if (elapsed > 2000) {
        nextStatus = `Đang đọc ${captured.sources.length} tài liệu specs và kiểm tra checklist…`;
      }
      setPendingTurn(curr => (curr ? { ...curr, statusText: nextStatus } : null));
    }, 1000);

    const controller = new AbortController();
    request.current = controller;
    const history = answers
      .filter(a => a.digest === captured.digest)
      .slice(-4)
      .flatMap(a => [
        { role: 'user', content: a.question },
        { role: 'assistant', content: a.answer.slice(0, 12000) }
      ]);
    try {
      await api<Settings>('/api/copilot/config', { ...settings, apiKey: key || undefined });
      setConfigured(true);
      const response = await api<Omit<Answer, 'question' | 'digest'>>(
        featurePath(feature.id) + '/ask',
        { scope, paths, digest: captured.digest, question: input, history },
        controller.signal
      );

      if (statusIntervalRef.current) clearInterval(statusIntervalRef.current);
      setPendingTurn(null);

      const fullAnswer: Answer = { ...response, question: input, digest: captured.digest };
      const fullText = fullAnswer.answer;

      // Progressive streaming chunk calculation
      const totalSteps = 35;
      const stepIntervalMs = 22;
      const chunkSize = Math.max(3, Math.ceil(fullText.length / totalSteps));

      setStreaming({ ...fullAnswer, streamedLength: 0 });

      if (streamIntervalRef.current) clearInterval(streamIntervalRef.current);
      streamIntervalRef.current = setInterval(() => {
        setStreaming(curr => {
          if (!curr) return null;
          const nextLength = curr.streamedLength + chunkSize;
          if (nextLength >= curr.answer.length) {
            if (streamIntervalRef.current) clearInterval(streamIntervalRef.current);
            setAnswers(old => [...old, fullAnswer].slice(-20));
            setBusy(false);
            return null;
          }
          return { ...curr, streamedLength: nextLength };
        });
      }, stepIntervalMs);
    } catch (e) {
      if (statusIntervalRef.current) clearInterval(statusIntervalRef.current);
      if (streamIntervalRef.current) clearInterval(streamIntervalRef.current);
      setPendingTurn(null);
      setStreaming(null);
      setBusy(false);
      setQuestion(input);
      setError((e as Error).name === 'AbortError' ? 'Đã hủy câu hỏi.' : (e as Error).message);
      if ((e as { status?: number }).status === 409) setContextTick(v => v + 1);
    } finally {
      request.current = null;
    }
  }

  async function transfer() {
    if (!context) return;
    try {
      const value = await api<{ prompt: string }>(
        featurePath(feature.id) + '/handoff',
        { scope, paths, digest: context.digest, question: question || 'Tổng hợp trạng thái, việc cần review và bước tiếp theo.' }
      );
      setHandoff(value.prompt);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function openSource(path: string) {
    const direct = contextDocs.find(a => a.path === path);
    if (direct) { source({ artifact: direct }); return; }
    const match = path.match(/^specs\/([^/]+)\/(.+)$/);
    if (!match) return;
    try {
      const data = match[1] === feature.id ? { feature } : await api<FeatureResponse>(featurePath(match[1]));
      const artifact = data.feature.artifacts.find(a => a.path === match[2]);
      if (artifact) source({ artifact: match[1] === feature.id ? artifact : { ...artifact, path }, external: match[1] !== feature.id });
      else setError('Tài liệu nguồn đã bị xóa.');
    } catch (e) { setError((e as Error).message); }
  }

  const activeProvider = providers.find(p => p.id === settings.provider);

  return <section className="copilot-panel" aria-label="Trợ lý AI">
    <div className="section-heading">
      <div>
        <span className="eyebrow">DOCS COPILOT · LOCAL AI</span>
        <h2>Hỏi nhanh có bối cảnh từ specs</h2>
        <p className="muted">Hỏi về yêu cầu, checklist, task và trạng thái review. AI chỉ tư vấn và không tự ý sửa file.</p>
      </div>
      <div className="copilot-header-actions">
        <button
          className={configured ? 'btn-subtle config-pill active' : 'btn-subtle config-pill'}
          onClick={() => setSettingsOpen(v => !v)}
        >
          <span className="status-dot" data-live={configured} />
          <span>{settings.provider === 'antigravity' ? 'Antigravity CLI' : settings.provider.toUpperCase()}</span>
          <span className="pill-model">{settings.model ? `· ${settings.model}` : ''}</span>
          <span className="chevron">{settingsOpen ? '▲' : '▼'}</span>
        </button>
      </div>
    </div>

    {settingsOpen && <div className="copilot-settings-card">
      <div className="settings-header">
        <div>
          <h3>Cấu hình kết nối AI</h3>
          <p className="muted">Kết nối Antigravity CLI, các AI CLI local (Ollama, LM Studio) hoặc API provider.</p>
        </div>
        <button className="btn-icon" onClick={() => setSettingsOpen(false)} title="Thu gọn">✕</button>
      </div>

      <div className="preset-strip">
        <span className="preset-label">Nhanh:</span>
        {PRESETS.map(p => (
          <button
            key={p.label}
            className={`preset-btn ${settings.provider === p.provider && (p.provider !== 'api' || settings.endpoint === p.endpoint) ? 'active' : ''}`}
            onClick={() => applyPreset(p)}
          >
            {p.label}
            {p.badge && <span className="preset-badge">{p.badge}</span>}
          </button>
        ))}
      </div>

      <div className="settings-grid">
        <label>
          <span>Nhà cung cấp</span>
          <select
            value={settings.provider}
            disabled={busy}
            onChange={e => {
              const prov = e.target.value;
              const ep = prov === 'api' ? (settings.endpoint || 'https://api.openai.com/v1') : '';
              const newSettings: Settings = { ...settings, provider: prov, endpoint: ep, model: '' };
              setSettings(newSettings);
              setConfigured(prov !== 'api');
              void fetchModels(prov, ep, key);
              void api<Settings>('/api/copilot/config', { ...newSettings, apiKey: key || undefined }).catch(() => undefined);
            }}
          >
            {[
              ['antigravity', '⚡ Antigravity CLI (agy)'],
              ['api', '🌐 API tương thích OpenAI / Local Service'],
              ['codex', 'Codex CLI'],
              ['claude', 'Claude CLI']
            ].map(([id, label]) => {
              const pInfo = providers.find(p => p.id === id);
              const isCli = id !== 'api';
              const disabled = isCli && !pInfo?.available;
              return (
                <option key={id} value={id} disabled={disabled}>
                  {label}{disabled ? ' (chưa thấy trên PATH)' : ''}
                </option>
              );
            })}
          </select>
        </label>

        {settings.provider === 'api' && <>
          <label>
            <span>Base URL</span>
            <input
              value={settings.endpoint}
              onChange={e => {
                const ep = e.target.value;
                setSettings(s => ({ ...s, endpoint: ep }));
                setConfigured(false);
                if (['localhost', '127.0.0.1'].some(h => ep.includes(h))) {
                  void fetchModels('api', ep, key);
                }
              }}
              placeholder="https://api.openai.com/v1"
            />
          </label>
          <label>
            <span>API key {settings.hasKey && <span className="badge-inline">đã lưu trong RAM</span>}</span>
            <input
              type="password"
              autoComplete="off"
              value={key}
              onChange={e => handleKeyChange(e.target.value)}
              placeholder="Nhập API key (không lưu vào file hay trình duyệt)"
            />
          </label>
        </>}

        <label>
          <span className="label-with-action">
            <span>Model {settings.provider !== 'api' && '(tùy chọn)'}</span>
            <button
              type="button"
              className="btn-link"
              disabled={modelsLoading}
              onClick={() => void fetchModels(settings.provider, settings.endpoint, key, true)}
            >
              {modelsLoading ? 'Đang fetch models…' : '↻ Tải danh sách models'}
            </button>
          </span>
          <div className="model-input-wrapper">
            <input
              list="fetched-models-list"
              value={settings.model}
              onChange={e => {
                setSettings(s => ({ ...s, model: e.target.value }));
                setConfigured(false);
              }}
              placeholder={models.length ? 'Chọn hoặc gõ model ID' : (settings.provider === 'api' ? 'Ví dụ: gpt-4o, llama3' : 'Để trống dùng mặc định')}
            />
            <datalist id="fetched-models-list">
              {models.map(m => (
                <option key={m.id} value={m.id}>{m.name !== m.id ? `${m.name} (${m.id})` : m.id}</option>
              ))}
            </datalist>
          </div>
          {models.length > 0 && (
            <small className="model-count-hint">Đã tìm thấy {models.length} models từ {settings.provider === 'antigravity' ? 'Antigravity CLI' : (settings.endpoint.includes('localhost') ? 'Local AI' : 'provider')}.</small>
          )}
          {modelsError && <small className="error-text">{modelsError}</small>}
        </label>
      </div>

      <div className="settings-actions">
        <button className="primary" onClick={() => void save()} disabled={busy}>
          Lưu kết nối tạm thời
        </button>
        <button className="btn-secondary" onClick={() => void forget()} disabled={busy}>
          Quên kết nối &amp; key
        </button>
      </div>

      <div className="provider-status-bar">
        {activeProvider && (
          <span className={`status-pill ${activeProvider.available ? 'online' : 'offline'}`}>
            {activeProvider.id}: {activeProvider.detail}
          </span>
        )}
        <small className="muted">Key chỉ nằm trong bộ nhớ Node.js tạm thời, không lưu vào đĩa.</small>
      </div>
    </div>}

    <div className="context-panel">
      <div className="context-header">
        <label className="scope-selector">
          <span>Phạm vi:</span>
          <select value={scope} disabled={busy} onChange={e => setScope(e.target.value as 'feature' | 'project')}>
            <option value="feature">Feature hiện tại ({feature.id})</option>
            <option value="project">Toàn bộ project (tối đa 20 feature)</option>
          </select>
        </label>
        <button className="btn-subtle" disabled={busy || contextLoading} onClick={() => setContextTick(v => v + 1)}>
          ↻ Đồng bộ context
        </button>
      </div>

      <details className="context-details">
        <summary>
          <span>Tài liệu đưa vào bối cảnh ({contextLoading ? 'đang đọc…' : `${context?.sources.length ?? 0} file`})</span>
        </summary>
        {scope === 'feature' && (
          <div className="context-chips">
            {feature.artifacts.filter(a => !a.error).map(a => (
              <label key={a.path} className={`context-chip ${paths.includes(a.path) ? 'checked' : ''}`}>
                <input
                  type="checkbox"
                  disabled={busy}
                  checked={paths.includes(a.path)}
                  onChange={e => setPaths(old => e.target.checked ? [...old, a.path] : old.filter(p => p !== a.path))}
                />
                <span>{a.path}</span>
              </label>
            ))}
          </div>
        )}
        <div className="context-sources-list">
          {context?.sources.map(s => (
            <button className="source-pill" key={s.path} onClick={() => void openSource(s.path)}>
              <span>▤ {s.path}</span>
              <span className="source-chars">{s.included.toLocaleString('vi-VN')} chars ↗</span>
            </button>
          ))}
        </div>
      </details>
      {context?.warnings.map(w => <p className="notice warning" key={w}>{w}</p>)}
    </div>

    <div className="quick-prompts">
      <span className="quick-label">Gợi ý câu hỏi:</span>
      {[
        'Tóm tắt các quyết định quan trọng và việc cần tôi review trước?',
        'Task nào đã xong, còn lại và có thể chạy song song?',
        'Có điểm nào chưa rõ (NEEDS CLARIFICATION) trong specs không?'
      ].map(q => (
        <button key={q} className="quick-prompt-btn" disabled={busy} onClick={() => setQuestion(q)}>
          {q}
        </button>
      ))}
    </div>

    <div className="conversation" aria-live="polite">
      {!answers.length && !pendingTurn && !streaming && (
        <div className="copilot-empty">
          <div className="empty-sparkle">✦</div>
          <div>
            <h4>Hỏi bất kỳ điều gì về specs &amp; tasks</h4>
            <p>Hệ thống tự động nạp tài liệu Markdown làm nguồn dữ liệu đối chiếu chuẩn.</p>
          </div>
        </div>
      )}
      {answers.map((a, i) => (
        <article className="chat-turn" key={i}>
          <div className="chat-bubble user">
            <p>{a.question}</p>
          </div>
          <div className="chat-bubble assistant">
            <div className="bubble-meta">
              <span className="meta-provider">✦ {a.provider}</span>
              <div className="meta-actions-right">
                <span className="meta-revision">DOCS {a.revision.slice(0, 8)}</span>
                <button
                  type="button"
                  className="btn-copy-bubble"
                  onClick={() => copyAnswer(i, a.answer)}
                  title="Sao chép nội dung câu trả lời"
                >
                  {copiedIndex === i ? '✓ Đã chép' : '📋 Sao chép'}
                </button>
              </div>
            </div>
            {context && a.digest !== context.digest && (
              <div className="notice warning text-xs">
                Tài liệu đã thay đổi sau câu trả lời này. Bấm gửi lại để dùng dữ liệu mới nhất.
              </div>
            )}
            <Markdown>{a.answer}</Markdown>
            <details className="bubble-sources">
              <summary>Nguồn tài liệu ({a.sources.length})</summary>
              <div className="sources-wrap">
                {a.sources.map(s => (
                  <button key={s.path} className="source-link" onClick={() => void openSource(s.path)}>
                    {s.path} ↗
                  </button>
                ))}
              </div>
            </details>
          </div>
        </article>
      ))}

      {streaming && (
        <article className="chat-turn streaming">
          <div className="chat-bubble user">
            <p>{streaming.question}</p>
          </div>
          <div className="chat-bubble assistant streaming">
            <div className="bubble-meta">
              <span className="meta-provider">
                <span className="sparkle-spin">✦</span> {streaming.provider}
              </span>
              <div className="meta-actions-right">
                <span className="status-badge-live">
                  <span className="live-dot" /> Đang streaming…
                </span>
                <button
                  type="button"
                  className="btn-subtle btn-xs skip-stream-btn"
                  onClick={finishStreaming}
                  title="Hiện toàn bộ câu trả lời"
                >
                  Hiện đủ ⏭
                </button>
              </div>
            </div>
            <Markdown>{streaming.answer.slice(0, streaming.streamedLength)}</Markdown>
            <span className="streaming-cursor" />
          </div>
        </article>
      )}

      {pendingTurn && !streaming && (
        <article className="chat-turn pending" aria-live="polite">
          <div className="chat-bubble user">
            <p>{pendingTurn.question}</p>
          </div>
          <div className="chat-bubble assistant pending">
            <div className="bubble-meta">
              <span className="meta-provider">
                <span className="sparkle-spin">✦</span> {settings.provider === 'antigravity' ? 'Antigravity CLI' : settings.provider.toUpperCase()}
                {settings.model && <span className="meta-model-tag">· {settings.model}</span>}
              </span>
              <span className="status-badge-live">
                <span className="live-dot" /> {pendingTurn.statusText}
              </span>
            </div>

            <div className="ai-thinking-state">
              <div className="typing-dots">
                <span />
                <span />
                <span />
              </div>
              <p className="thinking-hint">{pendingTurn.statusText}</p>
            </div>

            <div className="pending-actions">
              <button
                type="button"
                className="btn-subtle btn-xs cancel-prompt-btn"
                onClick={cancelAsk}
              >
                ■ Hủy yêu cầu
              </button>
            </div>
          </div>
        </article>
      )}

      <div ref={chatBottomRef} />
    </div>

    <div className="chat-input-area">
      <textarea
        id="copilot-question"
        value={question}
        maxLength={8000}
        onChange={e => setQuestion(e.target.value)}
        onKeyDown={e => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            void ask();
          }
        }}
        placeholder="Đặt câu hỏi về specs, tasks hoặc rủi ro (Enter để gửi, Shift+Enter xuống dòng)…"
        disabled={busy}
      />
      <div className="copilot-actions">
        <button className="btn-subtle" onClick={() => void transfer()} disabled={!context || busy}>
          📋 Tạo Handoff Prompt cho Agent CLI
        </button>
        {busy ? (
          <button className="danger" onClick={cancelAsk}>
            ■ Hủy yêu cầu
          </button>
        ) : (
          <button
            className="primary"
            onClick={() => void ask()}
            disabled={busy || !question.trim() || !context || (settings.provider === 'api' && !settings.endpoint)}
          >
            ✦ Gửi câu hỏi
          </button>
        )}
      </div>
      {error && <p role="alert" className="notice danger">{error}</p>}
      {message && <p role="status" className="notice success">{message}</p>}
    </div>

    {handoff && <div className="handoff-box">
      <div className="handoff-header">
        <strong>Prompt Handoff (dán vào terminal của agent CLI)</strong>
        <button
          className="btn-subtle"
          onClick={() => {
            void navigator.clipboard.writeText(handoff).then(() => setMessage('Đã sao chép prompt handoff.')).catch(() => setMessage('Chọn và sao chép thủ công.'));
          }}
        >
          Sao chép
        </button>
      </div>
      <textarea aria-label="Prompt chuyển agent" readOnly value={handoff} />
    </div>}
  </section>;
}
