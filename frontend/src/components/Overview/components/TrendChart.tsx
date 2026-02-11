import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { ProgressMetricDataPoint } from '../../../services/progressApi';
import './TrendChart.css';

interface TrendChartProps {
  dataPoints: ProgressMetricDataPoint[];
}

interface TooltipPayloadItem {
  value: number;
  payload: ProgressMetricDataPoint;
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: TooltipPayloadItem[];
}) {
  if (!active || !payload || payload.length === 0) return null;

  const data = payload[0];
  return (
    <div className="trend-chart-tooltip">
      <p className="trend-chart-tooltip-date">{data.payload.date}</p>
      <p className="trend-chart-tooltip-value">{data.value}&deg;</p>
      <p className="trend-chart-tooltip-count">
        {data.payload.count} serve{data.payload.count !== 1 ? 's' : ''}
      </p>
    </div>
  );
}

function TrendChart({ dataPoints }: TrendChartProps) {
  if (dataPoints.length === 0) return null;

  return (
    <div className="trend-chart">
      <h3 className="trend-chart-title">Elbow Angle Over Time</h3>
      <div className="trend-chart-container">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart
            data={dataPoints}
            margin={{ top: 8, right: 16, left: 8, bottom: 8 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--color-border-light)"
            />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12, fill: 'var(--color-text-muted)' }}
              tickLine={false}
              axisLine={{ stroke: 'var(--color-border-light)' }}
            />
            <YAxis
              tick={{ fontSize: 12, fill: 'var(--color-text-muted)' }}
              tickLine={false}
              axisLine={{ stroke: 'var(--color-border-light)' }}
              unit="&deg;"
            />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey="avg"
              stroke="var(--color-primary)"
              strokeWidth={2}
              dot={{ r: 4, fill: 'var(--color-primary)' }}
              activeDot={{ r: 6, fill: 'var(--color-primary-dark)' }}
              isAnimationActive={true}
              animationDuration={800}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default TrendChart;
