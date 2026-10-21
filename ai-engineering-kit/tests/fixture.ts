import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
export const spec = `# Feature: Team availability

## User Scenarios & Testing

### User Story 1 - Xem lịch tuần (Priority: P1)

Thành viên xem lịch tuần của workspace.

**Acceptance Scenarios**:
1. Given thành viên, when mở lịch, then thấy các ngày trong tuần.

## Functional Requirements

- **FR-001**: Thành viên tự cập nhật lịch.

## Clarifications

- Q: Timezone nào? A: Workspace.

## Success Criteria

- Xem lịch tuần dưới một phút.
`;
export const plan = `# Plan

**Lane**: LARGE (schema and permissions)

## Decisions Needed

Chọn timezone dùng tính trạng thái.

| Option | Trade-offs |
| --- | --- |
| Workspace | Nhất quán |
| Cá nhân | Linh hoạt |

## Verification

PASS (planned). Chưa chạy kiểm chứng.

## Key Design Decisions

Một row mỗi người mỗi ngày.
`;
export const tasks = `# Tasks

## Phase 1: Foundation

- [x] T001 [US1] Create model in \`src/model.ts\`.
- [ ] T002 [P] [US1] Render calendar in \`ui/calendar.tsx\`.

Checkpoint — Verify: npm test
`;
export async function fixture() {
  const directory = await mkdtemp(join(tmpdir(), 'aiek-review-'));
  const project = join(directory, 'project with spaces');
  const feature = join(project, 'specs', '001-team-availability');
  const data = join(directory, 'user-data');
  await mkdir(feature, { recursive: true });
  await mkdir(join(project, '.aiek', 'core'), { recursive: true });
  await writeFile(join(project, '.aiek', 'core', 'WORKFLOW.md'), '# Canonical workflow\n');
  await writeFile(join(project, '.aiek', 'adapter.md'), '---\nverify:\n  test: npm test\n---\n');
  await Promise.all([writeFile(join(feature, 'spec.md'), spec), writeFile(join(feature, 'plan.md'), plan), writeFile(join(feature, 'tasks.md'), tasks)]);
  return { directory, project, feature, data, id: '001-team-availability', cleanup: () => rm(directory, { recursive: true, force: true }) };
}
