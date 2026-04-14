import { useState, useEffect } from "react";
import { auth } from "@/lib/api";
import { getPayload } from "@/lib/utils";

export interface Me {
  id: number;
  username: string;
  role: "admin" | "analyst" | "viewer";
}

export function useAuth() {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const payload = getPayload();
    if (!payload) { setLoading(false); return; }
    auth.me()
      .then((r) => setMe(r.data))
      .catch(() => { localStorage.clear(); })
      .finally(() => setLoading(false));
  }, []);

  const login = async (username: string, password: string) => {
    const { data } = await auth.login(username, password);
    localStorage.setItem("access", data.access);
    localStorage.setItem("refresh", data.refresh);
    const { data: me } = await auth.me();
    setMe(me);
    return me;
  };

  const logout = async () => {
    const refresh = localStorage.getItem("refresh") ?? "";
    try { await auth.logout(refresh); } catch { /* ignore */ }
    localStorage.clear();
    setMe(null);
  };

  return { me, loading, login, logout };
}
