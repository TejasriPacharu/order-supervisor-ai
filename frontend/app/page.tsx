import Link from "next/link";

export default function Home() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Order Supervisor</h1>
      <p className="text-gray-600">
        AI-powered order lifecycle monitoring and intervention
      </p>
      <div className="flex gap-4">
        <Link
          href="/supervisors"
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Supervisors
        </Link>
        <Link
          href="/runs"
          className="bg-gray-800 text-white px-4 py-2 rounded hover:bg-gray-900"
        >
          Runs
        </Link>
      </div>
    </div>
  );
}
