// Imported only in aws mode, so local development never loads the Amplify code.
import { Amplify } from 'aws-amplify';
import { confirmSignIn, fetchAuthSession, signIn, signOut } from 'aws-amplify/auth';

export function configureAuth(config) {
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId: config.userPoolId,
        userPoolClientId: config.userPoolClientId,
      },
    },
  });
}

// Amplify refreshes an expired token by itself using the refresh token.
export async function getToken() {
  const session = await fetchAuthSession();
  return session.tokens?.idToken?.toString() ?? null;
}

function resultOf(output) {
  const step = output.nextStep?.signInStep;
  if (output.isSignedIn || step === 'DONE') return 'done';
  // Users created by an admin must choose a password on their first sign-in.
  if (step === 'CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED') return 'newPassword';
  throw new Error(`This sign-in needs a step TaskCloud does not support: ${step}`);
}

export async function logIn(email, password) {
  return resultOf(await signIn({ username: email, password }));
}

export async function setNewPassword(newPassword) {
  return resultOf(await confirmSignIn({ challengeResponse: newPassword }));
}

export async function logOut() {
  await signOut();
}
