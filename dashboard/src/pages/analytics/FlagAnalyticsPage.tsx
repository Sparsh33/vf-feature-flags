import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { analyticsApi } from "@/lib/analytics_api";
import { StatsCards } from "@/components/analytics/StatsCards";
import { CohortBarChart } from "@/components/analytics/CohortBarChart";
import { TimeSeriesChart } from "@/components/analytics/TimeSeriesChart";

type PresetRange = "1h" | "24h" | "7d" | "custom";
type Interval = "minute" | "hour" | "day";

interface RangeState {
  preset: PresetRange;
  from: string;
  to: string;
}

function computePresetRange(preset: PresetRange): { from: string; to: string } {
  const to = new Date();
  const deltas: Record<Exclude<PresetRange, "custom">, number> = {
    "1h": 60 * 60 * 1000,
    "24h": 24 * 60 * 60 * 1000,
    "7d": 7 * 24 * 60 * 60 * 1000,
  };
  if (preset === "custom") {
    return { from: to.toISOString(), to: to.toISOString() };
  }
  const from = new Date(to.getTime() - deltas[preset]);
  return { from: from.toISOString(), to: to.toISOString() };
}

function toInputLocal(isoString: string): string {
  // datetime-local expects 'YYYY-MM-DDTHH:mm'.
  const date = new Date(isoString);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function fromInputLocal(value: string): string {
  return new Date(value).toISOString();
}

export default function FlagAnalyticsPage(): JSX.Element {
  const { id: flagId } = useParams<{ id: string }>();
  const initialRange = useMemo(() => computePresetRange("24h"), []);
  const [range, setRange] = useState<RangeState>({
    preset: "24h",
    from: initialRange.from,
    to: initialRange.to,
  });
  const [interval, setInterval] = useState<Interval>("hour");

  const rangeParams = { from_ts: range.from, to_ts: range.to };

  const analyticsQuery = useQuery({
    queryKey: ["flag-analytics", flagId, rangeParams],
    queryFn: () => analyticsApi.getFlagAnalytics(flagId ?? "", rangeParams),
    enabled: Boolean(flagId),
  });

  const timeSeriesQuery = useQuery({
    queryKey: ["flag-time-series", flagId, rangeParams, interval],
    queryFn: () =>
      analyticsApi.getFlagTimeSeries(flagId ?? "", {
        ...rangeParams,
        interval,
      }),
    enabled: Boolean(flagId),
  });

  const handlePreset = (preset: PresetRange) => {
    if (preset === "custom") {
      setRange((prev) => ({ ...prev, preset }));
      return;
    }
    const next = computePresetRange(preset);
    setRange({ preset, ...next });
  };

  if (!flagId) {
    return (
      <div className="p-6 text-sm text-destructive">
        Missing flag id in URL.
      </div>
    );
  }

  const data = analyticsQuery.data;
  const defaultCount =
    data?.per_cohort.find((stat) => stat.cohort_name === "__fallback__")
      ?.count ?? 0;
  const notFoundCount =
    data?.per_cohort.find((stat) => stat.cohort_name === "__not_found__")
      ?.count ?? 0;

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">
            <span className="font-mono text-base text-muted-foreground">
              {data?.flag_key ?? flagId}
            </span>
          </h1>
          <p className="text-xs text-muted-foreground">Flag analytics</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1 rounded-md border p-1 text-xs">
            {(["1h", "24h", "7d", "custom"] as PresetRange[]).map((preset) => (
              <button
                key={preset}
                type="button"
                onClick={() => handlePreset(preset)}
                className={`rounded px-2 py-1 transition ${
                  range.preset === preset
                    ? "bg-slate-900 text-slate-50 dark:bg-slate-50 dark:text-slate-900"
                    : "hover:bg-muted"
                }`}
              >
                {preset}
              </button>
            ))}
          </div>
          {range.preset === "custom" ? (
            <div className="flex items-center gap-2 text-xs">
              <input
                type="datetime-local"
                value={toInputLocal(range.from)}
                onChange={(e) =>
                  setRange((prev) => ({
                    ...prev,
                    from: fromInputLocal(e.target.value),
                  }))
                }
                className="rounded border bg-background px-2 py-1"
              />
              <span className="text-muted-foreground">→</span>
              <input
                type="datetime-local"
                value={toInputLocal(range.to)}
                onChange={(e) =>
                  setRange((prev) => ({
                    ...prev,
                    to: fromInputLocal(e.target.value),
                  }))
                }
                className="rounded border bg-background px-2 py-1"
              />
            </div>
          ) : null}
          <select
            value={interval}
            onChange={(e) => setInterval(e.target.value as Interval)}
            className="rounded-md border bg-background px-2 py-1 text-xs"
          >
            <option value="minute">minute</option>
            <option value="hour">hour</option>
            <option value="day">day</option>
          </select>
        </div>
      </div>
      <StatsCards
        items={[
          {
            title: "Total requests",
            value: (data?.total_requests ?? 0).toLocaleString(),
          },
          { title: "Fallback (default)", value: defaultCount.toLocaleString() },
          { title: "Not found", value: notFoundCount.toLocaleString() },
        ]}
      />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-lg border bg-card p-4">
          <h2 className="mb-3 text-sm font-semibold">Cohort breakdown</h2>
          {analyticsQuery.isLoading ? (
            <div className="py-10 text-center text-sm text-muted-foreground">
              Loading…
            </div>
          ) : (
            <CohortBarChart data={data?.per_cohort ?? []} />
          )}
        </div>
        <div className="rounded-lg border bg-card p-4">
          <h2 className="mb-3 text-sm font-semibold">Over time ({interval})</h2>
          {timeSeriesQuery.isLoading ? (
            <div className="py-10 text-center text-sm text-muted-foreground">
              Loading…
            </div>
          ) : (
            <TimeSeriesChart buckets={timeSeriesQuery.data?.buckets ?? []} />
          )}
        </div>
      </div>
    </div>
  );
}
