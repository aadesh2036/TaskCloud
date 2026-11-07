// config.json is generated and git-ignored, so a fresh clone has none.
// This gives local development a working one without a manual copy step.
import { copyFileSync, existsSync, mkdirSync } from 'node:fs';

if (!existsSync('public/config.json')) {
  mkdirSync('public', { recursive: true });
  copyFileSync('config.local.example.json', 'public/config.json');
  console.log('Created public/config.json for local mode.');
}
