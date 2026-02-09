import { CourtSideDistribution } from '../../../services/progressApi';
import './CourtSideDiagram.css';

interface CourtSideDiagramProps {
  courtSide: CourtSideDistribution;
}

function CourtSideDiagram({ courtSide }: CourtSideDiagramProps) {
  const total = courtSide.deuce + courtSide.ad + courtSide.unknown;
  const deuceOpacity = total > 0 ? 0.2 + 0.6 * (courtSide.deuce / total) : 0.2;
  const adOpacity = total > 0 ? 0.2 + 0.6 * (courtSide.ad / total) : 0.2;

  return (
    <div className="court-side-diagram">
      <h3 className="court-side-title">Court Side Distribution</h3>
      <svg
        viewBox="0 0 200 160"
        className="court-svg"
        role="img"
        aria-label={`Deuce side: ${courtSide.deuce} serves, Ad side: ${courtSide.ad} serves`}
      >
        {/* Court outline */}
        <rect
          x="10"
          y="10"
          width="180"
          height="140"
          fill="none"
          stroke="var(--color-border)"
          strokeWidth="1.5"
          rx="2"
        />

        {/* Center service line */}
        <line
          x1="100"
          y1="10"
          x2="100"
          y2="150"
          stroke="var(--color-border)"
          strokeWidth="1"
        />

        {/* Service line */}
        <line
          x1="10"
          y1="80"
          x2="190"
          y2="80"
          stroke="var(--color-border)"
          strokeWidth="1"
        />

        {/* Deuce side (right box when facing net) */}
        <rect
          x="100"
          y="10"
          width="90"
          height="70"
          fill="var(--color-primary)"
          opacity={deuceOpacity}
          className="court-zone court-zone-deuce"
        />

        {/* Ad side (left box when facing net) */}
        <rect
          x="10"
          y="10"
          width="90"
          height="70"
          fill="var(--color-primary)"
          opacity={adOpacity}
          className="court-zone court-zone-ad"
        />

        {/* Labels */}
        <text
          x="145"
          y="40"
          textAnchor="middle"
          className="court-zone-label"
        >
          Deuce
        </text>
        <text
          x="145"
          y="58"
          textAnchor="middle"
          className="court-zone-count"
        >
          {courtSide.deuce}
        </text>

        <text
          x="55"
          y="40"
          textAnchor="middle"
          className="court-zone-label"
        >
          Ad
        </text>
        <text
          x="55"
          y="58"
          textAnchor="middle"
          className="court-zone-count"
        >
          {courtSide.ad}
        </text>
      </svg>
    </div>
  );
}

export default CourtSideDiagram;
