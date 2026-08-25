import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { auth } from "./api";
import { ApiError } from "./api/client";
import type { User } from "./api/types";

type AuthMode = "oidc" | "local";

type Session = {
  user: User | null;
  mode: AuthMode | null;
  loading: boolean;
  /** Set only when the session could not be checked — never when there is none. */
  error: Error | null;
  setUser: (user: User | null) => void;
  refresh: () => Promise<void>;
  signOut: () => Promise<void>;
};

const SessionContext = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [mode, setMode] = useState<AuthMode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(async () => {
    try {
      setUser(await auth.me());
      setError(null);
    } catch (cause) {
      // 401 is the normal "not signed in yet" answer, not a failure to report.
      if (cause instanceof ApiError && cause.isUnauthorized) {
        setUser(null);
        setError(null);
        return;
      }
      // Anything else means we do not know: say so rather than signing them out.
      setError(cause instanceof Error ? cause : new Error(String(cause)));
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const [config] = await Promise.allSettled([auth.config(), refresh()]);
      if (cancelled) return;
      if (config.status === "fulfilled") setMode(config.value.mode);
      setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  const signOut = useCallback(async () => {
    await auth.logout();
    setUser(null);
  }, []);

  const value = useMemo<Session>(
    () => ({ user, mode, loading, error, setUser, refresh, signOut }),
    [user, mode, loading, error, refresh, signOut],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) throw new Error("useSession must be used inside a SessionProvider");
  return session;
}
