import { diffLines } from 'diff';
export function Diff({ before, after }: { before: string; after: string }) {
  return <pre className="diff" aria-label="So sánh nội dung">{diffLines(before, after).map((part, index) =>
    <span key={index} className={part.added ? 'added' : part.removed ? 'removed' : ''}>{part.value.split('\n').map((line, i, lines) =>
      i === lines.length - 1 && !line ? null : <span className="diff-line" key={i}><span aria-hidden="true">{part.added ? '+ ' : part.removed ? '− ' : '  '}</span>{line}{'\n'}</span>)}</span>)}</pre>;
}
