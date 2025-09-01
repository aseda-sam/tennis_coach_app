import React, { useState } from 'react';
import { BallContact, BallContactUpdate } from '../services/ballContactApi';
import './BallContactModal.css';

interface BallContactModalProps {
  contact: BallContact | null;
  isOpen: boolean;
  onClose: () => void;
  onUpdate: (contactId: number, updates: BallContactUpdate) => Promise<void>;
  onDelete: (contactId: number) => Promise<void>;
}

const BallContactModal: React.FC<BallContactModalProps> = ({
  contact,
  isOpen,
  onClose,
  onUpdate,
  onDelete,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState<BallContactUpdate>({
    video_timestamp: contact?.video_timestamp || 0,
    contact_hand: contact?.contact_hand || 'right',
    stroke_type: contact?.stroke_type || 'ground_stroke',
    stroke_subtype: contact?.stroke_subtype || '',
  });

  if (!isOpen || !contact) return null;

  const handleEdit = () => {
    setIsEditing(true);
    setFormData({
      video_timestamp: contact.video_timestamp,
      contact_hand: contact.contact_hand,
      stroke_type: contact.stroke_type || 'ground_stroke',
      stroke_subtype: contact.stroke_subtype || '',
    });
  };

  const handleSave = async () => {
    setIsLoading(true);
    try {
      await onUpdate(contact.id, formData);
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to update contact:', error);
      alert('Failed to update contact. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this ball contact?')) {
      return;
    }

    setIsLoading(true);
    try {
      await onDelete(contact.id);
      onClose();
    } catch (error) {
      console.error('Failed to delete contact:', error);
      alert('Failed to delete contact. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="ball-contact-modal-overlay" onClick={onClose}>
      <div className="ball-contact-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Ball Contact Details</h3>
          <button className="close-btn" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="modal-content">
          {isEditing ? (
            <div className="edit-form">
              <div className="form-group">
                <label>Timestamp (seconds):</label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.video_timestamp}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      video_timestamp: parseFloat(e.target.value) || 0,
                    })
                  }
                />
              </div>

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
                  value={formData.stroke_subtype || ''}
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
          ) : (
            <div className="contact-details">
              <div className="detail-row">
                <span className="detail-label">Timestamp:</span>
                <span className="detail-value">{formatTime(contact.video_timestamp)}</span>
              </div>

              <div className="detail-row">
                <span className="detail-label">Contact Hand:</span>
                <span className="detail-value capitalize">{contact.contact_hand}</span>
              </div>

              <div className="detail-row">
                <span className="detail-label">Stroke Type:</span>
                <span className="detail-value capitalize">
                  {contact.stroke_type?.replace('_', ' ') || 'Unknown'}
                </span>
              </div>

              {contact.stroke_subtype && (
                <div className="detail-row">
                  <span className="detail-label">Stroke Subtype:</span>
                  <span className="detail-value">{contact.stroke_subtype}</span>
                </div>
              )}

              <div className="detail-row">
                <span className="detail-label">Detection Source:</span>
                <span className={`detail-value badge ${contact.detection_source}`}>
                  {contact.detection_source}
                </span>
              </div>

              <div className="detail-row">
                <span className="detail-label">Created:</span>
                <span className="detail-value">
                  {new Date(contact.created_at).toLocaleString()}
                </span>
              </div>
            </div>
          )}
        </div>

        <div className="modal-actions">
          {isEditing ? (
            <>
              <button
                className="btn btn-secondary"
                onClick={() => setIsEditing(false)}
                disabled={isLoading}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary"
                onClick={handleSave}
                disabled={isLoading}
              >
                {isLoading ? 'Saving...' : 'Save Changes'}
              </button>
            </>
          ) : (
            <>
              <button
                className="btn btn-danger"
                onClick={handleDelete}
                disabled={isLoading}
              >
                {isLoading ? 'Deleting...' : 'Delete Contact'}
              </button>
              <button
                className="btn btn-primary"
                onClick={handleEdit}
                disabled={isLoading}
              >
                Edit Contact
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default BallContactModal;
