import { useCallback, useEffect, useRef, useState } from 'react';
import { ServeWindowCreate } from '../types/serveWindow';
import {
  validateContactTimestamp,
  validateManualTimestamp,
} from '../utils/validation';

interface UseServeWindowFormOptions {
  videoId: number;
  currentTime: number;
  videoDuration: number;
  fps?: number;
  isReadOnly: boolean;
  onAddServeWindow: (serveWindow: ServeWindowCreate) => Promise<void>;
  onFormOpen?: (timestamp: number) => void;
  onFormClose?: () => void;
  onSeek?: (time: number) => void;
  openRequestId?: number;
  openRange?: { start: number; end: number };
}

export function useServeWindowForm({
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
}: UseServeWindowFormOptions) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [lockedTimestamp, setLockedTimestamp] = useState<number | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [formData, setFormData] = useState<ServeWindowCreate>({
    video_id: videoId,
    start_timestamp: currentTime,
    end_timestamp: currentTime + 3, // Default 3 second window
    contact_timestamp: null,
    court_side: null,
    serve_number: null,
    serve_subtype: null,
    in_out: null,
  });

  const lastOpenRequestId = useRef<number | null>(null);

  const openAtTimestamp = useCallback(
    (timestamp: number) => {
      if (isReadOnly) {
        alert('Manual serve creation is disabled in Demo Mode!');
        return;
      }
      setLockedTimestamp(timestamp);
      setShowAdvanced(false);
      setFormData((prev) => ({
        ...prev,
        start_timestamp: timestamp,
        end_timestamp: Math.min(timestamp + 3, videoDuration || timestamp + 3),
        contact_timestamp: null,
      }));
      setIsOpen(true);
      onFormOpen?.(timestamp);
    },
    [isReadOnly, onFormOpen, videoDuration]
  );

  const openAtRange = useCallback(
    (rangeStart: number, rangeEnd: number) => {
      if (isReadOnly) {
        alert('Manual serve creation is disabled in Demo Mode!');
        return;
      }

      const start = Math.max(0, Math.min(rangeStart, rangeEnd));
      const end = Math.min(
        videoDuration || rangeEnd,
        Math.max(rangeStart, rangeEnd)
      );
      const clampedEnd = Math.max(start + 0.1, end);

      setLockedTimestamp(start);
      setShowAdvanced(false);
      setFormData((prev) => ({
        ...prev,
        start_timestamp: start,
        end_timestamp: clampedEnd,
        contact_timestamp: null,
      }));
      setIsOpen(true);
      onFormOpen?.(start);
    },
    [isReadOnly, onFormOpen, videoDuration]
  );

  const handleOpen = useCallback(() => {
    openAtTimestamp(currentTime);
  }, [openAtTimestamp, currentTime]);

  const handleClose = useCallback(() => {
    setIsOpen(false);
    setLockedTimestamp(null);
    setValidationError(null);
    setShowAdvanced(false);
    onFormClose?.();
  }, [onFormClose]);

  useEffect(() => {
    if (!isOpen && lockedTimestamp === null) {
      setFormData((prev) => ({
        ...prev,
        start_timestamp: currentTime,
        end_timestamp: Math.min(
          currentTime + 3,
          videoDuration || currentTime + 3
        ),
        contact_timestamp: null,
      }));
      setValidationError(null);
    }
  }, [currentTime, isOpen, lockedTimestamp, videoDuration]);

  useEffect(() => {
    if (!openRequestId) return;
    if (openRequestId === lastOpenRequestId.current) return;

    lastOpenRequestId.current = openRequestId;

    if (openRange) {
      openAtRange(openRange.start, openRange.end);
    }
  }, [openRequestId, openRange, openAtRange]);

  // Keyboard shortcut for contact timestamp (C key)
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      // Don't handle if typing in an input field
      if (
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement ||
        event.target instanceof HTMLSelectElement
      ) {
        return;
      }

      if (event.key === 'c' || event.key === 'C') {
        event.preventDefault();
        // Set contact timestamp to current time, clamped to serve window range
        setFormData((prev) => {
          const clampedTime = Math.max(
            prev.start_timestamp,
            Math.min(currentTime, prev.end_timestamp)
          );
          if (onSeek) onSeek(clampedTime);
          return {
            ...prev,
            contact_timestamp: clampedTime,
          };
        });
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [
    isOpen,
    formData.start_timestamp,
    formData.end_timestamp,
    currentTime,
    onSeek,
  ]);

  useEffect(() => {
    if (videoDuration > 0) {
      const startValidation = validateManualTimestamp(
        formData.start_timestamp,
        videoDuration
      );
      const endValidation = validateManualTimestamp(
        formData.end_timestamp,
        videoDuration
      );
      if (!startValidation.isValid) {
        setValidationError(startValidation.error || null);
      } else if (!endValidation.isValid) {
        setValidationError(endValidation.error || null);
      } else if (formData.start_timestamp >= formData.end_timestamp) {
        setValidationError('Start time must be before end time');
      } else {
        const contactValidation = validateContactTimestamp(
          formData.contact_timestamp ?? null,
          formData.start_timestamp,
          formData.end_timestamp,
          videoDuration
        );
        if (!contactValidation.isValid) {
          setValidationError(contactValidation.error || null);
        } else {
          setValidationError(null);
        }
      }
    }
  }, [formData, videoDuration]);

  const handleAddServeWindow = useCallback(async () => {
    if (videoDuration > 0) {
      const startValidation = validateManualTimestamp(
        formData.start_timestamp,
        videoDuration
      );
      const endValidation = validateManualTimestamp(
        formData.end_timestamp,
        videoDuration
      );
      if (!startValidation.isValid || !endValidation.isValid) {
        setValidationError(
          startValidation.error || endValidation.error || 'Invalid timestamp'
        );
        return;
      }

      if (formData.start_timestamp >= formData.end_timestamp) {
        setValidationError('Start time must be before end time');
        return;
      }

      const contactValidation = validateContactTimestamp(
        formData.contact_timestamp ?? null,
        formData.start_timestamp,
        formData.end_timestamp,
        videoDuration
      );
      if (!contactValidation.isValid) {
        setValidationError(contactValidation.error || 'Invalid timestamp');
        return;
      }
    }

    setIsLoading(true);
    try {
      await onAddServeWindow(formData);
      handleClose();
      setFormData({
        video_id: videoId,
        start_timestamp: currentTime,
        end_timestamp: Math.min(
          currentTime + 3,
          videoDuration || currentTime + 3
        ),
        contact_timestamp: null,
        court_side: null,
        serve_number: null,
        serve_subtype: null,
        in_out: null,
      });
    } catch (error) {
      alert('Failed to add serve. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [
    formData,
    videoDuration,
    onAddServeWindow,
    handleClose,
    videoId,
    currentTime,
  ]);

  const lockedFrameNumber =
    lockedTimestamp !== null && fps && fps > 0
      ? Math.floor(lockedTimestamp * fps)
      : null;

  return {
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
  };
}
