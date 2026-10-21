import type { Baseline, Feature, Workflow, WorkflowStep } from './types.js';

export const evidenceSteps = ['analyze', 'worktree', 'verify', 'review'] as const;
export function workflow(feature: Feature, baseline: Baseline | null): Workflow {
  const docs = feature.artifacts.filter(a => !a.error);
  const tasks = docs.find(a => a.path === 'tasks.md')?.tasks ?? [];
  const completed = tasks.filter(t => t.checked).length;
  const evidence = baseline?.evidence ?? [];
  const pending = docs.filter(a => !baseline || baseline.files[a.path] !== a.content).map(a => a.path);
  const deleted = Object.keys(baseline?.files ?? {}).filter(path => !feature.artifacts.some(a => a.path === path));
  pending.push(...deleted);
  const steps: WorkflowStep[] = [];
  const addDoc = (id: string, label: string, command: string, paths: string[]) => {
    const present = docs.filter(a => paths.includes(a.path));
    const state = !present.length ? 'missing' : !baseline ? 'available' : present.some(a => pending.includes(a.path)) ? 'changed' : 'reviewed';
    steps.push({ id, label, command, paths: present.map(a => a.path), state,
      detail: state === 'missing' ? 'Chưa có tài liệu' : state === 'changed' ? 'Tài liệu đã đổi · cần review' : state === 'reviewed' ? 'Tài liệu khớp mốc đã review' : 'Đã có tài liệu · chưa lưu mốc review' });
  };
  const addEvidence = (id: string, label: string, command: string) => {
    const item = evidence.findLast(item => item.step === id);
    steps.push({ id, label, command, paths: [], state: !item ? 'unknown' : item.revision === feature.revision ? 'reported' : 'stale',
      detail: !item ? 'Chưa có ghi nhận thực thi' : item.revision !== feature.revision ? 'Docs đã đổi sau ghi nhận' : 'Bạn ghi nhận · UI chưa xác thực thực thi' });
  };
  addDoc('specify', 'Yêu cầu', '/speckit-specify', ['spec.md']);
  steps.push({ id: 'clarify', label: 'Làm rõ', command: '/speckit-clarify', paths: docs.some(a => a.path === 'spec.md') ? ['spec.md'] : [],
    state: feature.clarifications ? 'changed' : 'unknown', detail: feature.clarifications ? `${feature.clarifications} marker cần làm rõ` : 'Không thấy marker chưa giải quyết; chưa xác nhận command đã chạy' });
  addDoc('plan', 'Thiết kế', '/speckit-plan', docs.filter(a => /^(plan|research|data-model|quickstart)\.md$|^contracts\//.test(a.path)).map(a => a.path));
  addDoc('tasks', 'Tasks', '/speckit-tasks', ['tasks.md']);
  if (feature.lane === 'LARGE') { addEvidence('analyze', 'Phân tích', '/speckit-analyze'); addEvidence('worktree', 'Cô lập', 'using-worktrees'); }
  steps.push({ id: 'execute', label: 'Thực hiện', command: 'executing-task', paths: ['tasks.md'], state: tasks.length ? 'available' : 'missing', detail: `${completed}/${tasks.length} task được tick trong docs` });
  addEvidence('verify', 'Kiểm chứng', 'verifying-change');
  addEvidence('review', feature.lane === 'LARGE' ? 'Review độc lập' : 'Review', 'reviewing-change');
  if (feature.lane === 'SMALL') steps.splice(0, steps.findIndex(s => s.id === 'execute'));
  let next = !docs.some(a => a.path === 'spec.md') ? 'specify' : feature.clarifications ? 'clarify' : !docs.some(a => a.path === 'plan.md') ? 'plan' : !docs.some(a => a.path === 'tasks.md') ? 'tasks' : '';
  if (feature.lane === 'SMALL') next = '';
  if (!next && pending.length) next = 'review-docs';
  if (!next && !feature.lane) next = 'classify';
  if (!next && feature.lane === 'LARGE') next = ['analyze', 'worktree'].find(id => !steps.some(s => s.id === id && s.state === 'reported')) ?? '';
  if (!next && (!tasks.length || completed < tasks.length)) next = 'execute';
  if (!next) next = ['verify', 'review'].find(id => !steps.some(s => s.id === id && s.state === 'reported')) ?? 'human-review';
  const target = steps.find(s => s.id === next);
  const current = tasks.length && completed > 0 ? `Thực hiện · ${completed}/${tasks.length} task` : docs.some(a => a.path === 'tasks.md') ? 'Đã có task breakdown' : docs.some(a => a.path === 'plan.md') ? 'Đã có thiết kế' : docs.some(a => a.path === 'spec.md') ? 'Đã có yêu cầu' : 'Chuẩn bị yêu cầu';
  const action = next === 'review-docs' ? `Review ${pending.length} tài liệu mới, sửa hoặc xóa; sau đó lưu mốc.` : next === 'classify' ? 'Xác nhận lane trong plan.md để chọn đúng các gate.' : next === 'human-review' ? 'Đối chiếu bằng chứng và chuyển Human Review / PR. UI chưa xác nhận DONE.' : next === 'execute' ? `Tiếp tục task chưa hoàn thành${tasks.find(t => !t.checked) ? `: ${tasks.find(t => !t.checked)!.id}` : '; kiểm tra tasks.md'}.` : next === 'clarify' ? 'Giải quyết marker NEEDS CLARIFICATION trong spec.' : `${target?.label ?? next}: chạy bước này trong agent, rồi quay lại review output.`;
  return { steps, current, next, action, command: target?.command ?? '', pending, completed, total: tasks.length, evidence };
}
