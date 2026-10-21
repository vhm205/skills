import { useEffect, useRef, useState } from 'react';
import type { Artifact, Section } from '../src/types';
import { api, ApiError, featurePath } from './api';
import { Diff } from './Diff';
export interface EditSelection { featureId: string; artifact: Artifact; section: Section }
export function Editor({ selection, close, saved }: { selection: EditSelection; close: () => void; saved: () => void }) {
  const [base, setBase] = useState(selection);
  const [draft, setDraft] = useState(selection.section.content);
  const [preview, setPreview] = useState(false);
  const [error, setError] = useState('');
  const [conflict, setConflict] = useState(false);
  const [busy, setBusy] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { dialog.current?.showModal(); }, []);
  const requestClose = () => {
    if (!busy && (draft === base.section.content || window.confirm('Đóng và bỏ bản nháp chưa lưu?'))) close();
  };
  async function save() {
    setBusy(true); setError('');
    try {
      await api(featurePath(base.featureId) + '/section', { artifactId: base.artifact.id, sectionId: base.section.id,
        hash: base.artifact.hash, content: draft });
      saved(); close();
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Chưa lưu được.');
      setConflict(error instanceof ApiError && error.status === 409);
    } finally { setBusy(false); }
  }
  async function reload() {
    setBusy(true);
    try {
      const { feature } = await api<import('./api').FeatureResponse>(featurePath(base.featureId));
      const artifact = feature.artifacts.find(a => a.id === base.artifact.id);
      // Duplicate headings cannot be matched safely after an external edit.
      const candidates = artifact?.sections.filter(s => s.editable && s.title.toLowerCase() === base.section.title.toLowerCase());
      if (!artifact || candidates?.length !== 1) throw new Error('Section bị xóa hoặc trùng heading. Sao chép bản nháp và mở lại section từ nguồn mới.');
      setBase({ ...base, artifact, section: candidates[0] });
      setConflict(false); setError('Đã tải nguồn mới. Bản nháp giữ nguyên; đối chiếu diff trước khi lưu.'); setPreview(true);
    } catch (error) { setError((error as Error).message); }
    finally { setBusy(false); }
  }
  return <dialog ref={dialog} className="editor-dialog" onCancel={event => { event.preventDefault(); requestClose(); }}>
    <header className="dialog-header"><div><span className="eyebrow">CHỈNH TÀI LIỆU</span><h2>{base.section.title}</h2><p className="muted">{base.artifact.path} · dòng {base.section.line}</p></div><button onClick={requestClose} disabled={busy}>Đóng ×</button></header>
    <p>Chỉ sửa section này. Giữ nguyên heading; lưu tài liệu không đồng nghĩa approve gate.</p>
    <label htmlFor="decision-draft">Markdown quyết định</label>
    <textarea id="decision-draft" value={draft} onChange={event => { setDraft(event.target.value); setPreview(false); }} spellCheck={false} disabled={busy} />
    {error && <p className={conflict ? 'notice danger' : 'notice'} role="alert">{error}</p>}
    {conflict && <button onClick={() => void reload()} disabled={busy}>Tải nguồn mới, giữ bản nháp</button>}
    {preview && <Diff before={base.section.content} after={draft} />}
    <footer className="editor-actions"><button onClick={() => setPreview(true)} disabled={busy || draft === base.section.content}>Xem diff</button>
      <button className="primary" onClick={() => void save()} disabled={busy || !preview || conflict || draft === base.section.content}>{busy ? 'Đang lưu…' : 'Lưu vào tài liệu'}</button></footer>
  </dialog>;
}
