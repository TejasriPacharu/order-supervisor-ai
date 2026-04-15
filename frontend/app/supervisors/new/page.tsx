"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

const DEFAULT_INSTRUCTION = `You are an order supervisor AI. Monitor the order lifecycle and take action when needed.

Key responsibilities:
- Track order status changes and flag anomalies
- Escalate payment failures to the payments team immediately
- Contact logistics team if shipment is delayed
- Keep the customer informed of significant updates
- Create internal notes for important observations

Be proactive but not noisy. Only wake up when there's something meaningful to act on.`;

export default function NewSupervisorPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    name: "",
    base_instruction: DEFAULT_INSTRUCTION,
    wake_aggressiveness: "medium",
    model: "claude-sonnet-4-20250514",
  });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    await api("/api/supervisors", {
      method: "POST",
      body: JSON.stringify(form),
    });
    router.push("/supervisors");
  };

  const set = (key: string, value: string) =>
    setForm({ ...form, [key]: value });

  return (
    <form onSubmit={submit} className="space-y-4 max-w-lg">
      <h1 className="text-2xl font-bold">New Supervisor</h1>
      <div>
        <label className="text-sm text-gray-600">Name</label>
        <input
          className="w-full border rounded p-2 mt-1"
          placeholder="Order Supervisor"
          value={form.name}
          onChange={(e) => set("name", e.target.value)}
          required
        />
      </div>
      <div>
        <label className="text-sm text-gray-600">Base Instruction</label>
        <textarea
          className="w-full border rounded p-2 mt-1 h-48 text-sm font-mono"
          value={form.base_instruction}
          onChange={(e) => set("base_instruction", e.target.value)}
          required
        />
      </div>
      <div>
        <label className="text-sm text-gray-600">Wake Aggressiveness</label>
        <select
          className="w-full border rounded p-2 mt-1"
          value={form.wake_aggressiveness}
          onChange={(e) => set("wake_aggressiveness", e.target.value)}
        >
          <option value="low">Low - only urgent events</option>
          <option value="medium">Medium - urgent + normal events</option>
          <option value="high">High - wake on all events</option>
        </select>
      </div>
      <div>
        <label className="text-sm text-gray-600">Model</label>
        <select
          className="w-full border rounded p-2 mt-1"
          value={form.model}
          onChange={(e) => set("model", e.target.value)}
        >
          <option value="claude-sonnet-4-20250514">Claude Sonnet 4</option>
          <option value="claude-haiku-4-5-20251001">Claude Haiku 4.5</option>
        </select>
      </div>
      <button
        type="submit"
        className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
      >
        Create Supervisor
      </button>
    </form>
  );
}
