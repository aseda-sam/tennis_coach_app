import React from 'react';
import './KeyboardShortcutsBanner.css';

interface KeyboardShortcutsBannerProps {
  isDemo?: boolean;
  naturalScroll?: boolean;
  onNaturalScrollChange?: (value: boolean) => void;
}

const KeyboardShortcutsBanner: React.FC<KeyboardShortcutsBannerProps> = ({
  isDemo = false,
  naturalScroll = false,
  onNaturalScrollChange,
}) => {
  const rangeStartTitle = isDemo
    ? 'Range tagging is disabled in Demo Mode!'
    : 'Mark the START point for a serve';
  const rangeEndTitle = isDemo
    ? 'Range tagging is disabled in Demo Mode!'
    : 'Mark the END point for a serve';

  return (
    <div className="keyboard-shortcuts">
      <div className="keyboard-shortcuts__content">
        <div className="keyboard-shortcuts__header">
          <span className="keyboard-shortcuts__icon">⌨️</span>
          <h4 className="keyboard-shortcuts__title">Controls</h4>
        </div>
        <div className="keyboard-shortcuts__list">
          <div className="keyboard-shortcuts__item">
            <kbd className="keyboard-shortcuts__kbd">Space</kbd>
            <span>Play/Pause</span>
          </div>
          <div className="keyboard-shortcuts__item">
            <kbd className="keyboard-shortcuts__kbd">← →</kbd>
            <span>Frame by frame</span>
          </div>
          <div className="keyboard-shortcuts__item">
            <kbd className="keyboard-shortcuts__kbd">[ ]</kbd>
            <span>Prev/Next serve</span>
          </div>
          <div
            className={`keyboard-shortcuts__item ${
              isDemo ? 'keyboard-shortcuts__item--disabled' : ''
            }`.trim()}
            title={rangeStartTitle}
            aria-disabled={isDemo}
          >
            <kbd className="keyboard-shortcuts__kbd">S</kbd>
            <span>Start</span>
          </div>
          <div
            className={`keyboard-shortcuts__item ${
              isDemo ? 'keyboard-shortcuts__item--disabled' : ''
            }`.trim()}
            title={rangeEndTitle}
            aria-disabled={isDemo}
          >
            <kbd className="keyboard-shortcuts__kbd">E</kbd>
            <span>End</span>
          </div>
          <div
            className={`keyboard-shortcuts__item ${
              isDemo ? 'keyboard-shortcuts__item--disabled' : ''
            }`.trim()}
            title={
              isDemo
                ? 'Demo mode: contact marking is disabled'
                : 'Mark contact point (when creating serve)'
            }
            aria-disabled={isDemo}
          >
            <kbd className="keyboard-shortcuts__kbd">C</kbd>
            <span>Contact</span>
          </div>
          <div className="keyboard-shortcuts__item keyboard-shortcuts__item--scroll">
            <kbd className="keyboard-shortcuts__kbd">⟳</kbd>
            <span>Scroll</span>
            {onNaturalScrollChange && (
              <label className="keyboard-shortcuts__natural-toggle">
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
    </div>
  );
};

export default KeyboardShortcutsBanner;
