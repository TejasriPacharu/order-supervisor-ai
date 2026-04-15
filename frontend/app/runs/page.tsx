"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface RunItem {
  id: string;
  order_id: string;
  status: string;
  created_at: string;
  completed_at: string | null;
}

interface Supervisor {
  id: string;
  name: string;
}

const STATUS_STYLES: Record<string, string> = {
  active: "bg-green-100 text-green-700",
  paused: "bg-yellow-100 text-yellow-700",
  completed: "bg-blue-100 text-blue-700",
  terminated: "bg-red-100 text-red-700",
};

export default function RunsPage() {
  const [runs, setRuns] = useState<RunItem[]>([]);
  const [supervisors, setSupervisors] = useState<Supervisor[]>([]);
  const [form, setForm] = useState({ supervisor_id: "", order_id: "" });

  const refresh = () => api<RunItem[]>("/api/runs").then(setRuns);

  useEffect(() => {
    refresh();
    api<Supervisor[]>("/api/supervisors").then(setSupervisors);
  }, []);

  const createRun = async (e: React.FormEvent) => {
    e.preventDefault();
    await api("/api/runs", { method: "POST", body: JSON.stringify(form) });
    setForm({ supervisor_id: "", order_id: "" });
    refresh();
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Runs</h1>

      <form
        onSubmit={createRun}
        className="bg-white p-4 rounded border flex gap-3 items-end"
      >
        <div className="flex-1">
          <label className="text-sm text-gray-500">Supervisor</label>
          <select
            className="w-full border rounded p-2"
            value={form.supervisor_id}
            onChange={(e) =>
              setForm({ ...form, supervisor_id: e.target.value })
            }
            required
          >
            <option value="">Select...</option>
            {supervisors.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex-1">
          <label className="text-sm text-gray-500">Order ID</label>
          <input
            className="w-full border rounded p-2"
            placeholder="ORD-001"
            value={form.order_id}
            onChange={(e) => setForm({ ...form, order_id: e.target.value })}
            required
          />
        </div>
        <button
          type="submit"
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm whitespace-nowrap"
        >
          Start Run
        </button>
      </form>

      <div className="space-y-2">
        {runs.length === 0 && <p className="text-gray-500">No runs yet.</p>}
        {runs.map((r) => (
          <Link
            key={r.id}
            href={`/runs/${r.id}`}
            className="block bg-white p-4 rounded border hover:border-blue-300 transition-colors"
          >
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-3">
                <span className="font-mono font-semibold">{r.order_id}</span>
                <span
                  className={`text-xs px-2 py-0.5 rounded ${STATUS_STYLES[r.status] || ""}`}
                >
                  {r.status}
                </span>
              </div>
              <span className="text-xs text-gray-400">
                {new Date(r.created_at).toLocaleString()}
              </span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
