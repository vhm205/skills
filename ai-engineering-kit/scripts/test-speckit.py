"""Install real Spec Kit components into scratch projects and check rendered output.

Run with a compatible specify on PATH and Python 3 + PyYAML. Does not invoke coding agents.
"""
from pathlib import Path
import re
import subprocess
import tempfile

import yaml

KIT = Path(__file__).resolve().parent.parent


def run(*args, cwd=None):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{' '.join(map(str, args))}\n{result.stdout}\n{result.stderr}")
    return result.stdout


with tempfile.TemporaryDirectory(prefix='aiek-speckit-') as temp:
    for integration, root in [('codex', '.agents/skills'), ('claude', '.claude/skills'),
                              ('agy', '.agents/skills')]:
        project = Path(temp) / integration
        if integration == 'codex':
            brd = Path(temp) / 'project requirements.md'
            brd.write_text('# Project requirements\n\nUsers need a small first release.\n')
            run('bash', str(KIT / 'scripts/init-project.sh'), str(project),
                '--brd', str(brd), '--integration', integration)
            assert (project / 'docs/inputs' / brd.name).read_bytes() == brd.read_bytes()
            assert (project / root / 'shaping-project/SKILL.md').exists()
        else:
            run('specify', 'init', str(project), '--integration', integration,
                '--ignore-agent-tools', '--non-interactive')
            run('bash', str(KIT / 'scripts/install.sh'), str(project),
                '--harness', integration, '--speckit')
        headings = {
            'specify': 'Feature Brief Intake (AI Engineering Kit)',
            'plan': 'Decision Gate (AI Engineering Kit)',
            'tasks': 'Before generating tasks (AI Engineering Kit)',
            'implement': 'Execution Discipline (AI Engineering Kit)',
        }
        for command, heading in headings.items():
            path = project / root / f'speckit-{command}' / 'SKILL.md'
            text = path.read_text()
            assert heading in text, (integration, command, 'missing wrapper')
            assert 'Mandatory Post-Execution Hooks' in text, (integration, command, 'missing core')
            assert '{CORE_TEMPLATE}' not in text, (integration, command, 'uncomposed wrapper')
            assert not re.search(r'__SPECKIT_COMMAND_[A-Z_]+__', text), (integration, command, 'unrendered command')
        tasks = (project / root / 'speckit-tasks/SKILL.md').read_text()
        assert tasks.index(headings['tasks']) < tasks.index('## Outline')
        for command in ('route', 'ready', 'verify', 'review', 'project-brief',
                        'project-roadmap', 'project-first-slice'):
            assert (project / root / f'speckit-aiek-{command}/SKILL.md').exists()
        hooks = yaml.safe_load((project / '.specify/extensions.yml').read_text())['hooks']
        completion = sorted(hooks['after_implement'], key=lambda hook: hook['priority'])
        assert [hook['command'] for hook in completion] == ['speckit.aiek.verify', 'speckit.aiek.review']
        assert all(hook['enabled'] and not hook['optional'] for hook in completion)
        assert hooks['after_tasks'][0]['command'] == 'speckit.aiek.ready'
        for name in ('aiek-normal', 'aiek-large', 'aiek-project'):
            assert (project / '.specify/workflows' / name / 'workflow.yml').exists()
        project_workflow = yaml.safe_load((project / '.specify/workflows/aiek-project/workflow.yml').read_text())
        steps = project_workflow['steps']
        assert [step['id'] for step in steps] == ['brief', 'constitution', 'roadmap', 'approve-roadmap', 'first-slice']
        assert steps[3]['type'] == 'gate' and steps[3]['on_reject'] == 'abort'
        run('specify', 'workflow', 'info', 'aiek-project', cwd=project)
        print(f'PASS {integration}: real install, four composed commands, project commands, hooks, workflows')
