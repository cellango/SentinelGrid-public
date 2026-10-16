import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');
const SOURCE_ROOT = path.join(projectRoot, 'src');
const SOURCE_FILE_PATTERN = /\.(?:[cm]?[jt]sx?|css|mdx)$/;

const LEGACY_CLASS_PATTERN =
  /\b(?:bg-white|bg-gray-\d{2,3}(?:\/\d{1,3})?|text-gray-\d{2,3}|border-gray-\d{2,3}|ring-gray-\d{2,3})\b/g;

async function collectSourceFiles(root, base = root) {
  const entries = await fs.readdir(root, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    const absolutePath = path.join(root, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await collectSourceFiles(absolutePath, base)));
      continue;
    }
    if (!SOURCE_FILE_PATTERN.test(entry.name)) {
      continue;
    }
    files.push(path.relative(base, absolutePath));
  }

  return files;
}

async function main() {
  const violations = [];
  const sourceFiles = await collectSourceFiles(SOURCE_ROOT);

  for (const relativePath of sourceFiles) {
    const absolutePath = path.join(SOURCE_ROOT, relativePath);
    const source = await fs.readFile(absolutePath, 'utf8');
    const matches = Array.from(new Set(source.match(LEGACY_CLASS_PATTERN) || []));

    if (matches.length > 0) {
      violations.push({ relativePath: path.posix.join('src', relativePath.split(path.sep).join(path.posix.sep)), matches });
    }
  }

  if (violations.length === 0) {
    console.log('No legacy color classes found anywhere in frontend/src.');
    return;
  }

  console.error('Legacy color classes detected in frontend/src:');
  for (const violation of violations) {
    console.error(`- ${violation.relativePath}: ${violation.matches.join(', ')}`);
  }
  process.exitCode = 1;
}

main().catch((error) => {
  console.error('Failed to run legacy color class guardrail.');
  console.error(error);
  process.exitCode = 1;
});
