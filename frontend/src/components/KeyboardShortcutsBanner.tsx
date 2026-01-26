import React from 'react';
import './KeyboardShortcutsBanner.css';

interface KeyboardShortcutsBannerProps {
  isDemo?: boolean;
}

const KeyboardShortcutsBanner: React.FC<KeyboardShortcutsBannerProps> = ({
  isDemo = false,
}) => {
  const rangeInTitle = isDemo
    ? 'Range tagging is disabled in Demo Mode!'
    : 'Mark the IN point for a serve attempt range';
  const rangeOutTitle = isDemo
    ? 'Range tagging is disabled in Demo Mode!'
    : 'Mark the OUT point for a serve attempt range';

  return (
    <div className="keyboard-shortcuts">
      <div className="keyboard-shortcuts__icon">⌨️</div>
      <div className="keyboard-shortcuts__content">
        <h4 className="keyboard-shortcuts__title">Keyboard Shortcuts</h4>
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
            <span>Previous/Next serve attempt</span>
          </div>
          <div
            className={`keyboard-shortcuts__item ${
              isDemo ? 'keyboard-shortcuts__item--disabled' : ''
            }`.trim()}
            title={rangeInTitle}
            aria-disabled={isDemo}
          >
            <kbd className="keyboard-shortcuts__kbd">I</kbd>
            <span>Mark IN point</span>
          </div>
          <div
            className={`keyboard-shortcuts__item ${
              isDemo ? 'keyboard-shortcuts__item--disabled' : ''
            }`.trim()}
            title={rangeOutTitle}
            aria-disabled={isDemo}
          >
            <kbd className="keyboard-shortcuts__kbd">O</kbd>
            <span>Mark OUT point</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default KeyboardShortcutsBanner;
