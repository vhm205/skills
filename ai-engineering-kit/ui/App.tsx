import { useCallback, useEffect, useState } from 'react';
import type { ProjectInfo, ProjectSummary } from '../src/types';
import {
  api,
  connect,
  featurePath,
  getProjects,
  addProject,
  switchProject,
  removeProject,
  type FeatureResponse
} from './api';
import { FeatureView, views, type View } from './Views';
import { Source, type SourceSelection } from './Source';
import { Editor, type EditSelection } from './Editor';
import { WorkflowPanel } from './Workflow';
import { CopilotPanel } from './Copilot';

export function App() {
  const [project, setProject] = useState<ProjectInfo | null>(null);
  const [projectsList, setProjectsList] = useState<ProjectSummary[]>([]);
  const [projectMenuOpen, setProjectMenuOpen] = useState(false);
  const [newPathInput, setNewPathInput] = useState('');
  const [projectActionBusy, setProjectActionBusy] = useState(false);
  const [selected, setSelected] = useState('');
  const [data, setData] = useState<FeatureResponse | null>(null);
  const [view, setView] = useState<View | 'copilot'>('overview');
  const [source, setSource] = useState<SourceSelection | null>(null);
  const [editor, setEditor] = useState<EditSelection | null>(null);
  const [tick, setTick] = useState(0);
  const [connected, setConnected] = useState(false);
  const [warning, setWarning] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Dark/Light theme state
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    return (localStorage.getItem('aiek-theme') as 'light' | 'dark') ||
      (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('aiek-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(t => (t === 'light' ? 'dark' : 'light'));
  };

  const reload = useCallback(() => setTick(value => value + 1), []);

  const refreshProjects = useCallback(async () => {
    try {
      const res = await getProjects();
      setProjectsList(res.projects || []);
    } catch {
      // Ignore initial project list error if session isn't ready
    }
  }, []);

  useEffect(() => {
    let active = true;
    let events: EventSource | undefined;
    void connect().then(info => {
      if (!active) return;
      setProject(info);
      void refreshProjects();
      events = new EventSource('/api/events');
      events.onopen = () => { setConnected(true); reload(); };
      events.addEventListener('change', () => {
        reload();
        void refreshProjects();
      });
      events.addEventListener('warning', event => { setWarning(JSON.parse((event as MessageEvent).data).error); });
      events.onerror = () => setConnected(false);
    }).catch(err => { if (active) setError(err.message); });
    return () => { active = false; events?.close(); };
  }, [reload, refreshProjects]);

  useEffect(() => {
    if (!project) return;
    const controller = new AbortController();
    setLoading(true);
    void Promise.all([
      api<ProjectInfo>('/api/project', undefined, controller.signal),
      selected ? api<FeatureResponse>(featurePath(selected), undefined, controller.signal) : Promise.resolve(null),
    ]).then(([info, feat]) => {
      setProject(info);
      setData(feat);
      setError('');
    }).catch(err => {
      if (err.name !== 'AbortError') { setError(err.message); setData(null); }
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [selected, tick, !!project]);

  const handleSwitchProject = async (root: string) => {
    if (projectActionBusy || root === project?.root) return;
    setProjectActionBusy(true);
    setError('');
    try {
      const res = await switchProject(root);
      setProject(res.project);
      setSelected('');
      setData(null);
      setView('overview');
      setProjectMenuOpen(false);
      setMessage(`Đã chuyển sang project: ${res.project.name}`);
      reload();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setProjectActionBusy(false);
    }
  };

  const handleAddProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPathInput.trim() || projectActionBusy) return;
    setProjectActionBusy(true);
    setError('');
    try {
      const res = await addProject(newPathInput.trim(), true);
      setProject(res.project);
      setSelected('');
      setData(null);
      setNewPathInput('');
      setProjectMenuOpen(false);
      setMessage(`Đã mở project: ${res.project.name}`);
      void refreshProjects();
      reload();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setProjectActionBusy(false);
    }
  };

  const handleRemoveProject = async (e: React.MouseEvent, root: string) => {
    e.stopPropagation();
    if (projectActionBusy || projectsList.length <= 1) return;
    if (!window.confirm('Bỏ project này khỏi danh sách quản lý?')) return;
    setProjectActionBusy(true);
    try {
      await removeProject(root);
      void refreshProjects();
      reload();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setProjectActionBusy(false);
    }
  };

  async function snapshot() {
    if (!data || saving) return;
    if (data.review.baseline && !window.confirm('Thay mốc review trước bằng phiên bản đang hiển thị?')) return;
    setSaving(true); setMessage('');
    try {
      await api(featurePath(data.feature.id) + '/snapshot', { revision: data.feature.revision });
      setMessage('Đã lưu mốc review local.');
      reload();
    } catch (err) { setMessage((err as Error).message); }
    finally { setSaving(false); }
  }

  const feature = data?.feature;
  const tasks = feature?.artifacts.find(a => a.path === 'tasks.md')?.tasks ?? [];
  const completedTasks = tasks.filter(t => t.checked).length;
  const taskPercent = tasks.length > 0 ? Math.round((completedTasks / tasks.length) * 100) : 0;
  const decisions = feature?.artifacts.flatMap(a => a.sections.filter(s => /decision|clarification|quyết định|làm rõ/i.test(s.title))) ?? [];
  const currentSource = source?.external
    ? source.artifact
    : source
      ? [...(data?.feature.artifacts ?? []), ...(project?.context ?? [])].find(a => a.id === source.artifact.id && a.path === source.artifact.path)
      : null;

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">Đến nội dung</a>

      {/* Sidebar */}
      {sidebarOpen && <div className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} aria-hidden="true" />}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`} aria-label="Điều hướng project">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">a.</span>
          <div className="brand-text">
            <strong>Engineering Kit</strong>
            <span>LOCAL REVIEW SUITE</span>
          </div>
        </div>

        {/* Project Selector / Switcher */}
        <div className="project-selector-wrapper">
          <button
            className={`project-switcher-btn ${projectMenuOpen ? 'open' : ''}`}
            onClick={() => setProjectMenuOpen(v => !v)}
            aria-expanded={projectMenuOpen}
            aria-label="Chuyển đổi project"
          >
            <span className="folder-icon" aria-hidden="true">📁</span>
            <div className="project-switcher-info">
              <span className="project-label">DỰ ÁN HIỆN TẠI</span>
              <strong className="project-title">{project?.name ?? 'Đang kết nối…'}</strong>
              <span className="root-path-mini" title={project?.root}>{project?.root}</span>
            </div>
            <span className="switcher-chevron">{projectMenuOpen ? '▲' : '▼'}</span>
          </button>

          {projectMenuOpen && (
            <div className="project-menu-dropdown animate-fade-in">
              <div className="menu-header">
                <span>Danh sách dự án ({projectsList.length})</span>
                <span className="menu-hint">Click để chuyển ngay</span>
              </div>
              <div className="project-menu-list">
                {projectsList.map(p => (
                  <div
                    key={p.root}
                    className={`project-menu-item ${p.root === project?.root ? 'active' : ''}`}
                    onClick={() => void handleSwitchProject(p.root)}
                  >
                    <div className="project-item-main">
                      <span className="project-item-dot" data-active={p.root === project?.root} />
                      <div>
                        <strong>{p.name}</strong>
                        <small className="muted root-path-sub">{p.root}</small>
                      </div>
                    </div>
                    <div className="project-item-meta">
                      <span className="feature-count-badge">{p.featureCount} feats</span>
                      {projectsList.length > 1 && (
                        <button
                          className="btn-remove-project"
                          title="Đóng project này"
                          onClick={e => void handleRemoveProject(e, p.root)}
                        >
                          ✕
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Add Project Form */}
              <form className="add-project-form" onSubmit={handleAddProject}>
                <label htmlFor="new-project-path">Thêm project từ thư mục local:</label>
                <div className="add-project-row">
                  <input
                    id="new-project-path"
                    type="text"
                    placeholder="/path/to/project-directory"
                    value={newPathInput}
                    onChange={e => setNewPathInput(e.target.value)}
                    disabled={projectActionBusy}
                  />
                  <button type="submit" className="primary btn-add" disabled={!newPathInput.trim() || projectActionBusy}>
                    + Thêm
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>

        {/* Feature search */}
        <div className="search-box">
          <input
            id="feature-search"
            className="search-input"
            type="search"
            placeholder="Tìm feature (tên, số)…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        <div className="sidebar-heading">
          <span>FEATURES</span>
          <span className="badge-count">{project?.features.length ?? 0}</span>
        </div>

        <nav className="features-nav" aria-label="Chọn feature">
          {project?.features
            .filter(f => f.name.toLowerCase().includes(search.toLowerCase()))
            .map(f => (
              <button
                key={f.id}
                aria-label={`Chọn feature ${f.id}`}
                className={selected === f.id ? 'feature-item active' : 'feature-item'}
                aria-current={selected === f.id ? 'page' : undefined}
                onClick={() => {
                  setSelected(f.id);
                  setData(null);
                  setView('overview');
                  setMessage('');
                  setSidebarOpen(false);
                }}
              >
                <span className="feature-icon" aria-hidden="true">◇</span>
                <span className="feature-name">{f.name}</span>
              </button>
            ))}
          {project && !project.features.length && (
            <p className="sidebar-empty">Chưa có feature nào trong specs/.</p>
          )}
        </nav>

        <footer className="sidebar-footer">
          <div className="status-indicator">
            <span className="status-dot" data-live={connected} />
            <span>{connected ? 'Local sync' : 'Đang kết nối'}</span>
          </div>
          <div className="footer-actions">
            <button className="btn-icon" onClick={toggleTheme} title={`Chuyển sang ${theme === 'dark' ? 'giao diện Sáng' : 'giao diện Tối'}`}>
              {theme === 'dark' ? '☀️' : '🌙'}
            </button>
            <button className="btn-icon" onClick={reload} aria-label="Tải lại dữ liệu" title="Tải lại dữ liệu">
              ↻
            </button>
          </div>
        </footer>
      </aside>

      {/* Main Workspace */}
      <div className="workspace">
        <header className="topbar">
          <div className="topbar-breadcrumbs">
            <button
              className="btn-icon mobile-menu-btn"
              onClick={() => setSidebarOpen(v => !v)}
              aria-label="Mở menu dự án và features"
              title="Menu"
            >
              ☰
            </button>
            <span className="muted">Project:</span>
            <strong className="topbar-project-name">{project?.name ?? 'Local Review'}</strong>
            {selected && (
              <>
                <span className="separator">/</span>
                <span className="breadcrumb-feature">{selected}</span>
              </>
            )}
          </div>
          <div className="topbar-actions">
            <span className="local-label">LOCAL · DOCS LÀ NGUỒN CHUẨN</span>
            <button className="btn-subtle btn-sm" onClick={toggleTheme} title="Đổi màu giao diện">
              {theme === 'dark' ? '☀️ Sáng' : '🌙 Tối'}
            </button>
          </div>
        </header>

        <main id="main" className="main">
          {error && <div className="notice danger" role="alert">{error}<button className="btn-link" onClick={reload}>Thử lại</button></div>}
          {warning && <p className="notice warning" role="alert">{warning}</p>}
          {project?.warnings.map(item => <p className="notice warning" key={item}>{item}</p>)}
          {project && !project.kitInstalled && (
            <p className="notice info">Chưa phát hiện .aiek/. Kit đang ở chế độ spec viewer; hãy cài đặt kit theo hướng dẫn để sử dụng toàn bộ workflow &amp; adapter.</p>
          )}

          {!selected && (
            <section className="welcome">
              <span className="eyebrow">AI ENGINEERING SUITE</span>
              <h1>Quản lý &amp; Review Specs<br />Toàn bộ bối cảnh trong tầm tay.</h1>
              <p>Chọn một feature ở thanh bên để đối chiếu yêu cầu, checklist, sự thay đổi tài liệu và kiểm thử thực tế.</p>
              <div className="welcome-line" />
              <div className="welcome-tips">
                <div className="tip-card">
                  <strong>⚡ Đa dự án</strong>
                  <p>Bấm vào tên dự án ở góc trên bên trái để thêm hoặc chuyển đổi giữa các dự án tức thì.</p>
                </div>
                <div className="tip-card">
                  <strong>✦ Docs Copilot</strong>
                  <p>Hỗ trợ Antigravity CLI (`agy`), Local AI (Ollama, LM Studio) và OpenAI API tự động nạp models.</p>
                </div>
              </div>
            </section>
          )}

          {selected && loading && !feature && (
            <div className="loading-card" role="status">
              <span className="spinner" />
              <p>Đang đọc và phân tích tài liệu specs…</p>
            </div>
          )}

          {feature && (
            <>
              {/* Feature Header */}
              <div className="feature-header">
                <div>
                  <div className="feature-meta-pill">
                    <span className="badge badge-accent">FEATURE {feature.id.match(/^(\d+)/)?.[1] ?? 'ID'}</span>
                    <span className="revision-tag" title="Revision hash">rev: {feature.revision.slice(0, 8)}</span>
                  </div>
                  <h1>{feature.id.replace(/^\d+-/, '').replaceAll('-', ' ')}</h1>
                  <p className="feature-subtext">Đường dẫn: specs/{feature.id}/</p>
                </div>
                <div className="feature-cta">
                  <button className="primary btn-save-baseline" onClick={() => void snapshot()} disabled={saving || loading}>
                    {saving ? 'Đang lưu mốc…' : '✓ Lưu mốc đã review'}
                  </button>
                </div>
              </div>

              {message && <p role="status" className="notice success">{message}</p>}

              {/* Redesigned Clean Metric Cards */}
              <div className="metrics-grid">
                <div className="metric-card">
                  <span className="metric-label">TIẾN ĐỘ TASKS</span>
                  <div className="metric-value-row">
                    <strong>{completedTasks} <span className="muted">/ {tasks.length}</span></strong>
                    <span className="metric-percent">{taskPercent}%</span>
                  </div>
                  <div className="progress-bar-bg">
                    <div className="progress-bar-fill" style={{ width: `${taskPercent}%` }} />
                  </div>
                </div>

                <div className="metric-card">
                  <span className="metric-label">LANE QUY TRÌNH</span>
                  <div className="metric-value-row">
                    <span className={`lane-pill ${feature.lane ? feature.lane.toLowerCase() : 'unspecified'}`}>
                      {feature.lane ?? 'Chưa xác định'}
                    </span>
                  </div>
                  <small className="muted metric-desc">Dựa trên khai báo trong plan.md</small>
                </div>

                <div className="metric-card">
                  <span className="metric-label">QUYẾT ĐỊNH &amp; LÀM RÕ</span>
                  <div className="metric-value-row">
                    <strong>{decisions.length}</strong>
                    <span className="metric-sub">{feature.clarifications > 0 ? `${feature.clarifications} cần làm rõ` : 'Rõ ràng'}</span>
                  </div>
                  <small className="muted metric-desc">Trong spec &amp; checklist</small>
                </div>

                <div className="metric-card">
                  <span className="metric-label">KIỂM CHỨNG CODE</span>
                  <div className="metric-value-row">
                    {data.workflow.evidence.length > 0 ? (
                      <span className="status-badge-verified">✓ {data.workflow.evidence.length} bằng chứng</span>
                    ) : (
                      <span className="status-badge-unverified">Chưa có ghi nhận</span>
                    )}
                  </div>
                  <small className="muted metric-desc">Cần độc lập chạy kiểm thử</small>
                </div>
              </div>

              {/* Workflow Stepper */}
              <WorkflowPanel data={data} inspect={() => setView('round')} refresh={reload} />

              {/* Review Panel & Document Rail */}
              <div className="content-layout">
                <div className="review-panel">
                  <nav className="tabs" aria-label="Nội dung review">
                    {views.map(([id, label]) => (
                      <button
                        key={id}
                        onClick={() => setView(id)}
                        className={view === id ? 'active' : ''}
                        aria-current={view === id ? 'page' : undefined}
                      >
                        {label}
                        {id === 'changes' && data.review.changes.length > 0 && (
                          <span className="count-pill">{data.review.changes.length}</span>
                        )}
                        {id === 'round' && data.workflow.pending.length > 0 && (
                          <span className="count-pill alert">{data.workflow.pending.length}</span>
                        )}
                      </button>
                    ))}
                    <button
                      onClick={() => setView('copilot')}
                      className={view === 'copilot' ? 'active copilot-tab' : 'copilot-tab'}
                      aria-current={view === 'copilot' ? 'page' : undefined}
                    >
                      ✦ Trợ lý AI
                    </button>
                  </nav>

                  <div className="view-content" aria-busy={loading}>
                    {view === 'copilot' ? (
                      <CopilotPanel
                        key={feature.id}
                        feature={feature}
                        contextDocs={project?.context ?? []}
                        source={setSource}
                        contextEpoch={tick}
                      />
                    ) : (
                      <FeatureView data={data} view={view} source={setSource} edit={setEditor} />
                    )}
                  </div>
                </div>

                {/* Right Document Rail */}
                <aside className="document-rail" aria-label="Tài liệu nguồn">
                  <div className="rail-header">
                    <h2>Tài liệu nguồn</h2>
                    <span className="rail-count">{feature.artifacts.length} file</span>
                  </div>
                  <p className="muted rail-sub">Đối chiếu nguyên văn specs Markdown.</p>

                  <div className="rail-doc-list">
                    {feature.artifacts.map(artifact => (
                      <button
                        key={artifact.id}
                        className={`document-link ${artifact.error ? 'has-error' : ''}`}
                        aria-label={`Mở ${artifact.path}`}
                        onClick={() => setSource({ artifact })}
                      >
                        <span className="doc-icon" aria-hidden="true">▤</span>
                        <span className="doc-path">{artifact.path}</span>
                        <span className="doc-status">{artifact.error ? '!' : '↗'}</span>
                      </button>
                    ))}
                  </div>

                  {!feature.artifacts.length && <p className="muted">Chưa có tài liệu Markdown nào.</p>}
                  {feature.warnings.map(item => <p className="rail-warning" key={item}>{item}</p>)}

                  {!!project?.context.length && (
                    <details className="rail-core-docs">
                      <summary>Core &amp; adapter ({project.context.length})</summary>
                      {project.context.map(artifact => (
                        <button
                          key={artifact.id}
                          className="document-link"
                          aria-label={`Mở ${artifact.path}`}
                          onClick={() => setSource({ artifact })}
                        >
                          <span className="doc-icon" aria-hidden="true">⚙</span>
                          <span className="doc-path">{artifact.path}</span>
                        </button>
                      ))}
                    </details>
                  )}

                  <div className="rail-note">
                    <span className="eyebrow">NGUYÊN TẮC</span>
                    <p>Tiến độ tick trong docs chưa chứng minh code pass kiểm thử thực tế.</p>
                  </div>
                </aside>
              </div>
            </>
          )}
        </main>
      </div>

      {/* Source Viewer Modal */}
      {source && (
        <Source
          selection={{
            ...source,
            artifact: currentSource ?? {
              ...source.artifact,
              error: 'Tài liệu đã bị xóa hoặc không còn đọc được trong project.'
            }
          }}
          close={() => setSource(null)}
          edit={feature && currentSource && !source.external && feature.artifacts.includes(currentSource)
            ? section => {
              setEditor({ featureId: feature.id, artifact: currentSource, section });
              setSource(null);
            }
            : undefined}
        />
      )}

      {/* Editor Modal */}
      {editor && (
        <Editor
          selection={editor}
          close={() => setEditor(null)}
          saved={() => {
            setMessage('Đã lưu section vào tài liệu. Mốc review chưa tự động approve.');
            reload();
          }}
        />
      )}
    </div>
  );
}
