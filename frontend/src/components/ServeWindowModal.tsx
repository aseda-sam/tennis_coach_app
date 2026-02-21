import React, { useEffect, useState } from 'react';
import { ServeWindow, ServeWindowUpdate } from '../types/serveWindow';
import {
  validateContactTimestamp,
  validateTimestamp,
} from '../utils/validation';
import ServeWindowOverlay from './ServeWindowOverlay';
import { ServeWindowFormData } from './ServeWindowPanel';
import ServeWindowPanel from './ServeWindowPanel';

interface ServeWindowModalProps {
  serveWindow: ServeWindow | null;
  isOpen: boolean;
  videoDuration: number;
  currentTime?: number;
  onClose: () => void;
  onUpdate: (
    serveWindowId: number,
    updates: ServeWindowUpdate
  ) => Promise<void>;
  onDelete: (serveWindowId: number) => Promise<void>;
  onSeek?: (time: number) => void;
  isDemo?: boolean;
  /** Use panel mode to show as side panel instead of blocking overlay */
  mode?: 'overlay' | 'panel';
}

const ServeWindowModal: React.FC<ServeWindowModalProps> = ({
  serveWindow,
  isOpen,
  videoDuration,
  currentTime = 0,
  onClose,
  onUpdate,
  onDelete,
  onSeek,
  isDemo = false,
  mode = 'overlay',
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [formData, setFormData] = useState<ServeWindowFormData>({
    start_timestamp: serveWindow?.start_timestamp ?? 0,
    end_timestamp: serveWindow?.end_timestamp ?? 0,
    contact_timestamp: serveWindow?.contact_timestamp ?? null,
    court_side: serveWindow?.court_side ?? null,
    serve_number: serveWindow?.serve_number ?? null,
    serve_subtype: serveWindow?.serve_subtype ?? null,
    in_out: serveWindow?.in_out ?? null,
  });

  useEffect(() => {
    if (serveWindow) {
      setFormData({
        start_timestamp: serveWindow.start_timestamp,
        end_timestamp: serveWindow.end_timestamp,
        contact_timestamp: serveWindow.contact_timestamp,
        court_side: serveWindow.court_side,
        serve_number: serveWindow.serve_number,
        serve_subtype: serveWindow.serve_subtype,
        in_out: serveWindow.in_out,
      });
    }
    setValidationError(null);
  }, [serveWindow]);

  useEffect(() => {
    if (
      isEditing &&
      videoDuration > 0 &&
      formData.start_timestamp !== undefined &&
      formData.start_timestamp !== null &&
      formData.end_timestamp !== undefined &&
      formData.end_timestamp !== null
    ) {
      const startVal = formData.start_timestamp;
      const endVal = formData.end_timestamp;
      const startValidation = validateTimestamp(startVal, videoDuration);
      const endValidation = validateTimestamp(endVal, videoDuration);
      if (!startValidation.isValid) {
        setValidationError(startValidation.error || null);
      } else if (!endValidation.isValid) {
        setValidationError(endValidation.error || null);
      } else if (startVal >= endVal) {
        setValidationError('Start time must be before end time');
      } else {
        const contactValidation = validateContactTimestamp(
          formData.contact_timestamp ?? null,
          startVal,
          endVal,
          videoDuration
        );
        if (!contactValidation.isValid) {
          setValidationError(contactValidation.error || null);
        } else {
          setValidationError(null);
        }
      }
    }
  }, [formData, videoDuration, isEditing]);

  if (!isOpen || !serveWindow) return null;

  const handleEdit = () => {
    setIsEditing(true);
    setFormData({
      start_timestamp: serveWindow.start_timestamp,
      end_timestamp: serveWindow.end_timestamp,
      contact_timestamp: serveWindow.contact_timestamp,
      court_side: serveWindow.court_side,
      serve_number: serveWindow.serve_number,
      serve_subtype: serveWindow.serve_subtype,
      in_out: serveWindow.in_out,
    });
    setValidationError(null);
  };

  const handleSave = async () => {
    if (
      videoDuration > 0 &&
      formData.start_timestamp !== undefined &&
      formData.start_timestamp !== null &&
      formData.end_timestamp !== undefined &&
      formData.end_timestamp !== null
    ) {
      const startVal = formData.start_timestamp;
      const endVal = formData.end_timestamp;
      const startValidation = validateTimestamp(startVal, videoDuration);
      const endValidation = validateTimestamp(endVal, videoDuration);
      if (!startValidation.isValid || !endValidation.isValid) {
        setValidationError(
          startValidation.error || endValidation.error || 'Invalid timestamp'
        );
        return;
      }

      if (startVal >= endVal) {
        setValidationError('Start time must be before end time');
        return;
      }

      const contactValidation = validateContactTimestamp(
        formData.contact_timestamp ?? null,
        startVal,
        endVal,
        videoDuration
      );
      if (!contactValidation.isValid) {
        setValidationError(contactValidation.error || 'Invalid timestamp');
        return;
      }
    }

    setIsLoading(true);
    try {
      await onUpdate(serveWindow.id, formData);
      setIsEditing(false);
      setValidationError(null);
    } catch (error) {
      alert('Failed to update serve. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this serve?')) {
      return;
    }

    setIsLoading(true);
    try {
      await onDelete(serveWindow.id);
      onClose();
    } catch (error) {
      alert('Failed to delete serve window. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setValidationError(null);
  };

  const childProps = {
    serveWindow,
    isEditing,
    isLoading,
    validationError,
    formData,
    setFormData,
    videoDuration,
    currentTime,
    isDemo,
    onClose,
    onSeek,
    onEdit: handleEdit,
    onSave: handleSave,
    onDelete: handleDelete,
    onCancelEdit: handleCancelEdit,
  };

  if (mode === 'panel') {
    return <ServeWindowPanel {...childProps} />;
  }

  return <ServeWindowOverlay {...childProps} />;
};

export default ServeWindowModal;
