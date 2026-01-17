import React from 'react';
import {
  AnalyticsIcon,
  BallDetectionIcon,
  PlayIcon,
  PoseDetectionIcon,
  UploadIcon,
  VideoIcon,
  ShareIcon,
  CheckIcon,
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
        {/* Hero Section with Integrated Demo Card */}
        <div className="demo-landing__hero-section">
          <div className="demo-landing__hero-content">
            <h1 className="demo-landing__title">
              Tennis feedback you can see in every frame
            </h1>
            <p className="demo-landing__subtitle">
              Review timing, contact, and body positions for serves and
              groundstrokes.
            </p>
          </div>

          {/* Cards Row */}
          <div className="demo-landing__cards-row">
            {/* Prominent Demo Card */}
            <div className="demo-landing__card demo-landing__card--gradient">
              <div className="demo-landing__card-inner">
                <div className="demo-landing__card-header">
                  <div className="demo-landing__card-icon demo-landing__card-icon--primary">
                    <PlayIcon size={20} color="white" />
                  </div>
                  <div className="demo-landing__card-title-wrap">
                    <div className="demo-landing__card-eyebrow">
                      Interactive demo
                    </div>
                    <h2 className="demo-landing__card-title">
                      Explore a sample analysis
                    </h2>
                  </div>
                </div>
                <p className="demo-landing__card-body">
                  Scrub through a real clip, jump between contacts, and review
                  technique and timing.
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
                <p className="demo-landing__demo-note">
                  Demo changes are not saved. Upload your own video to keep edits.
                </p>
              </div>
            </div>

            {/* Upload Card - Less Prominent */}
            <div className="demo-landing__card demo-landing__card--upload">
              <div className="demo-landing__card-header">
                <div className="demo-landing__card-icon demo-landing__card-icon--outline">
                  <UploadIcon size={16} color="var(--color-primary)" />
                </div>
                <div className="demo-landing__card-title-wrap">
                  <h2 className="demo-landing__card-title">Upload and analyze</h2>
                </div>
              </div>
              <p className="demo-landing__card-body">
                Upload a rally or serve to get posture metrics and timing insights.
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
        </div>

        {/* Features Section */}
        <div className="demo-landing__features-section">
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
                Track key positions and movements throughout the stroke.
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

        {/* Coming Soon Section */}
        <div className="demo-landing__coming-soon">
          <div className="demo-landing__coming-soon-header">
            <h3 className="demo-landing__coming-soon-title">Coming soon</h3>
            <p className="demo-landing__coming-soon-subtitle">
              More ways to improve your game.
            </p>
          </div>
          <div className="demo-landing__coming-soon-grid">
            <div className="demo-landing__coming-soon-item">
              <div className="demo-landing__coming-soon-icon-wrapper">
                <AnalyticsIcon size={20} color="var(--color-primary)" />
              </div>
              <div className="demo-landing__coming-soon-item-content">
                <h4 className="demo-landing__coming-soon-item-title">
                  Progress tracking
                </h4>
                <p className="demo-landing__coming-soon-item-description">
                  See how your technique improves over time with session comparisons.
                </p>
              </div>
            </div>
            <div className="demo-landing__coming-soon-item">
              <div className="demo-landing__coming-soon-icon-wrapper">
                <CheckIcon size={20} color="var(--color-primary)" />
              </div>
              <div className="demo-landing__coming-soon-item-content">
                <h4 className="demo-landing__coming-soon-item-title">
                  More shot types
                </h4>
                <p className="demo-landing__coming-soon-item-description">
                  Volleys, overheads, and other strokes coming soon.
                </p>
              </div>
            </div>
            <div className="demo-landing__coming-soon-item">
              <div className="demo-landing__coming-soon-icon-wrapper">
                <ShareIcon size={20} color="var(--color-primary)" />
              </div>
              <div className="demo-landing__coming-soon-item-content">
                <h4 className="demo-landing__coming-soon-item-title">
                  Share with coaches
                </h4>
                <p className="demo-landing__coming-soon-item-description">
                  Collaborate with coaches and get feedback on your sessions.
                </p>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};

export default DemoLanding;
