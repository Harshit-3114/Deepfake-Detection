import React, { useState } from "react";
import API_BASE_URL from "../config";

const MAX_FILE_SIZE = 100 * 1024 * 1024;

function UploadForm() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleUpload = async () => {
    if (!file) {
      setStatus("Please select a file first!");
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setStatus("File too large (max 100MB)");
      return;
    }

    setLoading(true);
    setStatus("Uploading...");
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE_URL}/ingest`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText || "Upload failed");
      }

      const data = await res.json();
      setStatus("Job submitted successfully!");
      setResult(data);
    } catch (err) {
      setStatus("Error: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white shadow-lg rounded-2xl p-6 w-full max-w-md">
      <input
        type="file"
        className="mb-4 block w-full text-sm"
        onChange={(e) => setFile(e.target.files[0])}
      />
      <button
        onClick={handleUpload}
        disabled={loading}
        className={`px-4 py-2 rounded-xl text-white ${
          loading ? "bg-gray-400" : "bg-indigo-600 hover:bg-indigo-700"
        }`}
      >
        {loading ? "Uploading..." : "Upload"}
      </button>
      {status && <p className="mt-4 text-gray-700">{status}</p>}
      {result && (
        <pre className="mt-4 bg-gray-100 p-4 rounded-lg text-sm overflow-auto max-h-96">
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}

export default UploadForm;

