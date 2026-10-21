import { useState } from 'react';
import type { Artifact, Feature, Section } from '../src/types';
import type { FeatureResponse } from './api';
import { Markdown } from './Markdown';
import { Diff } from './Diff';
import type { SourceSelection } from './Source';
import type { EditSelection } from './Editor';
import { ReviewInbox } from './Workflow';
export type View = 'overview' | 'round' | 'decisions' | 'changes' | 'tasks' | 'evidence';
export const views: [View, string][] = [['overview', 'Tổng quan'], ['round', 'Vòng review'], ['decisions', 'Cần xử lý'], ['changes', 'Thay đổi'], ['tasks', 'Tasks'], ['evidence', 'Bằng chứng']];
interface Props { data: FeatureResponse; view: View; source: (s: SourceSelection) => void; edit: (s: EditSelection) => void }
const sectionIs = (section: Section, expression: RegExp) => expression.test(section.title);
function Excerpt({ artifact, section, source }: { artifact: Artifact; section: Section; source: Props['source'] }) {
  return <article className="excerpt"><button className="source-link" onClick={() => source({ artifact, line: section.line, content: section.content })}>{artifact.path} · dòng {section.line} ↗</button><Markdown>{section.content}</Markdown></article>;
}
function Overview({ feature, source }: { feature: Feature; source: Props['source'] }) {
  const spec = feature.artifacts.find(a => a.path === 'spec.md');
  const sections = spec?.sections.filter(s => sectionIs(s, /^(problem|summary|overview|user stor|user scenario|functional requirement|acceptance|success criteria|scope|phạm vi|mục tiêu)/i));
  // Prefer child stories/requirements over an enclosing section that repeats them.
  const selected = sections?.filter(s => !sections.some(other => other.start > s.start && other.start < s.end));
  return <>
    <div className="section-heading"><div><h2>Feature này xây gì?</h2><p className="muted">Trích trực tiếp từ spec, kèm vị trí nguồn.</p></div></div>
    <div className="story-grid">{spec?.sections.filter(s => /user story|câu chuyện/i.test(s.title)).map(s => <button key={s.id} className="story-card" onClick={() => source({ artifact: spec, line: s.line, content: s.content })}><span className="badge">{s.title.match(/P\d/)?.[0] ?? 'Story'}</span><strong>{s.title.replace(/\s*\(Priority:.*?\)/i, '')}</strong><span>{s.content.split('\n').slice(1).map(line => line.trim()).find(Boolean)?.slice(0, 180)}</span><small>Xem yêu cầu &amp; acceptance ↗</small></button>)}</div>
    {selected?.length ? selected.filter(s => !/user story/i.test(s.title)).map(s => <details className="spec-detail" key={s.id}><summary>{s.title}</summary><Excerpt artifact={spec!} section={s} source={source} /></details>) :
      <div className="empty"><h3>Chưa nhận diện được cấu trúc spec</h3><p>Mở tài liệu nguồn để đọc nội dung hiện có.</p></div>}
    <h2>Điều kiện cần đối chiếu</h2>
    <ul className="observations"><li>{feature.artifacts.some(a => a.path === 'plan.md' && !a.error) ? '✓ Đã đọc plan.md' : '○ Chưa đọc được plan.md'}</li>
      <li>{feature.artifacts.some(a => a.path === 'tasks.md' && !a.error) ? '✓ Đã đọc tasks.md' : '○ Chưa đọc được tasks.md'}</li>
      <li>{feature.clarifications} marker NEEDS CLARIFICATION trong spec</li><li>Readiness, analyze và review: cần đối chiếu bằng chứng thực thi.</li></ul>
  </>;
}
function Tasks({ feature, source }: { feature: Feature; source: Props['source'] }) {
  const [groupBy, setGroupBy] = useState('phase');
  const [status, setStatus] = useState('all');
  const artifact = feature.artifacts.find(a => a.path === 'tasks.md');
  const tasks = artifact?.tasks ?? [];
  const groups = new Map<string, typeof tasks>();
  for (const task of tasks.filter(t => status === 'all' || (status === 'done' ? t.checked : !t.checked))) {
    const key = groupBy === 'story' ? task.story ?? 'Chưa gắn user story' : task.phase;
    groups.set(key, [...(groups.get(key) ?? []), task]);
  }
  return <><div className="section-heading"><div><h2>Công việc theo tài liệu</h2><p className="muted">Checkbox phản ánh khai báo; [P] là ứng viên song song.</p></div>
    <div className="task-controls"><label>Nhóm theo <select aria-label="Nhóm theo" value={groupBy} onChange={e => setGroupBy(e.target.value)}><option value="phase">Phase</option><option value="story">User story</option></select></label><label>Trạng thái <select aria-label="Trạng thái" value={status} onChange={e => setStatus(e.target.value)}><option value="all">Tất cả</option><option value="todo">Chưa hoàn thành</option><option value="done">Đã hoàn thành</option></select></label></div></div>
    <div className="phase-progress">{[...new Set(tasks.map(t => t.phase))].map(phase => { const items = tasks.filter(t => t.phase === phase); const done = items.filter(t => t.checked).length; return <div key={phase}><div><strong>{phase}</strong><span>{done}/{items.length}</span></div><progress value={done} max={items.length} aria-label={`Tiến độ ${phase}`} /></div>; })}</div>
    {!tasks.length && <p className="empty">Chưa có checkbox task được nhận diện.</p>}
    {[...groups].map(([group, items]) => <section key={group} className="task-group"><h3>{group} <span className="muted">{items.filter(t => t.checked).length}/{items.length}</span></h3>
      {items.map(task => <div className="task" key={task.line}><span aria-label={task.checked ? 'Đã tick trong tài liệu' : 'Chưa tick'} className={task.checked ? 'task-check checked' : 'task-check'}>{task.checked ? '✓' : '○'}</span>
        <div>{task.text.length > 180 ? <details className="task-detail"><summary><strong>{task.id}</strong>{task.parallel && <span className="badge">Song song [P]</span>}{task.story && <span className="badge">{task.story}</span>} {task.text.replace(/^T\d+\s*(?:\[(?:P|US\d+)\]\s*)*/, '').slice(0, 150)}…</summary><p>{task.text}</p></details> : <p>{task.text}</p>}<button className="source-link" onClick={() => source({ artifact: artifact!, line: task.line })}>tasks.md · dòng {task.line} ↗</button></div></div>)}</section>)}
    {artifact?.content.includes('Verify:') && <details><summary>Checkpoint kiểm chứng</summary><Markdown>{artifact.content.split('\n').filter(line => line.includes('Verify:')).join('\n\n')}</Markdown></details>}
  </>;
}
export function FeatureView({ data, view, source, edit }: Props) {
  const { feature, review } = data;
  if (view === 'round') return <ReviewInbox data={data} source={source} />;
  if (view === 'overview') return <Overview feature={feature} source={source} />;
  if (view === 'tasks') return <Tasks feature={feature} source={source} />;
  if (view === 'decisions') {
    const sections = feature.artifacts.flatMap(artifact => artifact.sections.filter(s => sectionIs(s, /decision|clarification|quyết định|làm rõ/i)).map(section => ({ artifact, section })));
    return <><h2>Quyết định và làm rõ</h2><p className="muted">Nội dung cần đối chiếu, không tự xác nhận đang chặn workflow.</p>
      {!sections.length && <p className="empty">Chưa tìm thấy section quyết định hoặc clarification. Xem tài liệu nguồn nếu dùng heading khác.</p>}
      {sections.map(({ artifact, section }) => <section key={artifact.id + section.id} className="decision"><Excerpt artifact={artifact} section={section} source={source} />
        {section.editable ? <button onClick={() => edit({ featureId: feature.id, artifact, section })}>Sửa section</button> : <p className="muted">Heading này chỉ hỗ trợ đọc trong v1.</p>}</section>)}</>;
  }
  if (view === 'changes') return <><h2>Thay đổi từ mốc review</h2>
    {data.reviewError && <p role="alert" className="notice danger">{data.reviewError}</p>}
    {!review.baseline ? <div className="empty"><h3>Chưa có mốc review</h3><p>Đọc tài liệu rồi bấm “Lưu mốc đã review”. Mốc bao gồm cả thay đổi chưa commit.</p></div> :
      <><p className="muted">Mốc lưu lúc {new Date(review.baseline.savedAt).toLocaleString('vi-VN')}</p>
        {!review.changes.length && <p className="empty">Không có thay đổi so với mốc đã lưu.</p>}
        {review.changes.map(change => <section className="change" key={change.path}><h3><span className="badge">{{ added: 'Thêm', modified: 'Sửa', deleted: 'Xóa' }[change.status]}</span> {change.path}</h3>
          {!!change.changedHeadings.length && <p className="muted">Section đã đổi: {change.changedHeadings.join(' · ')}</p>}
          <Diff before={change.before} after={change.after} /></section>)}</>}
  </>;
  const evidence = feature.artifacts.flatMap(artifact => artifact.sections.filter(s => /verification|checks run|review findings|kiểm chứng|xác minh/i.test(s.title)).map(section => ({ artifact, section })));
  return <><h2>Bằng chứng và giới hạn xác minh</h2><p className="notice">Chưa có kết quả thực thi được xác thực bởi UI. Nội dung dưới đây là khai báo trong tài liệu; PASS (planned) không chứng minh gate đã pass.</p>
    {evidence.length ? evidence.map(({ artifact, section }) => <Excerpt key={artifact.id + section.id} artifact={artifact} section={section} source={source} />) :
      <p className="empty">Chưa tìm thấy section kiểm chứng/review. Kết quả chỉ nằm trong chat không được đọc từ project.</p>}</>;
}
