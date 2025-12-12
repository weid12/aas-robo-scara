export async function adAuthenticate({ userId, password }) {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ userId, password }),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = data?.error || `Erro ${response.status}`;
    throw new Error(message);
  }

  return data;
}
