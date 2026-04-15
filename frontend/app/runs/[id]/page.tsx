"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";

const EVENT_TYPES = [
  "order_created",
  "payment_confirmed",
  "payment_failed",
  "shipment_created",
  "shipment_delayed",
  "delivered",
  "refund_requested",
  "customer_message_received",
  "no_update_for_n_hours",
];

const STATUS_STYLES: Record<string, string> = {
  active: "bg-green-100 text-green-700",
  paused: "bg-yellow-100 text-yellow-700",
  completed: "bg-blue-100 text-blue-700",
  terminated: "bg-red-100 text-red-700",
};

const ACTIVITY_ICONS: Record<string, string> = {
  event: "\u{1F4E8}",
  action: "\u26A1",
  decision: "\u{1F9E0}",
  instruction: "\u{1F4DD}",
  summary: "\u{1F4CB}",
  wake: "\u23F0",
};

interface ActivityItem {
  id: string;
  type: string;
  data: Record<string, unknown>;
  created_at: string;
}

interface RunDetail {
  id: string;
  order_id: string;
  status: string;
  state: Record<string, unknown>;
  extra_instructions: string[];
  final_summary: string | null;
  created_at: string;
  completed_at: string | null;
  activities: ActivityItem[];
}

function Controls({
  status,
  runId,
  onDone,
}: {
  status: string;
  runId: string;
  onDone: () => void;
}) {
  const act = async (action: string) => {
    await api(`/api/runs/${runId}/${action}`, { method: "POST" });
    onDone();
  };

  return (
    <div className="flex gap-2">
      {status === "active" && (
        <button
          onClick={() => act("interrupt")}
          className="bg-yellow-500 text-white px-3 py-1 rounded text-sm"
        >
          Pause
        </button>
      )}
      {status === "paused" && (
        <button
          onClick={() => act("resume")}
          className="bg-green-600 text-white px-3 py-1 rounded text-sm"
        >
          Resume
        </button>
      )}
      {status !== "completed" && status !== "terminated" && (
        <button
          onClick={() => act("terminate")}
          className="bg-red-600 text-white px-3 py-1 rounded text-sm"
        >
          Terminate
        </button>
      )}
    </div>
  );
}

function EventPanel({ runId, onSent }: { runId: string; onSent: () => void }) {
  const [eventType, setEventType] = useState(EVENT_TYPES[0]);

  const send = async () => {
    await api(`/api/runs/${runId}/events`, {
      method: "POST",
      body: JSON.stringify({ type: eventType }),
    });
    onSent();
  };

  return (
    <div className="bg-white p-4 rounded border">
      <h2 className="font-semibold mb-2 text-sm">Send Event</h2>
      <div className="flex gap-2">
        <select
          className="flex-1 border rounded p-2 text-sm"
          value={eventType}
          onChange={(e) => setEventType(e.target.value)}
        >
          {EVENT_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <button
          onClick={send}
          className="bg-gray-800 text-white px-3 py-1 rounded text-sm"
        >
          Send
        </button>
      </div>
    </div>
  );
}

function InstructionPanel({
  runId,
  onAdded,
}: {
  runId: string;
  onAdded: () => void;
}) {
  const [instruction, setInstruction] = useState("");

  const add = async () => {
    if (!instruction.trim()) return;
    await api(`/api/runs/${runId}/instructions`, {
      method: "POST",
      body: JSON.stringify({ instruction }),
    });
    setInstruction("");
    onAdded();
  };

  return (
    <div className="bg-white p-4 rounded border">
      <h2 className="font-semibold mb-2 text-sm">Add Instruction</h2>
      <div className="flex gap-2">
        <input
          className="flex-1 border rounded p-2 text-sm"
          placeholder="e.g. Prioritize speed over cost"
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && add()}
        />
        <button
          onClick={add}
          className="bg-gray-800 text-white px-3 py-1 rounded text-sm"
        >
          Add
        </button>
      </div>
    </div>
  );
}

function ActivityLog({ activities }: { activities: ActivityItem[] }) {
  return (
    <div className="bg-white rounded border">
      <h2 className="font-semibold p-4 border-b text-sm">
        Activity Log ({activities.length})
      </h2>
      <div className="divide-y max-h-[600px] overflow-y-auto">
        {activities.length === 0 && (
          <p className="p-4 text-sm text-gray-400">No activity yet.</p>
        )}
        {activities.map((a) => (
          <div key={a.id} className="p-3 text-sm">
            <div className="flex justify-between items-center">
              <span>
                <span className="mr-1">
                  {ACTIVITY_ICONS[a.type] || "\u2022"}
                </span>
                <span className="font-medium">{a.type}</span>
              </span>
              <span className="text-xs text-gray-400">
                {new Date(a.created_at).toLocaleTimeString()}
              </span>
            </div>
            <pre className="text-xs text-gray-600 mt-1 whitespace-pre-wrap break-words max-h-40 overflow-y-auto">
              {JSON.stringify(a.data, null, 2)}
            </pre>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function RunDetailPage() {
  const { id } = useParams();
  const [run, setRun] = useState<RunDetail | null>(null);

  const refresh = () => api<RunDetail>(`/api/runs/${id}`).then(setRun);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 3000);
    return () => clearInterval(interval);
  }, [id]);

  if (!run) return <div className="text-gray-500">Loading...</div>;

  const isLive = run.status === "active" || run.status === "paused";

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold font-mono">{run.order_id}</h1>
          <div className="flex items-center gap-3 mt-1">
            <span
              className={`text-sm px-2 py-0.5 rounded ${STATUS_STYLES[run.status] || ""}`}
            >
              {run.status}
            </span>
            <span className="text-xs text-gray-400">
              Started {new Date(run.created_at).toLocaleString()}
            </span>
            {run.completed_at && (
              <span className="text-xs text-gray-400">
                Ended {new Date(run.completed_at).toLocaleString()}
              </span>
            )}
          </div>
        </div>
        <Controls status={run.status} runId={run.id} onDone={refresh} />
      </div>

      {run.state && Object.keys(run.state).length > 0 && (
        <div className="bg-white p-4 rounded border">
          <h2 className="font-semibold mb-2 text-sm">Agent State</h2>
          <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto">
            {JSON.stringify(run.state, null, 2)}
          </pre>
        </div>
      )}

      {run.extra_instructions && run.extra_instructions.length > 0 && (
        <div className="bg-white p-4 rounded border">
          <h2 className="font-semibold mb-2 text-sm">Extra Instructions</h2>
          <ul className="text-sm space-y-1">
            {run.extra_instructions.map((inst, i) => (
              <li key={i} className="text-gray-700">
                &bull; {inst}
              </li>
            ))}
          </ul>
        </div>
      )}

      {run.final_summary && (
        <div className="bg-blue-50 p-4 rounded border border-blue-200">
          <h2 className="font-semibold mb-2 text-sm">Final Summary</h2>
          <div className="text-sm whitespace-pre-wrap">{run.final_summary}</div>
        </div>
      )}

      {isLive && (
        <div className="grid grid-cols-2 gap-4">
          <EventPanel runId={run.id} onSent={refresh} />
          <InstructionPanel runId={run.id} onAdded={refresh} />
        </div>
      )}

      <ActivityLog activities={run.activities || []} />
    </div>
  );
}
