// Stage `index.html` + `core/` from the repo root into www/ for Capacitor bundling.
// The app is a backend-less SPA: the bundle IS the app — fully offline, no server.
import { cpSync, mkdirSync, rmSync, readdirSync, unlinkSync } from 'node:fs';
import { join } from 'node:path';

const root = process.cwd();
const www = join(root, 'www');

rmSync(www, { recursive: true, force: true });
mkdirSync(www, { recursive: true });

// Repo-root web assets: index.html + core/ (generated JS constants).
cpSync(join(root, 'index.html'), join(www, 'index.html'));
cpSync(join(root, 'core'), join(www, 'core'), {
  recursive: true,
  // Python sources / caches are not part of the web bundle (JS-only on mobile).
  filter: (src) => !/__pycache__|\.pyc?$/.test(src),
});

// Drop any Python files copied as part of core/ (fees.py etc. stay repo-only).
for (const name of readdirSync(join(www, 'core'))) {
  if (name.endsWith('.py') || name.endsWith('.pyc')) unlinkSync(join(www, 'core', name));
}

console.log('www/ ready: index.html + core/fees.generated.js (offline bundle, no server)');
