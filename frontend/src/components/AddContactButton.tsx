import React, { useEffect, useState } from 'react';
import { BallContactCreate } from '../services/ballContactApi';
import './AddContactButton.css';

interface AddContactButtonProps {
  currentTime: number;
  videoId: number;
  onAddContact: (contact: BallContactCreate) => Promise<void>;
  isVisible: boolean;
}

const AddContactButton: React.FC<AddContactButtonProps> = ({
  currentTime,
  videoId,
  onAddContact,
  isVisible,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState<BallContactCreate>({
    video_id: videoId,
    video_timestamp: currentTime,
    contact_hand: 'right',
    stroke_type: 'ground_stroke',
    stroke_subtype: '',
    detection_source: 'manual',
  });

  // Update video_timestamp when currentTime changes
  useEffect(() => {
    setFormData((prev) => ({
      ...prev,
      video_timestamp: currentTime,
    }));
  }, [currentTime]);

  const handleAddContact = async () => {
    setIsLoading(true);
    try {
      await onAddContact(formData);
      setIsOpen(false);
      setFormData({
        video_id: videoId,
        video_timestamp: currentTime,
        contact_hand: 'right',
        stroke_type: 'ground_stroke',
        stroke_subtype: '',
        detection_source: 'manual',
      });
    } catch (error) {
      console.error('Failed to add contact:', error);
      alert('Failed to add contact. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!isVisible) return null;

  return (
    <div className="add-contact-container">
      {!isOpen ? (
        <button
          className="add-contact-btn"
          onClick={(e) => {
            e.stopPropagation();
            setIsOpen(true);
          }}
          title={`Add ball contact at ${formatTime(currentTime)}`}
        >
          <span className="add-icon">+</span>
          <span className="add-text">Add Contact</span>
        </button>
      ) : (
        <div className="add-contact-form" onClick={(e) => e.stopPropagation()}>
          <div className="form-header">
            <span className="timestamp-display">{formatTime(currentTime)}</span>
            <button
              className="close-form-btn"
              onClick={(e) => {
                e.stopPropagation();
                setIsOpen(false);
              }}
            >
              ×
            </button>
          </div>

          <div className="form-fields">
            <div className="form-group">
              <label>Contact Hand:</label>
              <select
                value={formData.contact_hand}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    contact_hand: e.target.value as 'left' | 'right',
                  })
                }
              >
                <option value="right">Right</option>
                <option value="left">Left</option>
              </select>
            </div>

            <div className="form-group">
              <label>Stroke Type:</label>
              <select
                value={formData.stroke_type}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    stroke_type: e.target.value as any,
                  })
                }
              >
                <option value="ground_stroke">Ground Stroke</option>
                <option value="serve">Serve</option>
                <option value="volley">Volley</option>
                <option value="overhead">Overhead</option>
              </select>
            </div>

            <div className="form-group">
              <label>Stroke Subtype:</label>
              <input
                type="text"
                value={formData.stroke_subtype}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    stroke_subtype: e.target.value,
                  })
                }
                placeholder="e.g., forehand, backhand"
              />
            </div>
          </div>

          <div className="form-actions">
            <button
              className="btn btn-secondary"
              onClick={(e) => {
                e.stopPropagation();
                setIsOpen(false);
              }}
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              className="btn btn-primary"
              onClick={(e) => {
                e.stopPropagation();
                handleAddContact();
              }}
              disabled={isLoading}
            >
              {isLoading ? 'Adding...' : 'Add Contact'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default AddContactButton;
