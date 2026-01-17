import React from 'react';
import {
  AnalyticsIcon,
  BallDetectionIcon,
  PlayIcon,
  PoseDetectionIcon,
  UploadIcon,
  VideoIcon,
} from './Icons';
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
        {/* Hero */}
        <div className="demo-landing__hero">
          <div className="demo-landing__badge">
            <span className="demo-landing__badge-dot" />
            Interactive demo
          </div>

          <div className="demo-landing__hero-icon">
            <VideoIcon size={44} color="var(--color-primary)" />
          </div>

          <h1 className="demo-landing__title">
            See what's possible with AI tennis analysis
          </h1>
          <p className="demo-landing__subtitle">
            Explore a fully analyzed serve video before uploading your own.
          </p>
        </div>

        {/* Main layout */}
        <div className="demo-landing__layout">
          {/* Primary cards */}
          <div className="demo-landing__primary">
            <div className="demo-landing__card demo-landing__card--gradient">
              <div className="demo-landing__card-header">
                <div className="demo-landing__card-icon demo-landing__card-icon--primary">
                  <PlayIcon size={18} color="white" />
                </div>
                <div className="demo-landing__card-title-wrap">
                  <div className="demo-landing__card-eyebrow">
                    See how it works
                  </div>
                  <h2 className="demo-landing__card-title">
                    Explore a sample analyzed serve
                  </h2>
                </div>
              </div>
              <p className="demo-landing__card-body">
                Scrub, jump between contacts, and review technique insights—no
                upload required.
              </p>
              <div className="demo-landing__card-actions">
                <button
                  className="demo-landing__cta-primary"
                  onClick={onTryDemo}
                  type="button"
                >
                  View demo analysis
                </button>
              </div>
            </div>

            <div className="demo-landing__card demo-landing__card--surface">
              <div className="demo-landing__card-header">
                <div className="demo-landing__card-icon demo-landing__card-icon--outline">
                  <UploadIcon size={18} color="var(--color-primary)" />
                </div>
                <div className="demo-landing__card-title-wrap">
                  <div className="demo-landing__card-eyebrow">
                    Ready for your own video?
                  </div>
                  <h2 className="demo-landing__card-title">Upload and analyze</h2>
                </div>
              </div>
              <p className="demo-landing__card-body">
                Upload a serve to get posture metrics and contact timing insights.
              </p>
              <div className="demo-landing__card-actions">
                <button
                  className="demo-landing__cta-secondary"
                  onClick={onUploadVideo}
                  type="button"
                >
                  Upload your video
                </button>
              </div>
            </div>
          </div>

          {/* Feature grid */}
          <div className="demo-landing__features">
            <div className="demo-landing__features-header">
              <h3 className="demo-landing__features-title">What you'll get</h3>
              <p className="demo-landing__features-subtitle">
                A realistic preview of the workflow and insights.
              </p>
            </div>

            <div className="demo-landing__feature-grid">
              <div className="demo-landing__feature-card">
                <div className="demo-landing__feature-icon demo-landing__feature-icon--pose">
                  <PoseDetectionIcon size={20} color="white" />
                </div>
                <h4 className="demo-landing__feature-title">Pose analysis</h4>
                <p className="demo-landing__feature-description">
                  Track key positions and movements throughout the serve.
                </p>
              </div>

              <div className="demo-landing__feature-card">
                <div className="demo-landing__feature-icon demo-landing__feature-icon--contact">
                  <BallDetectionIcon size={20} color="white" />
                </div>
                <h4 className="demo-landing__feature-title">Contact markers</h4>
                <p className="demo-landing__feature-description">
                  Jump to key moments and review timing with timestamps.
                </p>
              </div>

              <div className="demo-landing__feature-card">
                <div className="demo-landing__feature-icon demo-landing__feature-icon--metrics">
                  <AnalyticsIcon size={20} color="white" />
                </div>
                <h4 className="demo-landing__feature-title">Performance metrics</h4>
                <p className="demo-landing__feature-description">
                  See angles and metrics computed from existing contacts.
                </p>
              </div>

              <div className="demo-landing__feature-card">
                <div className="demo-landing__feature-icon demo-landing__feature-icon--video">
                  <VideoIcon size={20} color="white" />
                </div>
                <h4 className="demo-landing__feature-title">Interactive video</h4>
                <p className="demo-landing__feature-description">
                  Frame-by-frame controls and fast navigation between contacts.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer note */}
        <div className="demo-landing__footer">
          Demo is read-only. Upload your own video to save edits.
        </div>
      </div>
    </div>
  );
};

export default DemoLanding;
