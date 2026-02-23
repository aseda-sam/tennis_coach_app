import React from 'react';
import { createPortal } from 'react-dom';
import { ServeWindowCreate } from '../types/serveWindow';
import { formatTime } from '../utils/validation';
import { useServeWindowForm } from '../hooks/useServeWindowForm';
import AdvancedServeForm from './AdvancedServeForm';
import CompactServeForm from './CompactServeForm';
import './AddContactButton.css'; // Reuse styles

interface AddServeWindowButtonProps {
  currentTime: number;
  videoId: number;
  videoDuration: number;
  fps?: number;
  onAddServeWindow: (serveWindow: ServeWindowCreate) => Promise<void>;
  isVisible: boolean;
  isReadOnly?: boolean;
  placement?: 'overlay' | 'scrubber';
  openRequestId?: number;
  openRange?: { start: number; end: number };
  onFormOpen?: (timestamp: number) => void;
  onFormClose?: () => void;
  onSeek?: (time: number) => void;
}

const AddServeWindowButton: React.FC<AddServeWindowButtonProps> = ({
  currentTime,
  videoId,
  videoDuration,
  fps,
  onAddServeWindow,
  isVisible,
  isReadOnly = false,
  placement = 'overlay',
  openRequestId,
  openRange,
  onFormOpen,
  onFormClose,
  onSeek,
}) => {
  const {
    isOpen,
    isLoading,
    validationError,
    lockedTimestamp,
    showAdvanced,
    setShowAdvanced,
    formData,
    setFormData,
    lockedFrameNumber,
    handleOpen,
    handleClose,
    handleAddServeWindow,
  } = useServeWindowForm({
    videoId,
    currentTime,
    videoDuration,
    fps,
    isReadOnly,
    onAddServeWindow,
    onFormOpen,
    onFormClose,
    onSeek,
    openRequestId,
    openRange,
  });

  const formPosition =
    placement === 'scrubber' && lockedTimestamp !== null && videoDuration > 0
      ? {
          left: `${(lockedTimestamp / videoDuration) * 100}%`,
        }
      : undefined;

  if (!isVisible) return null;

  const supportsCompact = placement === 'overlay';
  const isCompact = supportsCompact && !showAdvanced;
  const isAdvancedPanel = supportsCompact && showAdvanced;
  const containerClassName = `add-contact-container ${
    placement === 'scrubber' ? 'add-contact-container--scrubber' : ''
  } ${placement === 'overlay' ? 'add-contact-container--overlay' : ''} ${
    isOpen ? 'is-open' : ''
  }`.trim();
  const buttonClassName = `add-contact-btn ${
    placement === 'scrubber' ? 'add-contact-btn--scrubber' : ''
  } ${isReadOnly ? 'add-contact-btn--readonly' : ''}`.trim();
  const isOverlayPlacement = placement === 'overlay';
  const formClassName = `add-contact-form ${
    placement === 'scrubber' ? 'add-contact-form--scrubber' : ''
  } ${isCompact ? 'add-contact-form--compact' : ''} ${
    isAdvancedPanel ? 'add-contact-form--advanced' : ''
  }`.trim();

  const formContent = (
    <div
      className={formClassName}
      onClick={(e) => e.stopPropagation()}
      style={isOverlayPlacement ? undefined : formPosition}
    >
      {isCompact ? (
        <CompactServeForm
          formData={formData}
          setFormData={setFormData}
          validationError={validationError}
          isLoading={isLoading}
          videoDuration={videoDuration}
          currentTime={currentTime}
          onClose={handleClose}
          onSubmit={handleAddServeWindow}
          onShowAdvanced={() => setShowAdvanced(true)}
          onSeek={onSeek}
        />
      ) : (
        <AdvancedServeForm
          formData={formData}
          setFormData={setFormData}
          validationError={validationError}
          isLoading={isLoading}
          videoDuration={videoDuration}
          currentTime={currentTime}
          lockedFrameNumber={lockedFrameNumber}
          supportsCompact={supportsCompact}
          onClose={handleClose}
          onSubmit={handleAddServeWindow}
          onShowCompact={() => setShowAdvanced(false)}
          onSeek={onSeek}
        />
      )}
    </div>
  );

  return (
    <div className={containerClassName}>
      {!isOpen
        ? placement !== 'scrubber' && (
            <button
              className={buttonClassName}
              onClick={(e) => {
                e.stopPropagation();
                handleOpen();
              }}
              title={
                isReadOnly
                  ? 'Demo mode: manual serve window creation is disabled'
                  : `Tag serve near ${formatTime(currentTime)}`
              }
              aria-disabled={isReadOnly}
            >
              <span className="add-icon">+</span>
              <span className="add-text">Tag Serve</span>
            </button>
          )
        : createPortal(
            <div className="serve-window-modal-backdrop" onClick={handleClose}>
              <div
                className="serve-window-modal-container"
                onClick={(e) => e.stopPropagation()}
              >
                {formContent}
              </div>
            </div>,
            document.body
          )}
    </div>
  );
};

export default AddServeWindowButton;
