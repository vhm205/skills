import { useEffect, useRef, useState } from 'react';
import type { Artifact, Section } from '../src/types';
import { Markdown } from './Markdown';
export interface SourceSelection { artifact: Artifact; line?: number; content?: string; external?: boolean }
export function Source({ selection, close, edit }: { selection: SourceSelection; close: () => void; edit?: (section: Section) => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [openedHash] = useState(selection.artifact.hash);
  useEffect(() => { dialog.current?.showModal(); }, []);
  const { artifact, line, content } = selection;
  const changed = artifact.hash !== openedHash;
  const displayed = changed ? artifact.content : content ?? artifact.content;
  return <dialog ref={dialog} onCancel={close} onClose={close} className="source-dialog">
    <header className="dialog-header"><div><span className="eyebrow">TÀI LIỆU NGUỒN</span><h2>{artifact.path}{line && !changed ? ` · dòng ${line}` : ''}</h2></div>
      <button onClick={close} aria-label="Đóng tài liệu nguồn">Đóng ×</button></header>
    {changed && <p role="status" className="notice">Nguồn đã đổi. Đang hiển thị toàn bộ phiên bản mới; vị trí section cũ không còn được dùng.</p>}
    {artifact.error ? <p role="alert">{artifact.error}</p> : <Markdown>{displayed}</Markdown>}
    {edit && !artifact.error && <details><summary>Chỉnh sửa section trong tài liệu này</summary><div className="section-edit-list">{artifact.sections.filter(s => s.editable && s.depth > 1).map(section => <button key={section.id} onClick={() => edit(section)}>{section.title} · dòng {section.line} ✎</button>)}{!artifact.sections.some(s => s.depth > 1) && artifact.sections.map(section => <button key={section.id} onClick={() => edit(section)}>Sửa {section.title} ✎</button>)}</div></details>}
    <details><summary>Markdown nguyên văn · {artifact.hash.slice(0, 10)}</summary><pre>{displayed}</pre></details>
  </dialog>;
}
