import { test, expect } from '@playwright/test';
import { writeFile, mkdir } from 'node:fs/promises';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { startServer } from '../src/server';
import { fixture, plan } from './fixture';
let f: Awaited<ReturnType<typeof fixture>>;
let app: Awaited<ReturnType<typeof startServer>>;
test.beforeEach(async ({ page }) => {
  f = await fixture(); app = await startServer({ project: f.project, port: 0, dataDir: f.data, assets: fileURLToPath(new URL('../dist/ui/', import.meta.url)) });
  await page.goto(app.url);
  await page.getByRole('button', { name: 'Chọn feature 001-team-availability' }).click();
  await expect(page.getByRole('heading', { name: 'Feature này xây gì?' })).toBeVisible();
});
test.afterEach(async () => { await app?.close(); await f?.cleanup(); });
test('review source, baseline, live changes and guarded editing', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', error => errors.push(error.message));
  await page.getByRole('button', { name: 'Mở plan.md', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('PASS (planned)');
  await page.getByRole('button', { name: 'Đóng tài liệu nguồn' }).click();
  await page.getByRole('button', { name: 'Thay đổi', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Chưa có mốc review' })).toBeVisible();
  await page.getByRole('button', { name: 'Lưu mốc đã review' }).click();
  await expect(page.getByRole('status')).toContainText('Đã lưu mốc');
  await writeFile(join(f.feature, 'plan.md'), plan.replace('Chọn timezone dùng tính trạng thái.', 'Timezone cần quyết định sau review.'));
  await expect(page.getByText('Timezone cần quyết định sau review.', { exact: false })).toBeVisible({ timeout: 2000 });
  await page.getByRole('button', { name: 'Cần xử lý', exact: true }).click();
  await page.getByRole('button', { name: 'Sửa section', exact: true }).first().click();
  const editor = page.getByRole('dialog');
  const draft = editor.getByLabel('Markdown quyết định');
  await draft.fill('## Decisions Needed\n\nQuyết định: timezone workspace.\n\n');
  await editor.getByRole('button', { name: 'Xem diff', exact: true }).click();
  await editor.getByRole('button', { name: 'Lưu vào tài liệu' }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.getByText('Quyết định: timezone workspace.', { exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});
test('conflict keeps draft and reloads source without silently overwriting', async ({ page }) => {
  await page.getByRole('button', { name: 'Cần xử lý', exact: true }).click();
  await page.getByRole('button', { name: 'Sửa section', exact: true }).first().click();
  const editor = page.getByRole('dialog'); const draft = editor.getByLabel('Markdown quyết định');
  const initial = await draft.inputValue();
  await draft.fill(initial + '\nBản nháp của tôi\n');
  await writeFile(join(f.feature, 'plan.md'), '\n' + plan + '\nExternal code agent edit\n');
  await editor.getByRole('button', { name: 'Xem diff', exact: true }).click();
  await editor.getByRole('button', { name: 'Lưu vào tài liệu' }).click();
  await expect(editor.getByRole('alert')).toContainText('File đã thay đổi');
  await expect(draft).toHaveValue(initial + '\nBản nháp của tôi\n');
  await editor.getByRole('button', { name: 'Tải nguồn mới, giữ bản nháp' }).click();
  await expect(editor.getByRole('alert')).toContainText('Đã tải nguồn mới');
  await expect(draft).toHaveValue(initial + '\nBản nháp của tôi\n');
});
test('responsive layout, keyboard access and untrusted Markdown', async ({ page }, testInfo) => {
  await writeFile(join(f.feature, 'research.md'), '# Notes\n<script>window.__unsafe = true</script>\n\n[unsafe](javascript:alert(1))\n');
  await expect(page.getByRole('button', { name: 'Mở research.md', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Mở research.md', exact: true }).click();
  expect(await page.evaluate(() => '__unsafe' in window)).toBe(false);
  await page.keyboard.press('Escape');
  for (const width of [320, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 960 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
  await page.getByRole('button', { name: 'Tasks', exact: true }).focus(); await page.keyboard.press('Enter');
  await expect(page.getByRole('heading', { name: 'Công việc theo tài liệu' })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('review-desktop.png'), fullPage: true });
});

test('open source follows live updates and reports deletion', async ({ page }) => {
  await page.getByRole('button', { name: 'Mở plan.md', exact: true }).click();
  const source = page.getByRole('dialog');
  await writeFile(join(f.feature, 'plan.md'), plan + '\nNguồn mới khi dialog đang mở\n');
  await expect(source).toContainText('Nguồn mới khi dialog đang mở', { timeout: 2000 });
  await expect(source.getByRole('status')).toContainText('Nguồn đã đổi');
  const { unlink } = await import('node:fs/promises');
  await unlink(join(f.feature, 'plan.md'));
  await expect(source.getByRole('alert')).toContainText('Tài liệu đã bị xóa');
});

test('workflow rounds, task filters and editing ordinary spec sections', async ({ page }) => {
  const flow = page.getByRole('region', { name: 'Trạng thái workflow' });
  await expect(flow).toContainText('Thực hiện · 1/2 task');
  await page.getByRole('button', { name: 'Review tài liệu (3)', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Vòng review hiện tại' })).toBeVisible();
  await page.getByRole('button', { name: 'Lưu mốc đã review' }).click();
  await expect(flow).toContainText('Phân tích: chạy bước này');
  await page.getByRole('button', { name: 'Tasks', exact: true }).click();
  await page.getByLabel('Trạng thái', { exact: true }).selectOption('done');
  await expect(page.locator('.task')).toHaveCount(1); await expect(page.locator('.task')).toContainText('T001');
  await page.getByLabel('Trạng thái', { exact: true }).selectOption('todo');
  await expect(page.locator('.task')).toHaveCount(1); await expect(page.locator('.task')).toContainText('T002');
  await page.getByRole('button', { name: 'Mở spec.md', exact: true }).click();
  await page.getByText('Chỉnh sửa section trong tài liệu này', { exact: true }).click();
  await page.getByRole('button', { name: /Functional Requirements · dòng/ }).click();
  const draft = page.getByLabel('Markdown quyết định');
  await draft.fill('## Functional Requirements\n\n- FR-001: Yêu cầu cập nhật qua UI.\n\n');
  await page.getByRole('button', { name: 'Xem diff', exact: true }).click();
  await page.getByRole('button', { name: 'Lưu vào tài liệu', exact: true }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await page.getByRole('button', { name: /Vòng review/ }).click();
  await expect(page.locator('.review-card')).toHaveCount(1);
  await expect(page.locator('.review-card')).toContainText('spec.md');
});

test('Copilot previews context, calls compatible API and cancels without losing question', async ({ page }) => {
  const { createServer } = await import('node:http');
  let calls = 0;
  const provider = createServer(async (req, res) => {
    let text = ''; for await (const chunk of req) text += chunk.toString();
    const payload = JSON.parse(text); calls++;
    if (payload.messages.at(-1).content === 'wait') return;
    res.setHeader('Content-Type', 'application/json'); res.end(JSON.stringify({ choices: [{ message: { content: 'Còn T002. Nguồn: [specs/001-team-availability/tasks.md:6]' } }] }));
  });
  await new Promise<void>(ok => provider.listen(0, '127.0.0.1', ok));
  const address = provider.address(); if (!address || typeof address === 'string') throw new Error('Missing address');
  const secondFeature = join(f.project, 'specs', '002-other-feature');
  await mkdir(secondFeature); await writeFile(join(secondFeature, 'spec.md'), '# Other feature\n\nInitial requirement\n');
  try {
    await page.getByRole('button', { name: '✦ Trợ lý AI', exact: true }).click();
    await page.getByLabel('Base URL', { exact: true }).fill(`http://127.0.0.1:${address.port}/v1`);
    await page.getByLabel('Model', { exact: true }).fill('test-model');
    await page.getByRole('button', { name: 'Lưu kết nối tạm thời' }).click();
    expect(calls).toBe(0);
    await page.getByText(/Tài liệu sẽ gửi ·/).click();
    await expect(page.getByRole('button', { name: /specs\/001-team-availability\/tasks.md ·/ })).toBeVisible();
    const input = page.getByLabel('Câu hỏi của bạn');
    await input.fill('Còn task nào?'); await page.getByRole('button', { name: 'Gửi câu hỏi', exact: true }).click();
    await expect(page.locator('.chat-answer')).toContainText('Còn T002.'); expect(calls).toBe(1);
    await writeFile(join(f.feature, 'plan.md'), plan + '\nCopilot stale context test\n');
    await expect(page.locator('.chat-answer')).toContainText('Context đã đổi');
    await page.getByLabel('Phạm vi câu hỏi').selectOption('project');
    await input.fill('Project overview'); await page.getByRole('button', { name: 'Gửi câu hỏi', exact: true }).click();
    await expect(page.locator('.chat-answer')).toHaveCount(2);
    await writeFile(join(secondFeature, 'spec.md'), '# Other feature\n\nChanged project requirement\n');
    await expect(page.locator('.chat-answer').last()).toContainText('Context đã đổi');
    await input.fill('wait'); await page.getByRole('button', { name: 'Gửi câu hỏi', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Hủy câu hỏi', exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Hủy câu hỏi', exact: true }).click();
    await expect(page.getByRole('alert')).toContainText('Đã hủy'); await expect(input).toHaveValue('wait');
    await page.getByRole('button', { name: 'Prompt cho agy / agent khác', exact: true }).click();
    await expect(page.getByLabel('Prompt chuyển agent')).toHaveValue(/Copilot stale context test/);
  } finally { provider.closeAllConnections(); await new Promise<void>(ok => provider.close(() => ok())); }
});

test('Normal lane default evidence selection records verification', async ({ page }) => {
  await writeFile(join(f.feature, 'plan.md'), plan.replace('LARGE', 'NORMAL'));
  const flow = page.getByRole('region', { name: 'Trạng thái workflow' });
  await expect(flow.locator('.workflow-map')).not.toContainText('Phân tích');
  await page.getByText('Ghi nhận analyze / worktree / kiểm chứng / review đã chạy', { exact: true }).click();
  await expect(page.getByLabel('Bước đã chạy', { exact: true })).toHaveValue('verify');
  await page.getByLabel('Bằng chứng / kết luận').fill('npm test · exit 0');
  await page.getByRole('button', { name: 'Ghi nhận cho phiên bản docs này', exact: true }).click();
  await expect(flow.locator('.evidence-note')).toContainText('verify');
  expect((await app.storage.load(f.id))?.evidence?.at(-1)?.step).toBe('verify');
});
