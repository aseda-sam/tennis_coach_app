import React from 'react';
import {
  FrameExtractionIcon,
  BallDetectionIcon,
  PoseDetectionIcon,
  VideoAnnotationIcon,
  ProcessingIcon,
} from './Icons';
import './StageProgress.css';

interface StageProgressProps {
  currentStage: string;
  stageProgress: number;
  stageMessage: string;
  overallProgress: number;
  size?: 'small' | 'medium' | 'large';
}

const StageProgress: React.FC<StageProgressProps> = ({
  currentStage,
  stageProgress,
  stageMessage,
  overallProgress,
  size = 'medium',
}) => {
  const getStageIcon = () => {
    switch (currentStage) {
      case 'initializing':
        return <ProcessingIcon size={20} className="stage-icon" />;
      case 'frame_extraction':
        return <FrameExtractionIcon size={20} className="stage-icon" />;
      case 'ball_detection':
        return <BallDetectionIcon size={20} className="stage-icon" />;
      case 'pose_detection':
        return <PoseDetectionIcon size={20} className="stage-icon" />;
      case 'video_annotation':
        return <VideoAnnotationIcon size={20} className="stage-icon" />;
      case 'finalizing':
        return <ProcessingIcon size={20} className="stage-icon" />;
      default:
        return <ProcessingIcon size={20} className="stage-icon" />;
    }
  };

  const getStageName = () => {
    switch (currentStage) {
      case 'initializing':
        return 'Initializing';
      case 'frame_extraction':
        return 'Frame Extraction';
      case 'ball_detection':
        return 'Ball Detection';
      case 'pose_detection':
        return 'Pose Detection';
      case 'video_annotation':
        return 'Video Annotation';
      case 'finalizing':
        return 'Finalizing';
      default:
        return 'Processing';
    }
  };

  const getStageColor = () => {
    switch (currentStage) {
      case 'initializing':
      case 'finalizing':
        return 'processing';
      case 'frame_extraction':
        return 'info';
      case 'ball_detection':
        return 'primary';
      case 'pose_detection':
        return 'secondary';
      case 'video_annotation':
        return 'success';
      default:
        return 'processing';
    }
  };

  return (
    <div className={`stage-progress-container ${size}`}>
      <div className="stage-header">
        <div className="stage-icon-container">
          {getStageIcon()}
        </div>
        <div className="stage-info">
          <div className="stage-name">{getStageName()}</div>
          <div className="stage-message">{stageMessage}</div>
        </div>
        <div className="stage-percentage">
          <span className="overall-progress">{overallProgress}%</span>
          <span className="stage-progress">({stageProgress}%)</span>
        </div>
      </div>
      
      <div className="stage-progress-bars">
        <div className="overall-progress-bar">
          <div 
            className={`progress-fill ${getStageColor()}`}
            style={{ width: `${overallProgress}%` }}
            data-testid="overall-progress-fill"
          />
        </div>
        <div className="stage-progress-bar">
          <div 
            className={`progress-fill ${getStageColor()}`}
            style={{ width: `${stageProgress}%` }}
            data-testid="stage-progress-fill"
          />
        </div>
      </div>
    </div>
  );
};

export default StageProgress;
