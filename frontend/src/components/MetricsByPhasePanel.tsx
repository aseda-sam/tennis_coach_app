import React, { useMemo, useState } from 'react';
import { MetricValue } from '../types/biomechanics';

const METRIC_DISPLAY_NAMES: Record<string, string> = {
  knee_flexion_min_deg: 'Knee Flexion',
  toss_peak_height: 'Toss Peak Height',
  toss_laterality: 'Toss Position',
};

function formatMetricValue(metric: MetricValue): string {
  if (metric.value === null) return 'N/A';
  if (metric.unit === 'deg' || metric.unit === 'degrees')
    return `${Math.round(metric.value)}\u00b0`;
  if (metric.unit === 'normalized') return metric.value.toFixed(2);
  if (metric.unit === 'ms') return `${metric.value} ms`;
  if (typeof metric.value === 'number' && Number.isInteger(metric.value))
    return String(metric.value);
  if (typeof metric.value === 'number') return metric.value.toFixed(2);
  return String(metric.value);
}

/** Group metrics by phase for collapsible sections. */
function groupMetricsByPhase(
  metrics: MetricValue[]
): Map<string | null, MetricValue[]> {
  const map = new Map<string | null, MetricValue[]>();
  for (const m of metrics) {
    const key = m.phase ?? null;
    const list = map.get(key) ?? [];
    list.push(m);
    map.set(key, list);
  }
  return map;
}

const PHASE_ORDER: (string | null)[] = [
  'toss',
  'trophy_load',
  'acceleration',
  'follow_through',
  null,
];

const PHASE_LABEL_MAP: Record<string, string> = {
  toss: 'Toss',
  trophy_load: 'Trophy & Load',
  acceleration: 'Acceleration',
  follow_through: 'Follow-Through',
};

interface MetricsByPhasePanelProps {
  metrics: MetricValue[];
}

const MetricsByPhasePanel: React.FC<MetricsByPhasePanelProps> = ({
  metrics,
}) => {
  const grouped = useMemo(() => groupMetricsByPhase(metrics), [metrics]);
  const [expandedPhases, setExpandedPhases] = useState<Set<string | null>>(
    () => new Set()
  );

  const toggle = (key: string | null) => {
    setExpandedPhases((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const sortedKeys = PHASE_ORDER.filter((k) => grouped.has(k));

  return (
    <div className="serve-biomechanics-detail__metrics-panel">
      <h4 className="serve-biomechanics-detail__metrics-title">
        Metrics by Phase
      </h4>
      <div className="serve-biomechanics-detail__metrics-groups">
        {sortedKeys.map((phaseKey) => {
          const list = grouped.get(phaseKey) ?? [];
          const label =
            phaseKey === null
              ? 'Unassigned'
              : (PHASE_LABEL_MAP[phaseKey] ??
                phaseKey
                  .replace(/_/g, ' ')
                  .replace(/\b\w/g, (c) => c.toUpperCase()));
          const isExpanded = expandedPhases.has(phaseKey);

          return (
            <div
              key={phaseKey ?? 'null'}
              className="serve-biomechanics-detail__phase-group"
            >
              <button
                type="button"
                className="serve-biomechanics-detail__phase-group-header"
                onClick={() => toggle(phaseKey)}
                aria-expanded={isExpanded}
              >
                <span className="serve-biomechanics-detail__phase-group-heading">
                  <span className="serve-biomechanics-detail__phase-group-label">
                    {label}
                  </span>
                  {!isExpanded && list.length > 0 && (
                    <span className="serve-biomechanics-detail__phase-group-summary">
                      {METRIC_DISPLAY_NAMES[list[0].metric_name] ??
                        list[0].metric_name.replace(/_/g, ' ')}
                      : {formatMetricValue(list[0])}
                    </span>
                  )}
                </span>
                <span
                  className="serve-biomechanics-detail__phase-group-chevron"
                  data-expanded={isExpanded}
                  aria-hidden
                >
                  &#9662;
                </span>
              </button>
              {isExpanded && (
                <div className="serve-biomechanics-detail__phase-group-body">
                  <table className="serve-biomechanics-detail__metrics-table">
                    <thead>
                      <tr>
                        <th>Metric</th>
                        <th>Value</th>
                        <th>Unit</th>
                      </tr>
                    </thead>
                    <tbody>
                      {list.map((m) => (
                        <tr key={m.metric_name}>
                          <td>
                            {METRIC_DISPLAY_NAMES[m.metric_name] ??
                              m.metric_name.replace(/_/g, ' ')}
                          </td>
                          <td>{formatMetricValue(m)}</td>
                          <td>{m.unit || '\u2014'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default MetricsByPhasePanel;
