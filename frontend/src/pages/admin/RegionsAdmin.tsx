import { useEffect, useState } from "react";

type Region = { id: number; name: string };

export function RegionsAdmin() {
  const [data, setData] = useState<Region[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;

    (async () => {
      try {
        setLoading(true);
        setErr(null);

        const res = await fetch("/api/regions");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = (await res.json()) as Region[];

        if (alive) setData(json);
      } catch (e: any) {
        if (alive) setErr(e?.message ?? "Ошибка загрузки");
      } finally {
        if (alive) setLoading(false);
      }
    })();

    return () => {
      alive = false;
    };
  }, []);

  if (loading) return <div style={{ padding: 16 }}>Загрузка регионов…</div>;
  if (err) return <div style={{ padding: 16 }}>Ошибка: {err}</div>;

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ fontSize: 20, fontWeight: 600, marginBottom: 12 }}>Регионы</h2>

      <div style={{ border: "1px solid #ddd", borderRadius: 8, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#f7f7f7" }}>
              <th style={{ textAlign: "left", padding: 12, width: 120 }}>ID</th>
              <th style={{ textAlign: "left", padding: 12 }}>Название</th>
            </tr>
          </thead>
          <tbody>
            {data.map((r) => (
              <tr key={r.id} style={{ borderTop: "1px solid #eee" }}>
                <td style={{ padding: 12 }}>{r.id}</td>
                <td style={{ padding: 12 }}>{r.name}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
