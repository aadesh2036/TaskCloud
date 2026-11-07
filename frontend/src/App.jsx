import { useCallback, useEffect, useMemo, useState } from 'react';
import { createApi } from './api.js';
import Dashboard from './components/Dashboard.jsx';
import Login from './components/Login.jsx';
import { loadConfig } from './config.js';

const LOCAL_TOKEN = async () => 'local-dev-token';

export default function App() {
  const [config, setConfig] = useState(null);
  const [auth, setAuth] = useState(null);
  const [signedIn, setSignedIn] = useState(false);
  const [startupError, setStartupError] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const loaded = await loadConfig();
        if (loaded.mode === 'aws') {
          const authModule = await import('./auth.js');
          authModule.configureAuth(loaded);
          setAuth(authModule);
          setSignedIn(Boolean(await authModule.getToken().catch(() => null)));
        } else {
          setSignedIn(true);
        }
        setConfig(loaded);
      } catch (error) {
        setStartupError(error.message);
      }
    })();
  }, []);

  const signOut = useCallback(async () => {
    // Local mode has no login to return to.
    if (!auth) return;
    setSignedIn(false);
    await auth.logOut().catch(() => {});
  }, [auth]);

  const api = useMemo(
    () =>
      config &&
      createApi({
        apiUrl: config.apiUrl,
        getToken: auth ? () => auth.getToken().catch(() => null) : LOCAL_TOKEN,
        onUnauthorized: signOut,
      }),
    [config, auth, signOut],
  );

  if (startupError) {
    return (
      <main className="centered">
        <h1 className="brand">TaskCloud</h1>
        <p role="alert">TaskCloud could not start: {startupError}.</p>
        <p>For local use, run <code>npm run dev</code>, which creates the config file. On AWS, re-run <code>scripts/4_frontend.sh</code>.</p>
      </main>
    );
  }
  if (!config) {
    return <main className="centered" aria-busy="true"><p role="status">Opening your journal…</p></main>;
  }
  if (!signedIn) {
    return <Login auth={auth} onSignedIn={() => setSignedIn(true)} />;
  }
  return <Dashboard api={api} localMode={config.mode === 'local'} onSignOut={signOut} />;
}
