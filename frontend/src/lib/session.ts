const SESSION_KEY = "aurashop_session_id";

/** Get session ID. Persists in both sessionStorage and localStorage so cart survives refresh and is consistent across tabs. */
export function getSessionId(): string {
  if (typeof window === "undefined") return "";
  let id = sessionStorage.getItem(SESSION_KEY) || localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = "sess_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    sessionStorage.setItem(SESSION_KEY, id);
    localStorage.setItem(SESSION_KEY, id);
  } else {
    sessionStorage.setItem(SESSION_KEY, id);
    localStorage.setItem(SESSION_KEY, id);
  }
  return id;
}
