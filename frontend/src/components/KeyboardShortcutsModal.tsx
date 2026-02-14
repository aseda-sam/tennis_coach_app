import React, { useEffect, useCallback } from 'react';
import './KeyboardShortcutsModal.css';

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
  isDemo?: boolean;
  naturalScroll?: boolean;
  onNaturalScrollChange?: (value: boolean) => void;
}

const KeyboardShortcutsModal: React.FC<KeyboardShortcutsModalProps> = ({
  isOpen,
  onClose,
  isDemo = false,
  naturalScroll = false,
  onNaturalScrollChange,
}) => {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    },
    [onClose]
  );

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  return (
    <div className="keyboard-modal-overlay" onClick={onClose}>
      <div className="keyboard-modal" onClick={(e) => e.stopPropagation()}>
        <div className="keyboard-modal__header">
          <h2>Keyboard Shortcuts</h2>
          <button className="keyboard-modal__close" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="keyboard-modal__content">
          <div className="keyboard-modal__section">
            <h3>Playback</h3>
            <div className="keyboard-modal__shortcuts">
              <div className="keyboard-modal__shortcut">
                <kbd>Space</kbd>
                <span>Play / Pause</span>
              </div>
              <div className="keyboard-modal__shortcut">
                <kbd>←</kbd> <kbd>→</kbd>
                <span>Previous / Next frame</span>
              </div>
              <div className="keyboard-modal__shortcut">
                <kbd>[</kbd> <kbd>]</kbd>
                <span>Previous / Next serve</span>
              </div>
              <div className="keyboard-modal__shortcut">
                <kbd>Scroll</kbd>
                <span>Navigate frames</span>
                {onNaturalScrollChange && (
                  <label className="keyboard-modal__toggle">
                    <input
                      type="checkbox"
                      checked={naturalScroll}
                      onChange={(e) => onNaturalScrollChange(e.target.checked)}
                    />
                    <span>Natural</span>
                  </label>
                )}
              </div>
            </div>
          </div>

          <div className="keyboard-modal__section">
            <h3>
              Tagging{' '}
              {isDemo && (
                <span className="keyboard-modal__demo-badge">
                  Demo: Disabled
                </span>
              )}
            </h3>
            <div
              className={`keyboard-modal__shortcuts ${isDemo ? 'keyboard-modal__shortcuts--disabled' : ''}`}
            >
              <div className="keyboard-modal__shortcut">
                <kbd>S</kbd>
                <span>Mark serve start point</span>
              </div>
              <div className="keyboard-modal__shortcut">
                <kbd>E</kbd>
                <span>Mark serve end point</span>
              </div>
              <div className="keyboard-modal__shortcut">
                <kbd>C</kbd>
                <span>Mark contact point</span>
              </div>
            </div>
          </div>

          <div className="keyboard-modal__section">
            <h3>General</h3>
            <div className="keyboard-modal__shortcuts">
              <div className="keyboard-modal__shortcut">
                <kbd>?</kbd>
                <span>Show this help</span>
              </div>
              <div className="keyboard-modal__shortcut">
                <kbd>Esc</kbd>
                <span>Close dialogs</span>
              </div>
            </div>
          </div>
        </div>

        <div className="keyboard-modal__footer">
          <span className="keyboard-modal__hint">
            Press <kbd>?</kbd> anytime to open this
          </span>
        </div>
      </div>
    </div>
  );
};

export default KeyboardShortcutsModal;
