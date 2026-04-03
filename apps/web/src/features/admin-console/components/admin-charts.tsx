import { cn } from "@/lib/utils";

type BarPoint = {
  label: string;
  value: number;
  detail?: string;
};

type DualBarPoint = {
  label: string;
  first: number;
  second: number;
};

type DistributionPoint = {
  label: string;
  count: number;
  share: number;
};

type SimpleBarChartProps = Readonly<{
  points: BarPoint[];
  emptyLabel: string;
  valueFormatter?: (value: number) => string;
  className?: string;
}>;

export function SimpleBarChart({
  points,
  emptyLabel,
  valueFormatter = (value) => String(value),
  className,
}: SimpleBarChartProps) {
  if (!points.length) {
    return <p className="text-sm leading-6 text-slate-300">{emptyLabel}</p>;
  }

  const maxValue = Math.max(...points.map((point) => point.value), 1);

  return (
    <div className={cn("space-y-3", className)}>
      {points.map((point) => (
        <div key={point.label} className="space-y-2">
          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3 text-sm">
            <span className="min-w-0 break-words text-slate-200">{point.label}</span>
            <span className="whitespace-nowrap text-right font-semibold text-white">
              {valueFormatter(point.value)}
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-white/8">
            <div
              className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-emerald-300"
              style={{ width: `${Math.max((point.value / maxValue) * 100, 4)}%` }}
            />
          </div>
          {point.detail ? (
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
              {point.detail}
            </p>
          ) : null}
        </div>
      ))}
    </div>
  );
}

type TrendChartProps = Readonly<{
  points: BarPoint[];
  emptyLabel: string;
  colorClassName?: string;
}>;

export function TrendChart({
  points,
  emptyLabel,
  colorClassName = "from-cyan-400 to-cyan-200",
}: TrendChartProps) {
  if (!points.length) {
    return <p className="text-sm leading-6 text-slate-300">{emptyLabel}</p>;
  }

  const maxValue = Math.max(...points.map((point) => point.value), 1);

  return (
    <div className="overflow-x-auto pb-2">
      <div className="flex min-w-[28rem] items-end gap-2">
        {points.map((point) => (
          <div
            key={point.label}
            className="flex min-w-[2.4rem] flex-1 flex-col items-center gap-2"
          >
            <div className="flex h-40 w-full items-end rounded-[1.25rem] bg-white/6 p-1">
              <div
                className={cn(
                  "w-full rounded-[0.9rem] bg-gradient-to-t",
                  colorClassName,
                )}
                style={{
                  height: `${Math.max((point.value / maxValue) * 100, 8)}%`,
                }}
              />
            </div>
            <span className="block w-full truncate text-center text-[11px] uppercase tracking-[0.18em] text-slate-500">
              {point.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

type DualTrendChartProps = Readonly<{
  points: DualBarPoint[];
  emptyLabel: string;
  firstLabel: string;
  secondLabel: string;
}>;

export function DualTrendChart({
  points,
  emptyLabel,
  firstLabel,
  secondLabel,
}: DualTrendChartProps) {
  if (!points.length) {
    return <p className="text-sm leading-6 text-slate-300">{emptyLabel}</p>;
  }

  const maxValue = Math.max(
    ...points.flatMap((point) => [point.first, point.second]),
    1,
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 text-xs uppercase tracking-[0.18em] text-slate-400">
        <span className="inline-flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-cyan-300" />
          {firstLabel}
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-300" />
          {secondLabel}
        </span>
      </div>
      <div className="grid grid-cols-5 gap-2 lg:grid-cols-10">
        {points.map((point) => (
          <div key={point.label} className="space-y-2">
            <div className="flex h-36 items-end justify-center gap-1 rounded-[1.15rem] bg-white/6 px-2 py-2">
              <div
                className="w-1/2 rounded-full bg-cyan-300"
                style={{
                  height: `${Math.max((point.first / maxValue) * 100, point.first ? 10 : 0)}%`,
                }}
              />
              <div
                className="w-1/2 rounded-full bg-emerald-300"
                style={{
                  height: `${Math.max((point.second / maxValue) * 100, point.second ? 10 : 0)}%`,
                }}
              />
            </div>
            <p className="truncate text-center text-[11px] uppercase tracking-[0.16em] text-slate-500">
              {point.label}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

type DistributionListProps = Readonly<{
  points: DistributionPoint[];
  emptyLabel: string;
}>;

export function DistributionList({
  points,
  emptyLabel,
}: DistributionListProps) {
  if (!points.length) {
    return <p className="text-sm leading-6 text-slate-300">{emptyLabel}</p>;
  }

  return (
    <div className="space-y-3">
      {points.map((point) => (
        <div key={point.label} className="space-y-2">
          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3 text-sm">
            <span className="min-w-0 break-words text-slate-200">{point.label}</span>
            <span className="whitespace-nowrap text-right font-semibold text-white">
              {point.count} · {(point.share * 100).toFixed(0)}%
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-white/8">
            <div
              className="h-full rounded-full bg-gradient-to-r from-cyan-300 via-sky-300 to-emerald-300"
              style={{ width: `${Math.max(point.share * 100, 4)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
