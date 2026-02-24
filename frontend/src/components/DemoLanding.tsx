import {
  Activity,
  ChartNoAxesColumn,
  Github,
  Play,
  ScanLine,
  StepForward,
  Upload,
  Video,
} from 'lucide-react';
import React from 'react';
import './DemoLanding.css';

import { User } from '@supabase/supabase-js';

interface DemoLandingProps {
  onTryDemo: () => void;
  onUploadVideo: () => void;
  onWatchTutorial: () => void;
  user: User | null;
}

const DemoLanding: React.FC<DemoLandingProps> = ({
  onTryDemo,
  onUploadVideo,
  onWatchTutorial,
  user,
}) => {
  return (
    <div className="demo-landing">
      <div className="demo-landing__container">
        {/* Hero Section with Integrated Demo Card */}
        <div className="demo-landing__hero-section">
          <div className="demo-landing__hero-content">
            <h1 className="demo-landing__title">Your serve, frame by frame!</h1>
            <p className="demo-landing__origin">
              I filmed my tennis serve, watched it back, and couldn't stop
              building. Sessions, pose detection, now full biomechanics phases.{' '}
              <a
                href="https://github.com/aseda-sam/tennis_coach_app"
                className="demo-landing__origin-link"
                target="_blank"
                rel="noopener noreferrer"
              >
                It&apos;s open source.
                <Github size={13} className="demo-landing__origin-link-icon" />
              </a>
            </p>
            <button
              className="demo-landing__watch-tutorial"
              onClick={onWatchTutorial}
              type="button"
            >
              <Video size={16} color="var(--color-primary)" />
              Watch Intro Video
            </button>
          </div>

          {/* Cards Row */}
          <div className="demo-landing__cards-row">
            {/* Prominent Demo Card */}
            <div className="demo-landing__card demo-landing__card--gradient">
              <div className="demo-landing__card-inner">
                <div className="demo-landing__card-header">
                  <div className="demo-landing__card-icon demo-landing__card-icon--primary">
                    <Play size={20} color="white" />
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
                  key moments, review timing, and see what stands out.
                </p>
                <div className="demo-landing__card-actions">
                  <button
                    className="demo-landing__cta-primary"
                    onClick={onTryDemo}
                    type="button"
                  >
                    Try Demo
                  </button>
                </div>
              </div>
            </div>

            {/* Upload Card - Less Prominent */}
            <div className="demo-landing__card demo-landing__card--upload">
              <div className="demo-landing__card-inner">
                <div className="demo-landing__card-header">
                  <div className="demo-landing__card-icon demo-landing__card-icon--outline">
                    <Upload size={20} color="var(--color-primary)" />
                  </div>
                  <div className="demo-landing__card-title-wrap">
                    <div className="demo-landing__card-eyebrow">Your Turn</div>
                  </div>
                </div>
                <p className="demo-landing__card-body">
                  Upload a serve clip to get clear feedback on timing, posture,
                  and key moments.
                </p>
                <div className="demo-landing__card-actions">
                  <button
                    className="demo-landing__cta-secondary"
                    onClick={onUploadVideo}
                    type="button"
                  >
                    Upload Serve Video
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Features Section */}
        <div className="demo-landing__features-section">
          <div className="demo-landing__features-header">
            <h3 className="demo-landing__features-title">
              What You&apos;ll Get
            </h3>
          </div>

          <div className="demo-landing__feature-grid">
            <div className="demo-landing__feature-card">
              <div className="demo-landing__feature-icon">
                <Activity
                  size={20}
                  color="var(--color-amber)"
                  strokeWidth={2}
                />
              </div>
              <h4 className="demo-landing__feature-title">Body Tracking</h4>
              <p className="demo-landing__feature-description">
                See how your body aligns and moves through each phase of the
                serve.
              </p>
            </div>

            <div className="demo-landing__feature-card">
              <div className="demo-landing__feature-icon">
                <ScanLine
                  size={20}
                  color="var(--color-amber)"
                  strokeWidth={2}
                />
              </div>
              <h4 className="demo-landing__feature-title">Serve Breakdown</h4>
              <p className="demo-landing__feature-description">
                Jump to tagged key moments and focus on what matters.
              </p>
            </div>

            <div className="demo-landing__feature-card">
              <div className="demo-landing__feature-icon">
                <ChartNoAxesColumn
                  size={20}
                  color="var(--color-amber)"
                  strokeWidth={2}
                />
              </div>
              <h4 className="demo-landing__feature-title">
                Progress Over Time
              </h4>
              <p className="demo-landing__feature-description">
                Track how your technique changes across sessions and weeks.
              </p>
            </div>

            <div className="demo-landing__feature-card">
              <div className="demo-landing__feature-icon">
                <StepForward
                  size={20}
                  color="var(--color-amber)"
                  strokeWidth={2}
                />
              </div>
              <h4 className="demo-landing__feature-title">
                Frame-by-Frame Control
              </h4>
              <p className="demo-landing__feature-description">
                Step through every frame and zoom in for a closer look.
              </p>
            </div>
          </div>
        </div>

        {/* Footer strip */}
        <div className="demo-landing__footer-strip">
          <p className="demo-landing__feedback-note">
            This is a work in progress.{' '}
            <a
              href="https://github.com/aseda-sam/tennis_coach_app/issues"
              target="_blank"
              rel="noopener noreferrer"
            >
              Open an issue
            </a>{' '}
            if something&apos;s broken or you have ideas.
          </p>
          <a
            href="https://substack.com/@aseda"
            className="demo-landing__substack-link"
            target="_blank"
            rel="noopener noreferrer"
          >
            Follow the build on Substack →
          </a>
        </div>
      </div>
    </div>
  );
};

export default DemoLanding;
