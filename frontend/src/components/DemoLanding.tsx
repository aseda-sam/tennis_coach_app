import React from 'react';
import { VideoIcon } from './Icons';
import './DemoLanding.css';

interface DemoLandingProps {
  onTryDemo: () => void;
  onUploadVideo: () => void;
}

const DemoLanding: React.FC<DemoLandingProps> = ({
  onTryDemo,
  onUploadVideo,
}) => {
  return (
    <div className="demo-landing">
      <div className="demo-landing__container">
        {/* Hero Section */}
        <div className="demo-landing__hero">
          <div className="demo-landing__hero-icon">
            <VideoIcon size={48} color="var(--color-primary)" />
          </div>
          <h1 className="demo-landing__title">
            See What's Possible with AI Tennis Analysis
          </h1>
          <p className="demo-landing__subtitle">
            Explore a fully-analyzed serve video before uploading your own
          </p>
        </div>

        {/* Feature Showcase */}
        <div className="demo-landing__features">
          <div className="demo-landing__feature-card">
            <div className="demo-landing__feature-icon">🎯</div>
            <h3 className="demo-landing__feature-title">Pose Analysis</h3>
            <p className="demo-landing__feature-description">
              Track key body positions and movements throughout your serve
            </p>
          </div>

          <div className="demo-landing__feature-card">
            <div className="demo-landing__feature-icon">⚡</div>
            <h3 className="demo-landing__feature-title">Contact Detection</h3>
            <p className="demo-landing__feature-description">
              Automatically identify ball contact moments with precise timestamps
            </p>
          </div>

          <div className="demo-landing__feature-card">
            <div className="demo-landing__feature-icon">📊</div>
            <h3 className="demo-landing__feature-title">Performance Metrics</h3>
            <p className="demo-landing__feature-description">
              Get insights on serve count, elbow angles, and more
            </p>
          </div>

          <div className="demo-landing__feature-card">
            <div className="demo-landing__feature-icon">🎬</div>
            <h3 className="demo-landing__feature-title">Interactive Video</h3>
            <p className="demo-landing__feature-description">
              Navigate through contacts, analyze frame by frame, and explore your technique
            </p>
          </div>
        </div>

        {/* CTA Section */}
        <div className="demo-landing__cta">
          <button
            className="demo-landing__cta-primary"
            onClick={onTryDemo}
            type="button"
          >
            Try Interactive Demo
          </button>
          <button
            className="demo-landing__cta-secondary"
            onClick={onUploadVideo}
            type="button"
          >
            Upload Your Video
          </button>
        </div>
      </div>
    </div>
  );
};

export default DemoLanding;
