"""Run with Python 3 + PyYAML; uses disposable projects, no agent or network needed."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

KIT = Path(__file__).resolve().parent.parent
BEGIN = '<!-- ai-engineering-kit:begin -->'
END = '<!-- ai-engineering-kit:end -->'


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='aiek-test-')
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / 'project with spaces'
        self.project.mkdir()

    def install(self, *args, ok=True):
        result = subprocess.run(['bash', str(KIT / 'scripts/install.sh'), str(self.project), *args],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def snapshot(self):
        return {str(p.relative_to(self.project)): p.read_bytes()
                for p in self.project.rglob('*') if p.is_file()}

    def test_dry_run_and_bad_harness_do_not_write(self):
        self.install('--dry-run')
        self.assertEqual(list(self.project.iterdir()), [])
        self.install('--harness', 'unknown', ok=False)
        self.assertEqual(list(self.project.iterdir()), [])
        self.install('--harness', '', ok=False)
        self.assertEqual(list(self.project.iterdir()), [])

    def test_missing_spec_project_fails_before_writes(self):
        self.install('--speckit', ok=False)
        self.assertEqual(list(self.project.iterdir()), [])

    def test_all_harnesses_idempotent_preserves_project_files(self):
        (self.project / 'AGENTS.md').write_text('Project rules.\n')
        (self.project / 'CLAUDE.md').write_text('Local rules.\n')
        self.install()
        count = len(list((KIT / 'skills').glob('*/SKILL.md')))
        for root in ('.agents/skills', '.claude/skills'):
            self.assertEqual(len(list((self.project / root).glob('*/SKILL.md'))), count)
        adapter = self.project / '.aiek/adapter.md'
        adapter.write_text('project-owned commands\n')
        before = self.snapshot()
        self.install()
        self.assertEqual(self.snapshot(), before)
        for name in ('AGENTS.md', 'CLAUDE.md'):
            text = (self.project / name).read_text()
            self.assertEqual(text.count(BEGIN), 1)
            self.assertEqual(text.count(END), 1)

    def test_link_mode_copies_adapter_and_force_refreshes_skill(self):
        self.install('--harness', 'codex,agy', '--link')
        skill = self.project / '.agents/skills/executing-task'
        self.assertTrue(skill.is_symlink())
        self.assertFalse((self.project / '.aiek/adapter.md').is_symlink())
        self.assertFalse((self.project / '.claude').exists())
        self.install('--harness', 'codex', '--force')
        self.assertFalse(skill.is_symlink())
        self.assertTrue((skill / 'SKILL.md').exists())

    def test_malformed_markers_fail_without_mutation(self):
        for text in (BEGIN + '\nkeep me\n', END + '\n' + BEGIN + '\n',
                     BEGIN + '\n' + END + '\n' + BEGIN + '\n' + END + '\n'):
            (self.project / 'AGENTS.md').write_text(text)
            before = self.snapshot()
            self.install(ok=False)
            self.assertEqual(self.snapshot(), before)
            self.assertFalse((self.project / '.aiek').exists())

    def test_valid_block_preserves_surrounding_rules(self):
        (self.project / 'AGENTS.md').write_text('before\n' + BEGIN + '\nold\n' + END + '\nafter\n')
        self.install('--harness', 'claude')
        text = (self.project / 'AGENTS.md').read_text()
        self.assertTrue(text.startswith('before\n' + BEGIN))
        self.assertTrue(text.endswith(END + '\nafter\n'))
        self.assertEqual((self.project / 'CLAUDE.md').read_text(), '@AGENTS.md\n')
        self.assertFalse((self.project / '.agents').exists())


class BootstrapTests(unittest.TestCase):
    def test_nonempty_target_and_missing_brd_leave_existing_files_untouched(self):
        with tempfile.TemporaryDirectory(prefix='aiek-bootstrap-') as temp:
            root = Path(temp)
            target = root / 'existing'
            target.mkdir()
            existing = target / 'keep.txt'
            existing.write_text('keep')
            brd = root / 'requirements.md'
            brd.write_text('# Requirements')
            script = KIT / 'scripts/init-project.sh'
            for args in ((str(target), '--brd', str(brd), '--integration', 'codex'),
                         (str(root / 'new'), '--brd', str(root / 'missing.md'), '--integration', 'codex')):
                result = subprocess.run(['bash', str(script), *args], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertEqual(existing.read_text(), 'keep')
            self.assertFalse((root / 'new').exists())


class ValidationTests(unittest.TestCase):
    def test_generated_trees_are_not_kit_sources(self):
        with tempfile.TemporaryDirectory(prefix='aiek-check-') as temp:
            copy = Path(temp) / KIT.name
            shutil.copytree(KIT, copy, ignore=shutil.ignore_patterns(
                '.git', '__pycache__', '.worktrees', 'node_modules', 'dist',
                'coverage', 'test-results', 'playwright-report', '.cache'))
            for directory in ('node_modules/dependency', 'dist', 'test-results', '.worktrees'):
                target = copy / directory
                target.mkdir(parents=True, exist_ok=True)
                (target / 'SKILL.md').write_text('invalid generated skill')
                (target / 'extension.yml').write_text('schema_version: wrong')
            result = subprocess.run([sys.executable, str(copy / 'scripts/check.py'), str(copy)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_broken_contracts(self):
        cases = [
            ('skills/executing-task/SKILL.md', lambda s: s.replace(s.splitlines()[2], 'description: Broken YAML: unquoted colon')),
            ('skills/executing-task/SKILL.md', lambda s: s.replace('description:', 'extra: value\ndescription:', 1)),
            ('skills/executing-task/SKILL.md', lambda s: s.replace('description:', 'name: duplicate\ndescription:', 1)),
            ('skills/executing-task/SKILL.md', lambda s: s + '\n[broken](references/missing.md)\n'),
            ('speckit/presets/aiek-core/commands/speckit.tasks.md', lambda s: s.replace('{CORE_TEMPLATE}', '')),
            ('manifest.json', lambda s: s.replace('"name": "shaping-feature"', '"name": "absent"')),
        ]
        for name, mutate in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory(prefix='aiek-check-') as temp:
                copy = Path(temp) / KIT.name
                shutil.copytree(KIT, copy, ignore=shutil.ignore_patterns('.git', '__pycache__', '.worktrees', 'node_modules', 'dist', 'coverage', 'test-results', 'playwright-report', '.cache'))
                path = copy / name
                path.write_text(mutate(path.read_text()))
                result = subprocess.run([sys.executable, str(copy / 'scripts/check.py'), str(copy)],
                                        capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn('FAIL', result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
