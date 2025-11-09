import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

const AUTH_FLAG = "wic.isAuthenticated";
const AUTH_USER_KEY = "wic.userId";
const LEGACY_AUTH_FLAG = "pmh.isAuthenticated";
const LEGACY_AUTH_USER_KEY = "pmh.userId";

const AuthContext = createContext(null);

function migrateLegacyKeys() {
  if (typeof window === "undefined") {
    return;
  }
  const legacyFlag = window.localStorage.getItem(LEGACY_AUTH_FLAG);
  const hasLegacyFlag = legacyFlag !== null;
  const legacyUser = window.localStorage.getItem(LEGACY_AUTH_USER_KEY);
  if (!hasLegacyFlag && legacyUser === null) {
    return;
  }
  if (legacyFlag !== null) {
    window.localStorage.setItem(AUTH_FLAG, legacyFlag);
    window.localStorage.removeItem(LEGACY_AUTH_FLAG);
  }
  if (legacyUser !== null) {
    window.localStorage.setItem(AUTH_USER_KEY, legacyUser);
    window.localStorage.removeItem(LEGACY_AUTH_USER_KEY);
  }
}

function readAuthState() {
  if (typeof window === "undefined") {
    return { isAuthenticated: false, userId: "" };
  }
  migrateLegacyKeys();
  return {
    isAuthenticated: window.localStorage.getItem(AUTH_FLAG) === "true",
    userId: window.localStorage.getItem(AUTH_USER_KEY) || "",
  };
}

export function AuthProvider({ children }) {
  const [state, setState] = useState(readAuthState);

  const login = useCallback((userId) => {
    if (typeof window === "undefined") {
      return;
    }
    window.localStorage.setItem(AUTH_FLAG, "true");
    if (userId) {
      window.localStorage.setItem(AUTH_USER_KEY, userId);
    }
    setState({ isAuthenticated: true, userId: userId || "" });
  }, []);

  const logout = useCallback(() => {
    if (typeof window === "undefined") {
      return;
    }
    window.localStorage.removeItem(AUTH_FLAG);
    window.localStorage.removeItem(AUTH_USER_KEY);
    setState({ isAuthenticated: false, userId: "" });
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const handleStorage = (event) => {
      if (
        event.key === AUTH_FLAG ||
        event.key === AUTH_USER_KEY ||
        event.key === LEGACY_AUTH_FLAG ||
        event.key === LEGACY_AUTH_USER_KEY
      ) {
        migrateLegacyKeys();
        setState(readAuthState());
      }
    };
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  const value = useMemo(
    () => ({
      isAuthenticated: state.isAuthenticated,
      userId: state.userId,
      login,
      logout,
    }),
    [state.isAuthenticated, state.userId, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
