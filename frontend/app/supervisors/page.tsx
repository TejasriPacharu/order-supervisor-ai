"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Supervisor {
  id: string;
  name: string;
  base_instruction: string;
  model: string;
  wake_aggressiveness: string;
}

export default function SupervisorsPage() {
  const [supervisors, setSupervisors] = useState<Supervisor[]>([]);

  useEffect(() => {
    api<Supervisor[]>("/api/supervisors").then(setSupervisors);
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Supervisors</h1>
        <Link
          href="/supervisors/new"
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm"
        >
          New Supervisor
        </Link>
      </div>
      {supervisors.length === 0 && (
        <p className="text-gray-500">
          No supervisors yet. Create one to get started.
        </p>
      )}
      {supervisors.map((s) => (
        <div key={s.id} className="bg-white p-4 rounded border">
          <h2 className="font-semibold">{s.name}</h2>
          <p className="text-sm text-gray-500 mt-1 line-clamp-2">
            {s.base_instruction}
          </p>
          <div className="mt-2 text-xs text-gray-400">
            Model: {s.model} &middot; Wake aggressiveness:{" "}
            {s.wake_aggressiveness} &middot;
            <span className="font-mono ml-1">{s.id.slice(0, 8)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
