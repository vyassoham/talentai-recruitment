"use client";
import React from "react";
export default function ErrorBoundary({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div style={{ padding: 40, color: "white", backgroundColor: "black", fontFamily: "monospace" }}>
      <h2>Frontend Crash!</h2>
      <p style={{ color: "red" }}>{error.message}</p>
      <pre style={{ color: "orange", whiteSpace: "pre-wrap" }}>{error.stack}</pre>
      <button onClick={reset} style={{ padding: 10, marginTop: 20, background: "white", color: "black" }}>Try Again</button>
    </div>
  );
}
