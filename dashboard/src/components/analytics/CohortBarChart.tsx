import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  type TooltipProps,
  XAxis,
  YAxis,
} from "recharts";

import type { CohortStats } from "@/types/feature_api";

interface CohortBarChartProps {
  data: CohortStats[];
  height?: number;
}

const FALLBACK_NAMES = new Set(["__fallback__", "__not_found__"]);

function colorFor(name: string): string {
  if (FALLBACK_NAMES.has(name)) return "#a1a1aa"; // zinc-400
  return "#10b981"; // emerald-500
}

function CustomTooltip({
  active,
  payload,
}: TooltipProps<number, string>): JSX.Element | null {
  if (!active || !payload || payload.length === 0) return null;
  const item = payload[0].payload as CohortStats & { label: string };
  return (
    <div className="rounded-md border bg-background px-3 py-2 shadow-md">
      <div className="text-xs font-medium">{item.label}</div>
      <div className="mt-1 text-xs text-muted-foreground">
        count: <span className="font-mono">{item.count}</span>
      </div>
      <div className="text-xs text-muted-foreground">
        pct: <span className="font-mono">{item.percentage.toFixed(1)}%</span>
      </div>
    </div>
  );
}

export function CohortBarChart({
  data,
  height = 280,
}: CohortBarChartProps): JSX.Element {
  const chartData = data.map((stat) => ({
    ...stat,
    label: stat.cohort_name || stat.cohort_id || "unknown",
  }));
  if (chartData.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground"
        style={{ height }}
      >
        No cohort data in this range.
      </div>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={chartData}>
        <CartesianGrid
          strokeDasharray="3 3"
          className="stroke-zinc-200 dark:stroke-zinc-800"
        />
        <XAxis dataKey="label" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
          {chartData.map((entry, idx) => (
            <Cell key={idx} fill={colorFor(entry.label)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
