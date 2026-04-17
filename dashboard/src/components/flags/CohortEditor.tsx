import * as React from "react";
import { Plus, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { tryParseJson } from "@/lib/json";

export interface CohortRow {
  id: string;
  name: string;
  percentage: number;
  valueText: string;
}

interface CohortEditorProps {
  rows: CohortRow[];
  onChange: (rows: CohortRow[]) => void;
}

function makeId(): string {
  return Math.random().toString(36).slice(2, 10);
}

export function newCohortRow(partial: Partial<CohortRow> = {}): CohortRow {
  return {
    id: partial.id ?? makeId(),
    name: partial.name ?? "",
    percentage: partial.percentage ?? 0,
    valueText: partial.valueText ?? '""',
  };
}

export function CohortEditor({ rows, onChange }: CohortEditorProps) {
  const [lastTouched, setLastTouched] = React.useState<string | null>(null);

  const updateRow = (id: string, patch: Partial<CohortRow>): void => {
    onChange(rows.map((row) => (row.id === id ? { ...row, ...patch } : row)));
    setLastTouched(id);
  };

  const addRow = (): void => {
    const row = newCohortRow();
    onChange([...rows, row]);
    setLastTouched(row.id);
  };

  const removeRow = (id: string): void => {
    onChange(rows.filter((row) => row.id !== id));
  };

  const distributeRemaining = (): void => {
    if (rows.length === 0) return;
    const targetId = lastTouched ?? rows[rows.length - 1].id;
    const others = rows.filter((row) => row.id !== targetId);
    const othersSum = others.reduce((sum, row) => sum + row.percentage, 0);
    const remaining = Math.max(0, Math.min(100, 100 - othersSum));
    onChange(
      rows.map((row) =>
        row.id === targetId ? { ...row, percentage: remaining } : row,
      ),
    );
  };

  const sum = rows.reduce((total, row) => total + row.percentage, 0);
  const sumExact = Math.round(sum * 100) / 100;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Label>Cohorts</Label>
        <div className="flex items-center gap-2">
          <Badge
            variant={sumExact === 100 ? "success" : "destructive"}
            className="font-mono"
          >
            {sumExact}%
          </Badge>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={distributeRemaining}
            disabled={rows.length === 0}
          >
            Distribute remaining
          </Button>
          <Button type="button" size="sm" onClick={addRow}>
            <Plus className="mr-1 h-4 w-4" /> Add cohort
          </Button>
        </div>
      </div>
      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No cohorts yet. All traffic will receive the default value.
        </p>
      ) : (
        <div className="space-y-3">
          {rows.map((row) => {
            const parseResult = tryParseJson(row.valueText);
            const hasError = !parseResult.ok;
            return (
              <div
                key={row.id}
                className="grid grid-cols-12 gap-3 rounded-md border bg-card p-4"
              >
                <div className="col-span-5 space-y-1">
                  <Label htmlFor={`cohort-name-${row.id}`}>Name</Label>
                  <Input
                    id={`cohort-name-${row.id}`}
                    value={row.name}
                    onChange={(e) =>
                      updateRow(row.id, { name: e.target.value })
                    }
                    placeholder="e.g. beta-users"
                  />
                </div>
                <div className="col-span-3 space-y-1">
                  <Label htmlFor={`cohort-pct-${row.id}`}>Percentage</Label>
                  <Input
                    id={`cohort-pct-${row.id}`}
                    type="number"
                    min={0}
                    max={100}
                    step={0.01}
                    value={row.percentage}
                    onChange={(e) =>
                      updateRow(row.id, {
                        percentage: Number(e.target.value) || 0,
                      })
                    }
                  />
                </div>
                <div className="col-span-3 space-y-1">
                  <Label htmlFor={`cohort-val-${row.id}`}>Value (JSON)</Label>
                  <Textarea
                    id={`cohort-val-${row.id}`}
                    className="font-mono text-xs"
                    rows={2}
                    value={row.valueText}
                    onChange={(e) =>
                      updateRow(row.id, { valueText: e.target.value })
                    }
                  />
                  {hasError ? (
                    <p className="text-xs text-destructive">
                      {parseResult.error}
                    </p>
                  ) : null}
                </div>
                <div className="col-span-1 flex items-end justify-end">
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => removeRow(row.id)}
                    aria-label="Remove cohort"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function validateCohortRows(rows: CohortRow[]): {
  valid: boolean;
  reason?: string;
} {
  const sum = rows.reduce((total, row) => total + row.percentage, 0);
  const sumExact = Math.round(sum * 100) / 100;
  if (rows.length > 0 && sumExact !== 100) {
    return { valid: false, reason: "Cohort percentages must sum to 100." };
  }
  for (const row of rows) {
    if (!row.name.trim()) {
      return { valid: false, reason: "Every cohort needs a name." };
    }
    const parsed = tryParseJson(row.valueText);
    if (!parsed.ok) {
      return {
        valid: false,
        reason: `Cohort "${row.name}" has invalid JSON value.`,
      };
    }
  }
  return { valid: true };
}
