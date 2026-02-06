import React from 'react';
import { VideoIcon } from './Icons';
import './FloatingHelpButton.css';

interface FloatingHelpButtonProps {
  onClick: () => void;
}

const FloatingHelpButton: React.FC<FloatingHelpButtonProps> = ({ onClick }) => {
  return (
    <button
      className="floating-help-button"
      onClick={onClick}
      aria-label="Watch tutorial video"
      type="button"
      title="Watch How It Works"
    >
      <div className="floating-help-button__icon">
        <VideoIcon size={20} color="white" />
      </div>
      <span className="floating-help-button__text">Help</span>
    </button>
  );
};

export default FloatingHelpButton;
