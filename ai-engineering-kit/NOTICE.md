# Third-Party Notices

The AI Engineering Kit adapts ideas, structure and some wording from the projects below.
No upstream code is vendored. Each adapted file carries a one-line attribution footer.

## obra/superpowers

Source: https://github.com/obra/superpowers (reviewed at v7.0.0, commit bb92a77, 2026-10-09)

Adapted into: `skills/shaping-feature` (from brainstorming), `skills/executing-task`
(executing-plans, subagent-driven-development), `skills/verifying-change`
(verification-before-completion), `skills/systematic-debugging`, `skills/using-worktrees`
(using-git-worktrees), `skills/parallel-development` (dispatching-parallel-agents,
subagent-driven-development), `skills/reviewing-change` (requesting-code-review,
receiving-code-review), `skills/test-driven-development`, `skills/finishing-branch`
(finishing-a-development-branch).

```text
MIT License

Copyright (c) 2025 Jesse Vincent

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## github/spec-kit

Source: https://github.com/github/spec-kit (reviewed at 1.2.2.dev0, commit c6a4c18, 2026-10-16)

The kit does not copy Spec Kit. It ships an extension, a preset and workflows written against
Spec Kit's published manifest formats, and its preset wraps (does not replace) the core
`specify`, `plan`, `tasks` and `implement` commands at install time.

```text
MIT License

Copyright GitHub, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
