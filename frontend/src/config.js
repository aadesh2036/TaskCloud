// Fetched at startup rather than built in, so the same build works anywhere
// and 4_frontend.sh can write the real IDs after the stacks exist.
export async function loadConfig() {
  const response = await fetch('/config.json', { cache: 'no-store' });
  if (!response.ok) throw new Error(`config.json returned ${response.status}`);
  const config = await response.json();
  if (!config.apiUrl || !['local', 'aws'].includes(config.mode)) {
    throw new Error('config.json needs apiUrl, and mode set to local or aws');
  }
  if (config.mode === 'aws' && (!config.userPoolId || !config.userPoolClientId)) {
    throw new Error('config.json needs userPoolId and userPoolClientId in aws mode');
  }
  return config;
}
