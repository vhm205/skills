"""Run with Python 3 + PyYAML; uses disposable projects, no agent or network needed."""
import json
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


class ProfileTests(unittest.TestCase):
    """Installer profiles, --only/--skip and the installed helper script set (T18/T24)."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='aiek-profile-')
        self.addCleanup(self.temp.cleanup)
        self.manifest = json.loads((KIT / 'manifest.json').read_text())

    def new_project(self, name):
        project = Path(self.temp.name) / name
        project.mkdir()
        return project

    def install(self, project, *args, ok=True):
        result = subprocess.run(
            ['bash', str(KIT / 'scripts/install.sh'), str(project), *args],
            text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def installed_skills(self, project):
        root = project / '.agents/skills'
        return {path.name for path in root.iterdir() if path.is_dir()} if root.is_dir() else set()

    def test_manifest_profiles_are_consistent(self):
        profiles = self.manifest['profiles']
        all_skills = {item['name'] for item in self.manifest['skills']}
        self.assertEqual(set(profiles['full']), all_skills)
        self.assertEqual(len(profiles['core']), 11)
        self.assertEqual(len(profiles['discovery']), 4)
        self.assertEqual(set(profiles['core']) | set(profiles['discovery']), all_skills)
        self.assertFalse(set(profiles['core']) & set(profiles['discovery']))

    def test_profiles_install_expected_skill_counts(self):
        for profile in ('core', 'discovery', 'full'):
            with self.subTest(profile=profile):
                project = self.new_project('profile-' + profile)
                self.install(project, '--harness', 'codex', '--profile', profile)
                expected = set(self.manifest['profiles'][profile])
                self.assertEqual(self.installed_skills(project), expected)
                self.assertEqual(len(expected), {'core': 11, 'discovery': 4, 'full': 15}[profile])
                # core never drags discovery skills in, and vice versa
                if profile == 'core':
                    self.assertFalse(
                        set(self.manifest['profiles']['discovery']) & self.installed_skills(project))
                if profile == 'discovery':
                    self.assertFalse(
                        set(self.manifest['profiles']['core']) & self.installed_skills(project))

    def test_only_and_skip(self):
        project = self.new_project('only')
        self.install(project, '--harness', 'codex', '--only', 'executing-task,verifying-change')
        self.assertEqual(self.installed_skills(project), {'executing-task', 'verifying-change'})

        project = self.new_project('skip')
        self.install(project, '--harness', 'codex', '--skip', 'exploring-idea,test-driven-development')
        self.assertEqual(len(self.installed_skills(project)), 13)
        self.assertNotIn('exploring-idea', self.installed_skills(project))
        self.assertIn('verifying-change', self.installed_skills(project))

        project = self.new_project('profile-skip')
        self.install(project, '--harness', 'codex', '--profile', 'core', '--skip', 'executing-task')
        self.assertEqual(len(self.installed_skills(project)), 10)
        self.assertNotIn('executing-task', self.installed_skills(project))

    def test_invalid_selection_fails_before_writing(self):
        cases = [
            ('--profile', 'nope'),
            ('--only', 'nope'),
            ('--only', 'executing-task,nope'),
            ('--skip', 'nope'),
            ('--only', 'executing-task', '--skip', 'executing-task'),
        ]
        for args in cases:
            with self.subTest(args=args):
                project = self.new_project('invalid-' + '-'.join(args).replace('/', '_'))
                result = self.install(project, '--harness', 'codex', *args, ok=False)
                self.assertTrue(result.stderr.strip(), result.stdout)
                self.assertEqual(list(project.iterdir()), [])

    def test_dry_run_for_each_profile_writes_nothing(self):
        for profile in ('core', 'discovery', 'full'):
            with self.subTest(profile=profile):
                project = self.new_project('dry-' + profile)
                self.install(project, '--harness', 'codex', '--profile', profile, '--dry-run')
                self.assertEqual(list(project.iterdir()), [])

    def test_adapter_never_overwritten_without_force(self):
        project = self.new_project('adapter')
        self.install(project, '--harness', 'codex')
        adapter = project / '.aiek/adapter.md'
        adapter.write_text('project-owned commands\n')
        self.install(project, '--harness', 'codex')
        self.assertEqual(adapter.read_text(), 'project-owned commands\n')
        self.install(project, '--harness', 'codex', '--force')
        self.assertNotEqual(adapter.read_text(), 'project-owned commands\n')

    def test_helper_scripts_installed_and_runnable(self):
        project = self.new_project('scripts')
        self.install(project, '--harness', 'codex', '--profile', 'core')
        installed = project / '.aiek/scripts'
        expected = {Path(entry).name for entry in self.manifest['scripts']}
        self.assertEqual({path.name for path in installed.iterdir()}, expected)
        self.assertEqual(len(expected), 5)
        for name in ('resolve_adapter.py', 'verify.py', 'worktree.py', 'traceability.py'):
            result = subprocess.run(
                [sys.executable, str(installed / name), '--help'],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, name + ': ' + result.stderr)
            self.assertIn('usage', (result.stdout + result.stderr).lower(), name)
        # The installed resolver runs standalone against the installed project.
        result = subprocess.run(
            [sys.executable, str(installed / 'resolve_adapter.py'),
             '--repo', str(project), '--json'],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(Path(payload['adapter']['repo']), project.resolve())
        self.assertIn('verify', payload['adapter'])


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
