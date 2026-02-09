import { ElbowAngleMetric } from '../../../services/progressApi';
import './ConsistencyReport.css';

interface ConsistencyReportProps {
  elbowAngle: ElbowAngleMetric | null;
}

interface MetricRow {
  name: string;
  deviation: string;
  rating: 'excellent' | 'good' | 'fair' | 'needs_work';
}

const RATING_LABELS: Record<string, string> = {
  excellent: 'Excellent',
  good: 'Good',
  fair: 'Fair',
  needs_work: 'Needs Work',
};

function ConsistencyReport({ elbowAngle }: ConsistencyReportProps) {
  const rows: MetricRow[] = [];

  if (elbowAngle) {
    rows.push({
      name: 'Elbow Angle',
      deviation: `\u00B1 ${elbowAngle.consistency}\u00B0`,
      rating: elbowAngle.consistency_rating,
    });
  }

  if (rows.length === 0) {
    return null;
  }

  return (
    <div className="consistency-report">
      <h3 className="consistency-report-title">Consistency Report</h3>
      <div className="consistency-report-list">
        {rows.map((row) => (
          <div key={row.name} className="consistency-report-row">
            <span className="consistency-report-name">{row.name}</span>
            <span className="consistency-report-deviation">{row.deviation}</span>
            <span className={`consistency-report-badge rating-${row.rating}`}>
              {RATING_LABELS[row.rating]}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ConsistencyReport;
