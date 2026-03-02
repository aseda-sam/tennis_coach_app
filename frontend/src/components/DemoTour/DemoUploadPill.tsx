import React, { useState } from 'react';
import { Upload, X } from 'lucide-react';
import './DemoUploadPill.css';

interface DemoUploadPillProps {
  onUpload: () => void;
}

const DemoUploadPill: React.FC<DemoUploadPillProps> = ({ onUpload }) => {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <div className="demo-upload-pill">
      <button
        className="demo-upload-pill__action"
        onClick={onUpload}
        type="button"
      >
        <Upload size={14} />
        Upload Your Serve
      </button>
      <button
        className="demo-upload-pill__dismiss"
        onClick={() => setDismissed(true)}
        type="button"
        aria-label="Dismiss"
      >
        <X size={12} />
      </button>
    </div>
  );
};

export default DemoUploadPill;
