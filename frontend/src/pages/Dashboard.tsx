import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetchJson } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";

export const Dashboard: React.FC = () => {
  const { token } = useAuth();
  const [summary, setSummary] = useState<any>(null);
  const [history, setHistory] = useState<any>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    const load = async () => {
      try {
        const s = await apiFetchJson("/api/dashboard/summary", { auth: true, token });
        setSummary(s);
        const h = await apiFetchJson("/api/dashboard/history", { auth: true, token });
        setHistory(h);
      } catch (e: any) {
        setError(e?.message || "Failed to load dashboard");
      }
    };
    load();
  }, [token]);

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      <h1 className="text-2xl font-semibold">DigiClinic Dashboard</h1>
      {error && <div className="text-red-600">{error}</div>}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Patients</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl">
              {summary?.patients?.patients ?? 0}
            </div>
            <div className="text-sm text-gray-500">records</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Best F1</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl">
              {summary?.evaluation?.best?.metrics?.f1?.toFixed?.(3) ?? "-"}
            </div>
            <div className="text-sm text-gray-500">model: {summary?.evaluation?.best?.model_id || "-"}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Recent Audits</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl">{summary?.recent_audit?.length ?? 0}</div>
            <div className="text-sm text-gray-500">last 20 events</div>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Training Progress (F1)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-gray-600">
            {history?.evaluation_history?.length ? (
              <ul className="list-disc pl-6 space-y-1">
                {history.evaluation_history.slice(-10).map((e: any, i: number) => (
                  <li key={i}>
                    {new Date(e.ts * 1000).toLocaleString()} — {e.model_id} — F1: {e.metrics?.f1?.toFixed?.(3)}
                  </li>
                ))}
              </ul>
            ) : (
              <span>No evaluation history yet.</span>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Dashboard;
