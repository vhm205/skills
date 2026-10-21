import { describe, expect, it } from 'vitest';
import { declaredLane, parseArtifact } from '../src/parser';
import { plan, spec, tasks } from './fixture';

describe('Markdown source index', () => {
  it('extracts declared lane without certifying readiness', () => {
    const artifact = parseArtifact('plan.md', plan);
    expect(declaredLane(artifact)).toBe('LARGE');
    expect(artifact).not.toHaveProperty('ready');
    expect(artifact.sections.find(s => s.title === 'Verification')?.content).toContain('PASS (planned)');
  });
  it('extracts GFM tasks, phases, stories, paths and source lines', () => {
    const artifact = parseArtifact('tasks.md', tasks);
    expect(artifact.tasks).toHaveLength(2);
    expect(artifact.tasks[0]).toMatchObject({ checked: true, id: 'T001', story: 'US1', paths: ['src/model.ts'], phase: 'Phase 1: Foundation' });
    expect(artifact.tasks[1].parallel).toBe(true);
    expect(tasks.split('\n')[artifact.tasks[1].line - 1]).toContain('T002');
  });
  it('ignores fenced checkbox examples and preserves exact CRLF source slices', () => {
    const raw = '# Spec\r\n\r\n## CLARIFICATIONS\r\n\r\nTiếng Việt 🪴\r\n\r\n```md\r\n- [x] T999 fake\r\n```\r\n\r\n## Next\r\nTail\r\n';
    const artifact = parseArtifact('spec.md', raw);
    expect(artifact.tasks).toHaveLength(0);
    const section = artifact.sections.find(s => s.title === 'CLARIFICATIONS')!;
    expect(section.content).toBe(raw.slice(section.start, section.end));
    expect(section.content).toContain('🪴');
    expect(raw.slice(section.end)).toBe('## Next\r\nTail\r\n');
  });
  it('indexes editable Markdown sections without losing unique position IDs', () => {
    expect(parseArtifact('research.md', plan).sections.every(s => s.editable)).toBe(true);
    expect(parseArtifact('spec.md', spec).sections.filter(s => s.editable).length).toBeGreaterThan(1);
    expect(parseArtifact('plan.md', '## Decisions Needed\nOne\n## Decisions Needed\nTwo').sections.map(s => s.id)).toEqual(['0:2', '24:2']);
  });
  it('handles empty/custom documents and conflicting lanes', () => {
    expect(parseArtifact('spec.md', '').sections).toEqual([]);
    expect(declaredLane(parseArtifact('plan.md', 'Lane: SMALL\nLane: LARGE'))).toBeNull();
    expect(declaredLane(parseArtifact('plan.md', 'Lane: NORMAL'))).toBe('NORMAL');
    expect(declaredLane(parseArtifact('plan.md', '```text\nLane: LARGE\n```'))).toBeNull();
  });
  it('keeps the enclosing phase when Spec Kit nests test and implementation headings', () => {
    const artifact = parseArtifact('tasks.md', '# Tasks\n\n## Phase 3: User Story 1\n\n### Tests for User Story 1\n\n- [x] T011 Test\n\n### Implementation for User Story 1\n\n- [ ] T012 Implement\n');
    expect(artifact.tasks.map(t => t.phase)).toEqual(['Phase 3: User Story 1', 'Phase 3: User Story 1']);
  });
});
