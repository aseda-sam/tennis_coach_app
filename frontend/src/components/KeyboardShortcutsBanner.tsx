import React from 'react';
import './KeyboardShortcutsBanner.css';

interface KeyboardShortcutsBannerProps {
  isDemo?: boolean;
}

const KeyboardShortcutsBanner: React.FC<KeyboardShortcutsBannerProps> = ({
  isDemo = false,
}) => {
  const manualLabel = 'Manually Add Contact';
  const manualTitle = isDemo
    ? 'Manual Contact Creation is disabled in Demo Mode!'
    : 'Manually add contact';

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
            <span>Previous/Next contact</span>
          </div>
          <div
            className={`keyboard-shortcuts__item ${
              isDemo ? 'keyboard-shortcuts__item--disabled' : ''
            }`.trim()}
            title={manualTitle}
            aria-disabled={isDemo}
          >
            <kbd className="keyboard-shortcuts__kbd">A</kbd>
            <span>{manualLabel}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default KeyboardShortcutsBanner;
