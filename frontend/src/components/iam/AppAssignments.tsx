"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";

export interface Assignment {
  id: string;
  subject_type: "group" | "user";
  subject_id: string;
  subject_name?: string;
  entitlement_id: string;
  entitlement_name?: string;
}

interface Props {
  appId: string;
  entitlements: { id: string; display_name: string }[];
  listAssignments: (appId: string) => Promise<Assignment[]>;
  addAssignment: (appId: string, payload: { subject_type: "group" | "user"; subject_id: string; entitlement_id: string }) => Promise<any>;
  removeAssignment: (appId: string, assignmentId: string) => Promise<any>;
}

export default function AppAssignments({ appId, entitlements, listAssignments, addAssignment, removeAssignment }: Props) {
  const queryClient = useQueryClient();
  const { data: assignments = [], isLoading } = useQuery({
    queryKey: ["app-assignments", appId],
    queryFn: () => listAssignments(appId),
    enabled: !!appId,
  });

  const addMutation = useMutation({
    mutationFn: (payload: { subject_type: "group" | "user"; subject_id: string; entitlement_id: string }) => addAssignment(appId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["app-assignments", appId] }),
  });

  const removeMutation = useMutation({
    mutationFn: (assignmentId: string) => removeAssignment(appId, assignmentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["app-assignments", appId] }),
  });

  const grouped = useMemo(() => {
    const byEnt: Record<string, Assignment[]> = {};
    assignments.forEach((a) => {
      byEnt[a.entitlement_id] = byEnt[a.entitlement_id] || [];
      byEnt[a.entitlement_id].push(a);
    });
    return byEnt;
  }, [assignments]);

  if (isLoading) return <div className="text-sm text-text-muted">Loading assignments...</div>;

  return (
    <div className="space-y-4">
      {entitlements.length === 0 && <p className="text-sm text-text-muted">No entitlements defined.</p>}
      {entitlements.map((ent) => {
        const items = grouped[ent.id] || [];
        return (
          <div key={ent.id} className="border border-surface-card-border rounded p-3">
            <div className="flex items-center justify-between mb-2">
              <div>
                <div className="text-sm font-semibold text-text-main">{ent.display_name}</div>
                <div className="text-xs text-text-muted">{items.length} assignments</div>
              </div>
            </div>
            <div className="space-y-2">
              {items.length === 0 ? (
                <div className="text-xs text-text-muted">No assignments yet.</div>
              ) : (
                items.map((a) => (
                  <div key={a.id} className="flex items-center justify-between bg-surface-hover rounded px-2 py-1 text-xs text-text-muted">
                    <div className="flex items-center gap-2">
                      <span className={clsx("px-2 py-0.5 rounded-full", a.subject_type === "group" ? "bg-blue-100 text-blue-800" : "bg-green-100 text-green-800")}>{a.subject_type}</span>
                      <span className="font-mono">{a.subject_name || a.subject_id}</span>
                    </div>
                    <button
                      onClick={() => removeMutation.mutate(a.id)}
                      className="text-red-600 hover:text-red-700"
                      disabled={removeMutation.isPending}
                    >
                      Remove
                    </button>
                  </div>
                ))
              )}
            </div>
            <AddAssignmentForm entitlements={entitlements} currentEnt={ent.id} onAdd={(payload) => addMutation.mutate(payload)} pending={addMutation.isPending} />
          </div>
        );
      })}
    </div>
  );
}

function AddAssignmentForm({ entitlements, currentEnt, onAdd, pending }: { entitlements: { id: string; display_name: string }[]; currentEnt: string; onAdd: (payload: { subject_type: "group" | "user"; subject_id: string; entitlement_id: string }) => void; pending: boolean; }) {
  const [subjectType, setSubjectType] = useState<"group" | "user">("group");
  const [subjectId, setSubjectId] = useState("");

  return (
    <div className="mt-3 flex flex-col md:flex-row gap-2 items-start md:items-center text-xs">
      <select
        value={subjectType}
        onChange={(e) => setSubjectType(e.target.value as any)}
        className="px-2 py-1 border border-surface-card-border rounded"
      >
        <option value="group">Group/Team</option>
        <option value="user">Person</option>
      </select>
      <input
        value={subjectId}
        onChange={(e) => setSubjectId(e.target.value)}
        placeholder={subjectType === "group" ? "group name" : "user email/username"}
        className="flex-1 px-2 py-1 border border-surface-card-border rounded"
      />
      <button
        onClick={() => {
          if (!subjectId.trim()) return;
          onAdd({ subject_type: subjectType, subject_id: subjectId.trim(), entitlement_id: currentEnt });
          setSubjectId("");
        }}
        disabled={pending}
        className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
      >
        {pending ? "Adding..." : "Add"}
      </button>
    </div>
  );
}
