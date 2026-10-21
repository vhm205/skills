import { createHash } from 'node:crypto';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import type { Root, RootContent, ListItem } from 'mdast';
import type { Artifact, Section, Task } from './types.js';

export const hash = (value: string | Buffer) => createHash('sha256').update(value).digest('hex');
export const normalize = (value: string) => value.trim().toLocaleLowerCase('en-US');
const parser = unified().use(remarkParse).use(remarkGfm);
const text = (node: RootContent | ListItem): string => {
  if ('value' in node) return node.value;
  if ('children' in node) return node.children.map(child => text(child as RootContent)).join('');
  return '';
};

export function parseArtifact(path: string, content: string): Artifact {
  const bom = content.startsWith('\ufeff') ? 1 : 0;
  const tree = parser.parse(content.slice(bom)) as Root;
  const headings = tree.children.filter(node => node.type === 'heading');
  const sections: Section[] = headings.map((node, index) => {
    const start = node.position!.start.offset! + bom;
    const next = headings.slice(index + 1).find(next => next.depth <= node.depth);
    const end = next ? next.position!.start.offset! + bom : content.length;
    const title = text(node);
    const editable = path.endsWith('.md');
    return { id: `${start}:${node.depth}`, title, depth: node.depth, start, end,
      line: node.position!.start.line, content: content.slice(start, end), editable };
  });
  const tasks: Task[] = [];
  function visit(nodes: RootContent[]) {
    for (const node of nodes) {
      if (node.type === 'listItem' && typeof node.checked === 'boolean') {
        // A parent task owns only its immediate paragraphs, not nested task text.
        const raw = node.children.filter(child => child.type === 'paragraph').map(child => text(child)).join(' ');
        const line = node.position!.start.line;
        const preceding = sections.filter(section => section.line < line);
        const phase = preceding.filter(section => /^(Phase\s+\d+|Giai đoạn\s+\d+)/i.test(section.title)).at(-1)?.title ?? preceding.at(-1)?.title ?? 'Chưa phân nhóm';
        tasks.push({ id: raw.match(/^T\d+\b/)?.[0] ?? `L${line}`, text: raw,
          checked: node.checked, parallel: /\[P\]/.test(raw), story: raw.match(/\[(US\d+)\]/)?.[1] ?? null,
          phase, line, paths: node.children.filter(child => child.type === 'paragraph').flatMap(child =>
            [...content.slice(child.position!.start.offset! + bom, child.position!.end.offset! + bom).matchAll(/`([^`]+)`/g)].map(match => match[1])) });
      }
      if ('children' in node) visit(node.children as RootContent[]);
    }
  }
  visit(tree.children);
  return { id: hash(path).slice(0, 24), path, hash: hash(content), content, sections, tasks };
}

export function declaredLane(artifact?: Artifact) {
  const tree = parser.parse(artifact?.content ?? '') as Root;
  const prose = tree.children.filter(node => node.type === 'paragraph').map(node => text(node)).join('\n');
  const matches = [...prose.matchAll(/^\s*Lane\s*:\s*(SMALL|NORMAL|LARGE)\b/gmi)];
  const values = new Set(matches.map(match => match[1].toUpperCase()));
  return values.size === 1 ? [...values][0] as 'SMALL' | 'NORMAL' | 'LARGE' : null;
}
