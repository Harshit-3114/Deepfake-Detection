import React, { useState } from "react";
import API_BASE_URL from "../config";

function StatusPage() {
  const [jobId, setJobId] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const checkStatus = async () => {
    if (!jobId.trim()) {
      setResult({ error: "Please enter a Job ID" });
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/status/${jobId}`);
      if (!res.ok) throw new Error("Job not found");
      const data = await res.json();
      setResult(data);
    } catch (err) {
      setResult({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-md mx-auto bg-white shadow-lg rounded-2xl mt-8">
      <h2 className="text-xl font-semibold mb-4">Check Job Status</h2>
      <input
        type="text"
        placeholder="Enter Job ID"
        className="border p-2 w-full mb-4 rounded-lg"
        value={jobId}
        onChange={(e) => setJobId(e.target.value)}
      />
      <button
        onClick={checkStatus}
        disabled={loading}
        className={`px-4 py-2 rounded-xl text-white ${
          loading ? "bg-gray-400" : "bg-green-600 hover:bg-green-700"
        }`}
      >
        {loading ? "Checking..." : "Check"}
      </button>
      {result && (
        <pre className="mt-4 bg-gray-100 p-4 rounded-lg text-sm overflow-auto max-h-96">
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}

export default StatusPage;

