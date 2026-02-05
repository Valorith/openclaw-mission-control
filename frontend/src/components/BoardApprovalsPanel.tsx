"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "@clerk/nextjs";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { getApiBaseUrl } from "@/lib/api-base";
import { cn } from "@/lib/utils";

const apiBase = getApiBaseUrl();

type Approval = {
  id: string;
  action_type: string;
  payload?: Record<string, unknown> | null;
  confidence: number;
  rubric_scores?: Record<string, number> | null;
  status: string;
  created_at: string;
  resolved_at?: string | null;
};

type BoardApprovalsPanelProps = {
  boardId: string;
};

const formatTimestamp = (value?: string | null) => {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const statusBadgeVariant = (status: string) => {
  if (status === "approved") return "success";
  if (status === "rejected") return "danger";
  return "outline";
};

const confidenceVariant = (confidence: number) => {
  if (confidence >= 90) return "success";
  if (confidence >= 80) return "accent";
  return "warning";
};

export function BoardApprovalsPanel({ boardId }: BoardApprovalsPanelProps) {
  const { getToken, isSignedIn } = useAuth();
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const loadApprovals = useCallback(async () => {
    if (!isSignedIn || !boardId) return;
    setIsLoading(true);
    setError(null);
    try {
      const token = await getToken();
      const res = await fetch(`${apiBase}/api/v1/boards/${boardId}/approvals`, {
        headers: {
          Authorization: token ? `Bearer ${token}` : "",
        },
      });
      if (!res.ok) throw new Error("Unable to load approvals.");
      const data = (await res.json()) as Approval[];
      setApprovals(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load approvals.");
    } finally {
      setIsLoading(false);
    }
  }, [boardId, getToken, isSignedIn]);

  useEffect(() => {
    loadApprovals();
    if (!isSignedIn || !boardId) return;
    const interval = setInterval(loadApprovals, 15000);
    return () => clearInterval(interval);
  }, [boardId, isSignedIn, loadApprovals]);

  const handleDecision = useCallback(
    async (approvalId: string, status: "approved" | "rejected") => {
      if (!isSignedIn || !boardId) return;
      setUpdatingId(approvalId);
      setError(null);
      try {
        const token = await getToken();
        const res = await fetch(
          `${apiBase}/api/v1/boards/${boardId}/approvals/${approvalId}`,
          {
            method: "PATCH",
            headers: {
              "Content-Type": "application/json",
              Authorization: token ? `Bearer ${token}` : "",
            },
            body: JSON.stringify({ status }),
          }
        );
        if (!res.ok) throw new Error("Unable to update approval.");
        const updated = (await res.json()) as Approval;
        setApprovals((prev) =>
          prev.map((item) => (item.id === approvalId ? updated : item))
        );
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Unable to update approval."
        );
      } finally {
        setUpdatingId(null);
      }
    },
    [boardId, getToken, isSignedIn]
  );

  const sortedApprovals = useMemo(() => {
    const pending = approvals.filter((item) => item.status === "pending");
    const resolved = approvals.filter((item) => item.status !== "pending");
    const sortByTime = (items: Approval[]) =>
      [...items].sort((a, b) => {
        const aTime = new Date(a.created_at).getTime();
        const bTime = new Date(b.created_at).getTime();
        return bTime - aTime;
      });
    return [...sortByTime(pending), ...sortByTime(resolved)];
  }, [approvals]);

  return (
    <Card>
      <CardHeader className="flex flex-col gap-4 border-b border-[color:var(--border)] pb-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted">
              Approvals
            </p>
            <p className="mt-1 text-lg font-semibold text-strong">
              Pending decisions
            </p>
          </div>
          <Button variant="secondary" size="sm" onClick={loadApprovals}>
            Refresh
          </Button>
        </div>
        <p className="text-sm text-muted">
          Review lead-agent decisions that require human approval.
        </p>
      </CardHeader>
      <CardContent className="space-y-4 pt-5">
        {error ? (
          <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        ) : null}
        {isLoading ? (
          <p className="text-sm text-muted">Loading approvals…</p>
        ) : sortedApprovals.length === 0 ? (
          <p className="text-sm text-muted">No approvals yet.</p>
        ) : (
          <div className="space-y-4">
            {sortedApprovals.map((approval) => (
              <div
                key={approval.id}
                className="space-y-2 rounded-2xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-strong">
                      {approval.action_type.replace(/_/g, " ")}
                    </p>
                    <p className="text-xs text-muted">
                      Requested {formatTimestamp(approval.created_at)}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={confidenceVariant(approval.confidence)}>
                      {approval.confidence}% confidence
                    </Badge>
                    <Badge variant={statusBadgeVariant(approval.status)}>
                      {approval.status}
                    </Badge>
                  </div>
                </div>
                {approval.payload || approval.rubric_scores ? (
                  <details className="rounded-xl border border-dashed border-[color:var(--border)] px-3 py-2 text-xs text-muted">
                    <summary className="cursor-pointer font-semibold text-strong">
                      Details
                    </summary>
                    {approval.payload ? (
                      <pre className="mt-2 whitespace-pre-wrap text-xs text-muted">
                        Payload: {JSON.stringify(approval.payload, null, 2)}
                      </pre>
                    ) : null}
                    {approval.rubric_scores ? (
                      <pre className="mt-2 whitespace-pre-wrap text-xs text-muted">
                        Rubric: {JSON.stringify(approval.rubric_scores, null, 2)}
                      </pre>
                    ) : null}
                  </details>
                ) : null}
                {approval.status === "pending" ? (
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handleDecision(approval.id, "approved")}
                      disabled={updatingId === approval.id}
                    >
                      Approve
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDecision(approval.id, "rejected")}
                      disabled={updatingId === approval.id}
                      className={cn(
                        "border-[color:var(--danger)] text-[color:var(--danger)] hover:text-[color:var(--danger)]"
                      )}
                    >
                      Reject
                    </Button>
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default BoardApprovalsPanel;
