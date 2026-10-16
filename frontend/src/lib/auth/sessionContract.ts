export const SESSION_AUTH_MARKER = 'session-cookie';
export const SESSION_AUTHORIZATION_HEADER = `Bearer ${SESSION_AUTH_MARKER}`;

export function isSessionAuthorizationHeader(value: string | null | undefined): boolean {
  return (value ?? '').trim().toLowerCase() === SESSION_AUTHORIZATION_HEADER.toLowerCase();
}
