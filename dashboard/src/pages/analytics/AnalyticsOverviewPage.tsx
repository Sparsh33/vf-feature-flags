import { useMemo } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { BarChart3 } from "lucide-react";

import { analyticsApi } from "@/lib/analytics_api";
import type { FlagSummary } from "@/types/feature_api";
import { StatsCards } from "@/components/analytics/StatsCards";
import { TimeSeriesChart } from "@/components/analytics/TimeSeriesChart";
import { CohortBarChart } from "@/components/analytics/CohortBarChart";

function last24hRange(): { from_ts: string; to_ts: string } {
  const to = new Date();
  const from = new Date(to.getTime() - 24 * 60 * 60 * 1000);
  return { from_ts: from.toISOString(), to_ts: to.toISOString() };
}

export default function AnalyticsOverviewPage(): JSX.Element {
  // TODO: Replace this fan-out with `/analytics/overview` once Agent E ships the endpoint.
  // MVP: list flags + per-flag analytics + per-flag sparkline.
  const flagsQuery = useQuery<FlagSummary[]>({
    queryKey: ["flags-list-for-overview"],
    queryFn: () => analyticsApi.listFlags(),
  });

  const range = useMemo(last24hRange, []);
  const flags = flagsQuery.data ?? [];

  const analyticsQueries = useQueries({
    queries: flags.map((flag) => ({
      queryKey: ["flag-analytics", flag.id, range.from_ts, range.to_ts],
      queryFn: () => analyticsApi.getFlagAnalytics(flag.id, range),
      enabled: flags.length > 0,
    })),
  });

  const sparklineQueries = useQueries({
    queries: flags.map((flag) => ({
      queryKey: ["flag-sparkline", flag.id, range.from_ts, range.to_ts],
      queryFn: () =>
        analyticsApi.getFlagTimeSeries(flag.id, { ...range, interval: "hour" }),
      enabled: flags.length > 0,
    })),
  });

  const totalFlags = flags.length;
  const totalEvals = analyticsQueries.reduce(
    (acc, query) => acc + (query.data?.total_requests ?? 0),
    0,
  );
  const combinedCohorts = useMemo(() => {
    const map = new Map<string, { count: number }>();
    for (const query of analyticsQueries) {
      if (!query.data) continue;
      for (const stat of query.data.per_cohort) {
        const label = stat.cohort_name || stat.cohort_id || "unknown";
        const existing = map.get(label)?.count ?? 0;
        map.set(label, { count: existing + stat.count });
      }
    }
    const totalCount = Array.from(map.values()).reduce(
      (acc, v) => acc + v.count,
      0,
    );
    return Array.from(map.entries()).map(([label, { count }]) => ({
      cohort_name: label,
      count,
      percentage: totalCount > 0 ? (count / totalCount) * 100 : 0,
    }));
  }, [analyticsQueries]);

  if (flagsQuery.isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center text-sm text-muted-foreground">
        Loading analytics…
      </div>
    );
  }
  if (flagsQuery.isError) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center text-sm text-destructive">
        Failed to load flags.
      </div>
    );
  }
  if (flags.length === 0) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3 text-center">
        <BarChart3 className="h-10 w-10 text-muted-foreground" />
        <div className="text-sm text-muted-foreground">
          No flags yet. Create one from the{" "}
          <Link to="/chat" className="font-medium text-foreground underline">
            flag builder
          </Link>
          .
        </div>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-xl font-semibold">Analytics overview</h1>
        <p className="text-xs text-muted-foreground">
          Last 24 hours, all flags.
        </p>
      </div>
      <StatsCards
        items={[
          { title: "Total flags", value: totalFlags },
          { title: "Total evals (24h)", value: totalEvals.toLocaleString() },
          {
            title: "Unique cohorts",
            value: combinedCohorts.length,
            subtitle: "Across all flags",
          },
        ]}
      />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-lg border bg-card p-4">
          <h2 className="mb-3 text-sm font-semibold">
            Evals per cohort (all flags)
          </h2>
          <CohortBarChart data={combinedCohorts} />
        </div>
        <div className="rounded-lg border bg-card p-4">
          <h2 className="mb-3 text-sm font-semibold">Per-flag breakdown</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs uppercase text-muted-foreground">
                  <th className="py-2 font-medium">Flag</th>
                  <th className="py-2 font-medium">Evals (24h)</th>
                  <th className="py-2 font-medium">Trend</th>
                  <th className="py-2" />
                </tr>
              </thead>
              <tbody>
                {flags.map((flag, idx) => {
                  const analytics = analyticsQueries[idx]?.data;
                  const sparkline = sparklineQueries[idx]?.data;
                  return (
                    <tr key={flag.id} className="border-b last:border-0">
                      <td className="py-2">
                        <div className="font-mono text-xs">{flag.flag_key}</div>
                        <div className="text-xs text-muted-foreground">
                          {flag.name}
                        </div>
                      </td>
                      <td className="py-2 tabular-nums">
                        {analytics?.total_requests?.toLocaleString() ?? "—"}
                      </td>
                      <td className="py-2" style={{ width: 120 }}>
                        {sparkline && sparkline.buckets.length > 0 ? (
                          <div style={{ width: 120, height: 40 }}>
                            <TimeSeriesChart
                              buckets={sparkline.buckets}
                              height={40}
                              compact
                            />
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            —
                          </span>
                        )}
                      </td>
                      <td className="py-2">
                        <Link
                          to={`/flags/${flag.id}/analytics`}
                          className="text-xs font-medium text-primary underline"
                        >
                          Details
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
