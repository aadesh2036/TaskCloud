import { useState } from 'react';
import MochiFace from './MochiFace.jsx';

const friendly = (error) => {
  if (error.name === 'NotAuthorizedException' || error.name === 'UserNotFoundException') {
    return 'That email and password do not match. Check both and try again.';
  }
  if (error.name === 'InvalidPasswordException') {
    return 'Choose a password with at least 8 characters, including upper case, lower case and a number.';
  }
  return error.message || 'Could not log in. Try again.';
};

export default function Login({ auth, onSignedIn }) {
  const [step, setStep] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError('');
    if (step === 'newPassword' && newPassword !== confirmPassword) {
      setError('The two passwords do not match.');
      return;
    }
    setBusy(true);
    try {
      const result = step === 'login' ? await auth.logIn(email.trim(), password) : await auth.setNewPassword(newPassword);
      if (result === 'done') onSignedIn();
      else setStep(result);
    } catch (caught) {
      setError(friendly(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login">
      <div className="login-page">
        <span className="tape tape-blue" aria-hidden="true" />
        <span className="login-mochi"><MochiFace mood={error ? 'worried' : busy ? 'thinking' : 'happy'} /></span>
        <h1 className="brand">TaskCloud</h1>
        <p className="login-intro">Your study tasks, your streak, and a planner that turns one line into a schedule.</p>
        <form onSubmit={submit}>
          {step === 'login' ? (
            <>
              <label>Email
                <input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
              </label>
              <label>Password
                <input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
              </label>
            </>
          ) : (
            <>
              <h2>Choose a new password</h2>
              <p>This is your first login, so replace the temporary password. Use at least 8 characters, including upper case, lower case and a number.</p>
              <label>New password
                <input type="password" autoComplete="new-password" required minLength={8} value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
              </label>
              <label>Repeat new password
                <input type="password" autoComplete="new-password" required minLength={8} value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
              </label>
            </>
          )}
          {error && <p className="error" role="alert">{error}</p>}
          <button className="primary" type="submit" disabled={busy}>
            {busy ? 'Please wait…' : step === 'login' ? 'Log in' : 'Save password and log in'}
          </button>
        </form>
        {step === 'login' && <p className="hint">Sign-up is closed. Your project admin creates accounts.</p>}
      </div>
    </main>
  );
}
