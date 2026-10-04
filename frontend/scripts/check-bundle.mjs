// Fails the build if a credential-looking token ships in the browser bundle.
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const dir = 'dist/assets';
const offenders = readdirSync(dir)
  .filter((f) => f.endsWith('.js'))
  .filter((f) => /(demo-token|ops-token|admin-token|Bearer [A-Za-z0-9_-]{8,})/.test(readFileSync(join(dir, f), 'utf8')));
if (offenders.length) {
  console.error(`Credential-like string found in bundle: ${offenders.join(', ')}`);
  process.exit(1);
}
console.log('bundle contains no embedded credentials');
