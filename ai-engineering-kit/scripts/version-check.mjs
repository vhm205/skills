import { readFile } from 'node:fs/promises';
const root = new URL('../', import.meta.url);
const read = async (name) => JSON.parse(await readFile(new URL(name, root), 'utf8'));
if ((await read('package.json')).version !== (await read('manifest.json')).version) {
  throw new Error('package.json version must match manifest.json');
}
