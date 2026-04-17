export interface StatItem {
  title: string;
  value: string | number;
  subtitle?: string;
}

interface StatsCardsProps {
  items: StatItem[];
  columns?: number;
}

export function StatsCards({ items, columns = 3 }: StatsCardsProps): JSX.Element {
  const gridClass =
    columns === 2
      ? "grid grid-cols-1 gap-4 md:grid-cols-2"
      : columns === 4
      ? "grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4"
      : "grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3";
  return (
    <div className={gridClass}>
      {items.map((item) => (
        <div
          key={item.title}
          className="rounded-lg border bg-card p-4 shadow-sm"
        >
          <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {item.title}
          </div>
          <div className="mt-2 text-2xl font-semibold tabular-nums">
            {item.value}
          </div>
          {item.subtitle ? (
            <div className="mt-1 text-xs text-muted-foreground">{item.subtitle}</div>
          ) : null}
        </div>
      ))}
    </div>
  );
}
