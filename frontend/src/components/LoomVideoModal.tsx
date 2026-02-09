import React from 'react';
import { CloseIcon } from './Icons';
import './LoomVideoModal.css';

interface LoomVideoModalProps {
  isOpen: boolean;
  onClose: () => void;
  videoId: string;
}

const LoomVideoModal: React.FC<LoomVideoModalProps> = ({
  isOpen,
  onClose,
  videoId,
}) => {
  if (!isOpen) return null;

  const embedUrl = `https://www.loom.com/embed/${videoId}`;

  return (
    <div
      className="loom-video-modal-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="loom-video-modal-title"
    >
      <div
        className="loom-video-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="loom-video-modal__header">
          <h2 id="loom-video-modal-title" className="loom-video-modal__title">
            How to Use Serve Tennis Coach
          </h2>
          <button
            className="loom-video-modal__close"
            onClick={onClose}
            aria-label="Close video"
            type="button"
          >
            <CloseIcon size={20} />
          </button>
        </div>
        <div className="loom-video-modal__content">
          <div className="loom-video-modal__video-wrapper">
            <iframe
              src={embedUrl}
              frameBorder="0"
              allowFullScreen
              title="Serve Tennis Coach Intro Video"
              className="loom-video-modal__iframe"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoomVideoModal;
