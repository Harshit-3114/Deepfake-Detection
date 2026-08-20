import React, { useState } from "react";
import UploadForm from "./components/UploadForm.jsx";
import StatusPage from "./pages/StatusPage.jsx";

function App() {
  const [tab, setTab] = useState("upload");

  return (
    <div className="min-h-screen flex flex-col items-center bg-gradient-to-br from-indigo-200 to-blue-200 p-6">
      <h1 className="text-4xl font-bold mt-6 mb-2 text-indigo-700">
        Deepfake Detection
      </h1>
      <p className="text-gray-600 mb-6">Upload a file or check a job status</p>
      <div className="flex gap-4 mb-6">
        <button
          onClick={() => setTab("upload")}
          className={`px-6 py-2 rounded-xl font-medium ${
            tab === "upload"
              ? "bg-indigo-600 text-white"
              : "bg-white text-indigo-600"
          }`}
        >
          Upload
        </button>
        <button
          onClick={() => setTab("status")}
          className={`px-6 py-2 rounded-xl font-medium ${
            tab === "status"
              ? "bg-indigo-600 text-white"
              : "bg-white text-indigo-600"
          }`}
        >
          Check Status
        </button>
      </div>
      {tab === "upload" ? <UploadForm /> : <StatusPage />}
    </div>
  );
}

export default App;

