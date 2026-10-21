import { useState } from 'react';
import type { FeatureResponse } from './api';
import { api, featurePath } from './api';
import type { SourceSelection } from './Source';

const labels: Record<string, string> = {
  missing: 'Chưa có',
  available: 'Có tài liệu',
  changed: 'Cần review',
  reviewed: 'Đã review',
  reported: 'Ghi nhận',
  stale: 'Cần đối chiếu',
  unknown: 'Chưa xác nhận'
};

export function WorkflowPanel({ data, inspect, refresh }: { data: FeatureResponse; inspect: () => void; refresh: () => void }) {
  const flow = data.workflow;
  const [step, setStep] = useState('analyze');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [showAllStages, setShowAllStages] = useState(false);
  const [copied, setCopied] = useState(false);

  const available = flow.steps.filter(s => ['analyze', 'worktree', 'verify', 'review'].includes(s.id));
  const chosenStep = available.some(s => s.id === step) ? step : available[0]?.id ?? 'verify';

  async function record() {
    setBusy(true); setError('');
    try {
      await api(featurePath(data.feature.id) + '/evidence', { revision: data.feature.revision, step: chosenStep, note });
      setNote('');
      refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const copyCommand = (cmd: string) => {
    void navigator.clipboard.writeText(cmd).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <section className="workflow-board" aria-label="Trạng thái workflow">
      {/* Workflow Header */}
      <div className="workflow-heading">
        <div className="workflow-current-info">
          <span className="workflow-eyebrow">QUY TRÌNH PHÁT TRIỂN</span>
          <div className="milestone-title-row">
            <span className="milestone-status-dot" />
            <h2>{flow.current}</h2>
          </div>
        </div>
        <div className="workflow-heading-controls">
          <span className="badge-lane">{data.feature.lane ? `Lane: ${data.feature.lane}` : 'Chưa rõ lane'}</span>
          <button
            className="btn-ghost-sm"
            onClick={() => setShowAllStages(v => !v)}
            aria-expanded={showAllStages}
          >
            {showAllStages ? 'Thu gọn các bước ▲' : 'Chi tiết 7 giai đoạn ▼'}
          </button>
        </div>
      </div>

      {/* Segmented Pipeline Stepper Bar */}
      <div className="pipeline-stepper-bar" aria-label="Tiến trình quy trình">
        {flow.steps.map((item, i) => {
          const isCurrent = flow.next === item.id;
          const isDone = item.state === 'reviewed' || item.state === 'reported';
          return (
            <div
              key={item.id}
              className={`stepper-node ${isCurrent ? 'current' : ''} ${isDone ? 'done' : ''}`}
              title={`${item.label}: ${item.detail}`}
            >
              <div className="node-marker">
                {isDone ? '✓' : (isCurrent ? '●' : (i + 1))}
              </div>
              <div className="node-content">
                <span className="node-label">{item.label}</span>
                <span className="node-state">{labels[item.state] || item.state}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Expandable full stage cards */}
      {showAllStages && (
        <ol className="workflow-detail-grid animate-fade-in">
          {flow.steps.map((item, i) => (
            <li key={item.id} className={`detail-card ${flow.next === item.id ? 'current' : ''}`} data-state={item.state}>
              <div className="detail-card-head">
                <span className="detail-num">{String(i + 1).padStart(2, '0')}</span>
                <strong>{item.label}</strong>
              </div>
              <span className="detail-status">{labels[item.state] || item.state}</span>
              <p className="detail-desc">{item.detail}</p>
            </li>
          ))}
        </ol>
      )}

      {/* Modern Next Action Banner */}
      <div className="next-action-card">
        <div className="action-indicator-bar" />
        <div className="action-body">
          <div className="action-tag">TIẾP THEO</div>
          <strong className="action-main-text">{flow.action}</strong>
          {flow.command && (
            <div className="command-row">
              <code className="action-code">{flow.command}</code>
              <button className="btn-copy-sm" onClick={() => copyCommand(flow.command)} title="Sao chép lệnh">
                {copied ? '✓ Đã chép' : 'Sao chép'}
              </button>
            </div>
          )}
        </div>
        {flow.pending.length > 0 && (
          <button className="primary btn-next-action" onClick={inspect}>
            Review tài liệu ({flow.pending.length}) →
          </button>
        )}
      </div>

      {/* Attestation recording drawer */}
      <details className="attestation-drawer">
        <summary className="attestation-summary">
          <span>Ghi nhận kiểm chứng đã chạy (analyze / worktree / verify / review)</span>
          <span className="text-muted text-xs">({flow.evidence.length} ghi nhận)</span>
        </summary>
        <div className="attestation-content">
          <p className="text-muted text-xs">
            Dán command, exit code hoặc kết luận kiểm thử của reviewer để ghi nhận bằng chứng cho phiên bản docs hiện tại.
          </p>
          <div className="attestation-form">
            <div className="form-row">
              <label htmlFor="attest-step-select">Bước kiểm chứng:</label>
              <select id="attest-step-select" aria-label="Bước đã chạy" value={chosenStep} onChange={e => setStep(e.target.value)}>
                {available.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
              </select>
            </div>
            <textarea
              value={note}
              maxLength={4000}
              onChange={e => setNote(e.target.value)}
              placeholder="Ví dụ: vitest run · exit 0 · 34 tests pass"
            />
            <div className="form-actions">
              <button className="btn-secondary" onClick={() => void record()} disabled={busy || !note.trim()}>
                {busy ? 'Đang lưu…' : 'Ghi nhận cho mốc này'}
              </button>
            </div>
            {error && <p role="alert" className="notice danger">{error}</p>}
          </div>

          {flow.evidence.length > 0 && (
            <div className="evidence-list">
              {flow.evidence.slice().reverse().map((item, i) => (
                <div className="evidence-entry" key={i}>
                  <div className="evidence-meta">
                    <strong>{item.step.toUpperCase()}</strong>
                    <span className="text-muted">{new Date(item.at).toLocaleString('vi-VN')}</span>
                    <span className={`evidence-badge ${item.revision === data.feature.revision ? 'match' : 'stale'}`}>
                      {item.revision === data.feature.revision ? 'Khớp mốc hiện tại' : 'Docs đã đổi'}
                    </span>
                  </div>
                  <pre>{item.note}</pre>
                </div>
              ))}
            </div>
          )}
        </div>
      </details>
    </section>
  );
}

export function ReviewInbox({ data, source }: { data: FeatureResponse; source: (value: SourceSelection) => void }) {
  const { feature, review, workflow: flow } = data;
  return (
    <section className="review-inbox">
      <div className="section-heading">
        <div>
          <h2>Vòng review hiện tại</h2>
          <p className="text-muted">
            {review.baseline ? 'So với lần bạn lưu mốc gần nhất. Tự động cập nhật khi tài liệu thay đổi.' : 'Lần review đầu tiên: đối chiếu tài liệu hiện có rồi lưu mốc.'}
          </p>
        </div>
        <span className="badge-pill">{flow.pending.length} tài liệu cần xem</span>
      </div>

      {!flow.pending.length && (
        <div className="empty-state-box">
          <span className="empty-icon">✓</span>
          <h4>Bạn đã hoàn thành vòng review này</h4>
          <p className="text-muted">Chạy bước tiếp theo trong workflow; giao diện sẽ tự động cập nhật khi có tài liệu đổi.</p>
        </div>
      )}

      {/* Review Cards Grid - Clean Monochrome Style */}
      <div className="review-cards-grid">
        {flow.pending.map(path => {
          const artifact = feature.artifacts.find(a => a.path === path);
          const change = review.changes.find(c => c.path === path);
          const stage = flow.steps.find(s => s.paths.includes(path));
          const isDeleted = change?.status === 'deleted';
          const isNew = !review.baseline || change?.status === 'added';
          const statusClass = isDeleted ? 'deleted' : (isNew ? 'added' : 'modified');
          const statusLabel = isDeleted ? 'ĐÃ XÓA' : (isNew ? 'MỚI' : 'ĐÃ SỬA');

          return (
            <article key={path} className={`doc-review-card ${statusClass}`}>
              <div className="card-top-row">
                <span className="category-pill">{stage?.label ?? 'Tài liệu hỗ trợ'}</span>
                <span className={`status-pill ${statusClass}`}>{statusLabel}</span>
              </div>
              <h3 className="doc-card-title">
                <span className="file-icon" aria-hidden="true">📄</span>
                <span>{path}</span>
              </h3>
              <div className="doc-card-metrics">
                <span>{artifact?.sections.length ?? 0} section</span>
                <span className="metric-dot">·</span>
                <span>{artifact?.tasks.length ? `${artifact.tasks.filter(t => t.checked).length}/${artifact.tasks.length} task tick` : 'Không có task'}</span>
              </div>
              {change && (change.taskProgress.totalBefore || change.taskProgress.totalAfter) > 0 && (
                <p className="task-delta">
                  Task tick: {change.taskProgress.before}/{change.taskProgress.totalBefore} → {change.taskProgress.after}/{change.taskProgress.totalAfter}
                </p>
              )}
              <ul className="doc-changes-list">
                {change ? (
                  change.changedHeadings.length ? (
                    change.changedHeadings.slice(0, 5).map(title => <li key={title}>Đổi: {title}</li>)
                  ) : (
                    <li>Nội dung tài liệu đã thay đổi; xem diff để đối chiếu.</li>
                  )
                ) : (
                  artifact?.sections.filter(s => s.depth === 2).slice(0, 4).map(s => <li key={s.id}>{s.title}</li>)
                )}
              </ul>
              {artifact && (
                <div className="card-action-row">
                  <button className="btn-review-card" onClick={() => source({ artifact })}>
                    Review &amp; chỉnh sửa ↗
                  </button>
                </div>
              )}
            </article>
          );
        })}
      </div>

      {!!review.baseline?.history?.length && (
        <details className="history-drawer">
          <summary>Lịch sử review ({review.baseline.history.length} vòng trước)</summary>
          <ol className="history-list">
            {review.baseline.history.slice().reverse().map((round, i) => (
              <li key={i}>
                <div className="history-meta">
                  <strong>{new Date(round.at).toLocaleString('vi-VN')}</strong>
                  <span className="text-muted">{round.changed.length} file đổi · {round.completed}/{round.total} tasks · {round.revision.slice(0, 8)}</span>
                </div>
                <small className="text-muted">{round.changed.join(' · ') || 'Docs không đổi'}</small>
              </li>
            ))}
          </ol>
        </details>
      )}
    </section>
  );
}
