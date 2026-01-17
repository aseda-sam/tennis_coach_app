import React from 'react';
import './DemoLanding.css';
import {
  AnalyticsIcon,
  BallDetectionIcon,
  PlayIcon,
  PoseDetectionIcon,
  UploadIcon,
  VideoIcon,
} from './Icons';

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
              Tennis Feedback You Can See in Every Frame
            </h1>
            <p className="demo-landing__subtitle">
              We break down body and ball positions for serves and
              groundstrokes to help you understand your technique better.
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
                    Interactive Demo
                    </div>
                    <h2 className="demo-landing__card-title">
                    Explore a Sample Analysis
                    </h2>
                  </div>
                </div>
                <p className="demo-landing__card-body">
                Start with a real clip and follow each moment. Jump between
                contacts, review timing, and see what stands out.
                </p>
                <div className="demo-landing__card-actions">
                  <button
                    className="demo-landing__cta-primary"
                    onClick={onTryDemo}
                    type="button"
                  >
                    Try a Demo Without Uploading a Video Yet
                  </button>
                </div>
              </div>
            </div>

            {/* Upload Card - Less Prominent */}
            <div className="demo-landing__card demo-landing__card--upload">
              <div className="demo-landing__card-inner">
                <div className="demo-landing__card-header">
                  <div className="demo-landing__card-icon demo-landing__card-icon--outline">
                    <UploadIcon size={20} color="var(--color-primary)" />
                  </div>
                  <div className="demo-landing__card-title-wrap">
                    <div className="demo-landing__card-eyebrow">
                      Ready to upload?
                    </div>
                    <h2 className="demo-landing__card-title">Upload and Analyze</h2>
                  </div>
                </div>
                <p className="demo-landing__card-body">
                  Ready to see your own swing. Upload a rally or serve and we will
                  map timing, contact, and posture.
                </p>
                <div className="demo-landing__card-actions">
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
          </div>
        </div>

        {/* Features Section */}
        <div className="demo-landing__features-section">
          <div className="demo-landing__features-header">
            <h3 className="demo-landing__features-title">What You'll Get</h3>
          </div>

          <div className="demo-landing__feature-grid">
            <div className="demo-landing__feature-card">
              <div className="demo-landing__feature-icon demo-landing__feature-icon--pose">
                <PoseDetectionIcon size={20} color="white" />
              </div>
              <h4 className="demo-landing__feature-title">Pose Analysis</h4>
              <p className="demo-landing__feature-description">
                Track key positions and movements throughout the stroke.
              </p>
            </div>

            <div className="demo-landing__feature-card">
              <div className="demo-landing__feature-icon demo-landing__feature-icon--contact">
                <BallDetectionIcon size={20} color="white" />
              </div>
              <h4 className="demo-landing__feature-title">Contact Markers</h4>
              <p className="demo-landing__feature-description">
                Jump to key moments and review timing with timestamps.
              </p>
            </div>

            <div className="demo-landing__feature-card">
              <div className="demo-landing__feature-icon demo-landing__feature-icon--metrics">
                <AnalyticsIcon size={20} color="white" />
              </div>
              <h4 className="demo-landing__feature-title">Performance Metrics</h4>
              <p className="demo-landing__feature-description">
                See angles and metrics computed from existing contacts.
              </p>
            </div>

            <div className="demo-landing__feature-card">
              <div className="demo-landing__feature-icon demo-landing__feature-icon--video">
                <VideoIcon size={20} color="white" />
              </div>
              <h4 className="demo-landing__feature-title">Interactive Video</h4>
              <p className="demo-landing__feature-description">
                Frame-by-frame controls and fast navigation between contacts.
              </p>
            </div>
          </div>
        </div>


      </div>
    </div>
  );
};

export default DemoLanding;
