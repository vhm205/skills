export interface Section {
  id: string; title: string; depth: number; start: number; end: number;
  line: number; content: string; editable: boolean;
}
export interface Task {
  id: string; text: string; checked: boolean; parallel: boolean;
  story: string | null; phase: string; line: number; paths: string[];
}
export interface Artifact {
  id: string; path: string; hash: string; content: string;
  sections: Section[]; tasks: Task[]; error?: string;
}
export interface FeatureSummary { id: string; name: string }
export interface Feature {
  id: string; revision: string; artifacts: Artifact[]; warnings: string[];
  lane: 'SMALL' | 'NORMAL' | 'LARGE' | null; clarifications: number;
}
export interface ProjectInfo {
  name: string; root: string; kitInstalled: boolean; features: FeatureSummary[];
  context: Artifact[]; warnings: string[];
}
export interface ProjectSummary {
  name: string; root: string; active: boolean; featureCount: number;
  kitInstalled: boolean;
}
export interface ProjectsResponse {
  projects: ProjectSummary[];
  active: string;
}
export interface CopilotModel {
  id: string;
  name: string;
  description?: string;
}
export interface Baseline {
  version: 1; feature: string; savedAt: string; revision: string;
  files: Record<string, string>;
  history?: ReviewRound[];
  evidence?: CommandEvidence[];
}
export interface ReviewRound { at: string; revision: string; changed: string[]; completed: number; total: number }
export interface CommandEvidence { step: string; note: string; at: string; revision: string }
export interface WorkflowStep { id: string; label: string; command: string; state: 'missing' | 'available' | 'changed' | 'reviewed' | 'reported' | 'stale' | 'unknown'; paths: string[]; detail: string }
export interface Workflow { steps: WorkflowStep[]; current: string; next: string; action: string; command: string; pending: string[]; completed: number; total: number; evidence: CommandEvidence[] }
export interface Change {
  path: string; status: 'added' | 'modified' | 'deleted';
  before: string; after: string; headings: string[];
  changedHeadings: string[];
  taskProgress: { before: number; after: number; totalBefore: number; totalAfter: number };
}
export interface ReviewState { baseline: Baseline | null; changes: Change[] }
export class AppError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
