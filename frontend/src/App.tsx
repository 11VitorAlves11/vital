import { useEffect, useState } from "react";

type ApiInfo = { name: string; version: string };

/** Placeholder shell — confirms the web app is wired to the API. */
export function App() {
  const [info, setInfo] = useState<ApiInfo | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch("/api")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then(setInfo)
      .catch(() => setError(true));
  }, []);

  return (
    <main className="mx-auto flex min-h-dvh max-w-2xl flex-col justify-center gap-4 p-8">
      <h1 className="font-display text-3xl text-primary">Vital</h1>
      <p className="text-ink-muted">
        Tracking de biomarcadores, composição corporal e progresso físico.
      </p>
      <p className="data text-sm text-ink-muted">
        {error ? "API indisponível" : info ? `API ${info.name} v${info.version}` : "A ligar à API…"}
      </p>
    </main>
  );
}
