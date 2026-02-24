import React, { useCallback, useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { getApiErrorMessage } from '../utils/apiError';
import { usePlayerProfile } from '../hooks/usePlayerProfile';
import { useUpdateVideoMetadata } from '../hooks/useVideos';
import { VideoMetadata } from '../types/video';
import { X } from 'lucide-react';
import DateTimePicker from './DateTimePicker';

function toDatetimeLocalValue(iso: string): string {
  return iso.slice(0, 16);
}

interface VideoEditModalProps {
  video: VideoMetadata;
  onClose: () => void;
}

const VideoEditModal: React.FC<VideoEditModalProps> = ({ video, onClose }) => {
  const queryClient = useQueryClient();
  const { data: playerProfile } = usePlayerProfile();
  const updateMetadataMutation = useUpdateVideoMetadata();

  const resolvePlayerTag = useCallback(
    (v: VideoMetadata): 'you' | 'someone_else' => {
      if (!v.primary_player_id || !playerProfile?.id) {
        return 'you';
      }
      return v.primary_player_id === playerProfile.id ? 'you' : 'someone_else';
    },
    [playerProfile?.id]
  );

  const [editTitle, setEditTitle] = useState(video.title || '');
  const [editNotes, setEditNotes] = useState(video.notes || '');
  const [editRecordedAt, setEditRecordedAt] = useState(
    video.recorded_at ? toDatetimeLocalValue(video.recorded_at) : ''
  );
  const [editSessionType, setEditSessionType] = useState(
    video.session_type || ''
  );
  const [editCameraAngle, setEditCameraAngle] = useState(
    video.camera_angle || ''
  );
  const [editPlayerTag, setEditPlayerTag] = useState<'you' | 'someone_else'>(
    resolvePlayerTag(video)
  );
  const [editError, setEditError] = useState<string | null>(null);

  // Reset form state when the video prop changes
  useEffect(() => {
    setEditTitle(video.title || '');
    setEditNotes(video.notes || '');
    setEditRecordedAt(
      video.recorded_at ? toDatetimeLocalValue(video.recorded_at) : ''
    );
    setEditSessionType(video.session_type || '');
    setEditCameraAngle(video.camera_angle || '');
    setEditPlayerTag(resolvePlayerTag(video));
    setEditError(null);
  }, [video, resolvePlayerTag]);

  const handleEditSave = useCallback(async () => {
    setEditError(null);

    try {
      await updateMetadataMutation.mutateAsync({
        videoId: video.id,
        metadata: {
          title: editTitle || undefined,
          notes: editNotes || undefined,
          recorded_at: editRecordedAt
            ? new Date(editRecordedAt).toISOString()
            : undefined,
          session_type: editSessionType || undefined,
          camera_angle: editCameraAngle || undefined,
          player_tag: editPlayerTag,
        },
      });

      queryClient.invalidateQueries({ queryKey: ['videos'] });
      onClose();
    } catch (err: unknown) {
      setEditError(
        getApiErrorMessage(err, 'Failed to update video. Please try again.')
      );
    }
  }, [
    editTitle,
    editNotes,
    editRecordedAt,
    editCameraAngle,
    editPlayerTag,
    editSessionType,
    video.id,
    queryClient,
    updateMetadataMutation,
    onClose,
  ]);

  return (
    <div className="upload-modal-overlay" onClick={onClose}>
      <div className="upload-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Edit Video Details</h2>
          <button
            className="close-btn"
            onClick={onClose}
            aria-label="Close"
            type="button"
          >
            <X size={18} />
          </button>
        </div>
        <div className="modal-content">
          <div className="edit-video-form">
            <div className="edit-video-field">
              <label>Title</label>
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                placeholder={video.filename}
                maxLength={200}
                disabled={updateMetadataMutation.isPending}
              />
            </div>

            <div className="edit-video-field">
              <label>Notes</label>
              <textarea
                value={editNotes}
                onChange={(e) => setEditNotes(e.target.value)}
                rows={3}
                placeholder="Any notes about this session..."
                disabled={updateMetadataMutation.isPending}
              />
            </div>

            <div className="edit-video-field">
              <label>Recording Date &amp; Time</label>
              <DateTimePicker
                value={editRecordedAt}
                onChange={setEditRecordedAt}
                disabled={updateMetadataMutation.isPending}
              />
              <p className="edit-video-note edit-video-note--compact">
                Used for progress trends. Correct it if the timestamp is wrong.
              </p>
            </div>

            <div className="edit-video-two-col">
              <div className="edit-video-field">
                <label>
                  Session Type{' '}
                  <span className="required-asterisk" aria-label="required">
                    *
                  </span>
                </label>
                <select
                  value={editSessionType}
                  onChange={(e) => setEditSessionType(e.target.value)}
                  disabled={updateMetadataMutation.isPending}
                >
                  <option value="">Select session type</option>
                  <option value="serve_practice">Serve Practice</option>
                  <option value="match">Match</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div className="edit-video-field">
                <label>Camera Angle</label>
                <select
                  value={editCameraAngle}
                  onChange={(e) => setEditCameraAngle(e.target.value)}
                  disabled={updateMetadataMutation.isPending}
                >
                  <option value="">Select camera angle</option>
                  <option value="behind">Behind</option>
                  <option value="profile">Profile</option>
                  <option value="unknown">Unknown</option>
                </select>
              </div>
            </div>

            <div className="edit-video-section">
              <div className="edit-video-section-header">
                <div className="edit-video-section-title">Who Is Serving?</div>
                <p className="edit-video-section-subtitle">
                  New serves detected in this video will be saved under this
                  player.
                </p>
              </div>

              <div className="edit-video-radio-group edit-video-radio-group--horizontal">
                <label>
                  <input
                    type="radio"
                    name="editPlayerTag"
                    value="you"
                    checked={editPlayerTag === 'you'}
                    onChange={() => setEditPlayerTag('you')}
                    disabled={updateMetadataMutation.isPending}
                  />
                  <span>{playerProfile?.name || 'Your Profile'}</span>
                </label>
                <label>
                  <input
                    type="radio"
                    name="editPlayerTag"
                    value="someone_else"
                    checked={editPlayerTag === 'someone_else'}
                    onChange={() => setEditPlayerTag('someone_else')}
                    disabled={updateMetadataMutation.isPending}
                  />
                  <span>Someone Else</span>
                </label>
              </div>
            </div>

            {editError && <div className="edit-video-error">{editError}</div>}
          </div>
        </div>
        <div className="edit-video-actions">
          <button
            type="button"
            className="edit-video-cancel"
            onClick={onClose}
            disabled={updateMetadataMutation.isPending}
          >
            Cancel
          </button>
          <button
            type="button"
            className="edit-video-save"
            onClick={handleEditSave}
            disabled={!editSessionType || updateMetadataMutation.isPending}
          >
            {updateMetadataMutation.isPending ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default VideoEditModal;
