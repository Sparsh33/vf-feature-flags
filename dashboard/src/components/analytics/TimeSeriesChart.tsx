import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { format, parseISO } from "date-fns";

import type { TimeSeriesBucket } from "@/types/feature_api";

interface TimeSeriesChartProps {
  buckets: TimeSeriesBucket[];
  height?: number;
  compact?: boolean;
}

// Deterministic palette for cohort lines.
const PALETTE = [
  "#10b981", // emerald
  "#3b82f6", // blue
  "#f59e0b", // amber
  "#8b5cf6", // violet
  "#ef4444", // red
  "#14b8a6", // teal
  "#f97316", // orange
  "#6366f1", // indigo
];

function colorFor(name: string, idx: number): string {
  if (name === "__fallback__" || name === "__not_found__") return "#a1a1aa";
  return PALETTE[idx % PALETTE.length];
}

export function TimeSeriesChart({
  buckets,
  height = 320,
  compact = false,
}: TimeSeriesChartProps): JSX.Element {
  if (buckets.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground"
        style={{ height }}
      >
        No time-series data.
      </div>
    );
  }
  const cohortNames = Array.from(
    new Set(buckets.flatMap((bucket) => Object.keys(bucket.counts_by_cohort)))
  );
  const chartData = buckets.map((bucket) => {
    const row: Record<string, string | number> = { ts: bucket.ts };
    for (const name of cohortNames) {
      row[name] = bucket.counts_by_cohort[name] ?? 0;
    }
    return row;
  });
  const formatTick = (value: string): string => {
    try {
      return format(parseISO(value), compact ? "HH:mm" : "MMM d HH:mm");
    } catch {
      return value;
    }
  };
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData}>
        {!compact ? (
          <CartesianGrid
            strokeDasharray="3 3"
            className="stroke-zinc-200 dark:stroke-zinc-800"
          />
        ) : null}
        <XAxis
          dataKey="ts"
          tickFormatter={formatTick}
          tick={{ fontSize: 10 }}
          hide={compact}
        />
        <YAxis tick={{ fontSize: 10 }} hide={compact} />
        {!compact ? (
          <Tooltip
            labelFormatter={(value: string) => formatTick(value)}
            contentStyle={{ fontSize: 12 }}
          />
        ) : null}
        {cohortNames.map((name, idx) => (
          <Area
            key={name}
            type="monotone"
            dataKey={name}
            stackId="1"
            stroke={colorFor(name, idx)}
            fill={colorFor(name, idx)}
            fillOpacity={0.4}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}
