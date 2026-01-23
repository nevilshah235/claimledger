'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Card } from './ui/Card';

type Kpi = {
  label: string;
  value: number;
  format: (v: number) => string;
  deltaLabel: string;
};

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

function useInViewOnce<T extends Element>() {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    if (!ref.current) return;
    if (inView) return;

    const el = ref.current;
    const obs = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry?.isIntersecting) {
          setInView(true);
          obs.disconnect();
        }
      },
      { threshold: 0.2 }
    );

    obs.observe(el);
    return () => obs.disconnect();
  }, [inView]);

  return { ref, inView } as const;
}

export function FinanceKpiStrip() {
  const kpis: Kpi[] = useMemo(
    () => [
      {
        label: 'Cost per evaluation',
        value: 0.35,
        format: (v) => `$${v.toFixed(2)}`,
        deltaLabel: '−8% vs baseline',
      },
      {
        label: 'Avg time to decision',
        value: 28,
        format: (v) => `${Math.round(v)}s`,
        deltaLabel: '−12% this week',
      },
      {
        label: 'Settlement finality',
        value: 2.0,
        format: (v) => `${v.toFixed(1)}s`,
        deltaLabel: 'p95 on testnet',
      },
      {
        label: 'Approval rate',
        value: 0.92,
        format: (v) => `${Math.round(v * 100)}%`,
        deltaLabel: '+3% QoQ',
      },
    ],
    []
  );

  const { ref, inView } = useInViewOnce<HTMLDivElement>();
  const [animated, setAnimated] = useState<number[]>(() => kpis.map(() => 0));

  useEffect(() => {
    if (!inView) return;

    const start = performance.now();
    const duration = 1400;

    let raf = 0;
    const tick = (t: number) => {
      const p = clamp((t - start) / duration, 0, 1);
      const eased = 1 - Math.pow(1 - p, 4);
      setAnimated(kpis.map((k) => k.value * eased));

      if (p < 1) raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [inView, kpis]);

  return (
    <section className="py-10 sm:py-12 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <h2 className="text-2xl sm:text-3xl font-bold text-text-primary mt-1">
            Operational metrics that finance teams care about
          </h2>
        </div>

        <div ref={ref} className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {kpis.map((k, idx) => (
            <Card key={k.label} padding="md" className="card-enhanced">
              <div className="text-xs font-semibold tracking-wide text-text-secondary">{k.label}</div>
              <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-text-primary tabular-nums">
                {k.format(animated[idx] ?? 0)}
              </div>
              <div className="mt-2 text-xs text-text-muted">{k.deltaLabel}</div>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}

export default FinanceKpiStrip;

