import { useState } from 'react';
import { useProgress } from '../../hooks/useProgress';
import LoadingIndicator from '../LoadingIndicator';
import CourtSideDiagram from './components/CourtSideDiagram';
import ConsistencyReport from './components/ConsistencyReport';
import MetricCard from './components/MetricCard';
import TimeFilter from './components/TimeFilter';
import TrendChart from './components/TrendChart';
import './Overview.css';

function Overview() {
  const [timePeriod, setTimePeriod] = useState('30d');
  const { progress, loading, error } = useProgress(timePeriod);

  if (loading) {
    return (
      <div className="overview">
        <div className="overview-loading">
          <LoadingIndicator size="lg" label="Loading progress..." />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="overview">
        <div className="overview-error">
          <p>Failed to load progress data. Please try again.</p>
        </div>
      </div>
    );
  }

  if (!progress || progress.total_videos < 2) {
    return (
      <div className="overview">
        <div className="overview-header">
          <div>
            <h2 className="overview-title">Progress Overview</h2>
            <p className="overview-subtitle">
              Track your serve improvement over time
            </p>
          </div>
        </div>
        <div className="overview-empty">
          <p className="overview-empty-text">
            Upload a few more serves to start tracking your progress.
          </p>
          <p className="overview-empty-subtext">
            We need at least 2 video sessions to show trends.
          </p>
        </div>
      </div>
    );
  }

  const { metrics, court_side } = progress;

  return (
    <div className="overview">
      <div className="overview-header">
        <div>
          <h2 className="overview-title">Progress Overview</h2>
          <p className="overview-subtitle">
            Track your serve improvement over time
          </p>
        </div>
        <div className="overview-header-right">
          <TimeFilter value={timePeriod} onChange={setTimePeriod} />
          <span className="overview-serve-count">
            {progress.total_serves} serve
            {progress.total_serves !== 1 ? 's' : ''} across{' '}
            {progress.total_videos} video
            {progress.total_videos !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      <div className="overview-metrics-row">
        {metrics.elbow_angle && (
          <MetricCard
            title="Elbow Angle"
            value={metrics.elbow_angle.current_avg}
            unit="deg"
            trend={metrics.elbow_angle.trend}
            consistencyLabel={`\u00B1 ${metrics.elbow_angle.consistency}\u00B0`}
            consistencyRating={metrics.elbow_angle.consistency_rating}
            delay={0}
          />
        )}
        {metrics.knee_bend && (
          <MetricCard
            title="Knee Bend Rate"
            value={Math.round(metrics.knee_bend.current_rate * 100)}
            unit="%"
            trend={metrics.knee_bend.trend}
            delay={100}
          />
        )}
      </div>

      {metrics.elbow_angle && metrics.elbow_angle.data_points.length > 0 && (
        <TrendChart dataPoints={metrics.elbow_angle.data_points} />
      )}

      <div className="overview-bottom-row">
        <CourtSideDiagram courtSide={court_side} />
        <ConsistencyReport elbowAngle={metrics.elbow_angle} />
      </div>
    </div>
  );
}

export default Overview;
