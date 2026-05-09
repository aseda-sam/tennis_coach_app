import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useMutation } from '@tanstack/react-query';
import { X, Scissors, Trash2 } from 'lucide-react';
import type { ServeWindow } from '../types/serveWindow';
import type { ServeWindowSplitResponse } from '../services/serveWindowApi';
import { serveWindowApi } from '../services/serveWindowApi';
import { getApiErrorMessage } from '../utils/apiError';

const MIN_WINDOW_DURATION = 0.5;

function formatTimestamp(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toFixed(2).padStart(5, '0')}`;
}

interface ServeWindowEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  serveWindow: ServeWindow;
  allWindows: ServeWindow[];
  videoDuration: number;
  videoUrl: string;
  onSaved: (updated: ServeWindow) => void;
  onSplit: (response: ServeWindowSplitResponse) => void;
  onDelete?: (serveWindowId: number) => Promise<void>;
}

const ServeWindowEditModal: React.FC<ServeWindowEditModalProps> = ({
  isOpen,
  onClose,
  serveWindow,
  allWindows,
  videoDuration,
  videoUrl,
  onSaved,
  onSplit,
  onDelete,
}) => {
  const [startTime, setStartTime] = useState(serveWindow.start_timestamp);
  const [endTime, setEndTime] = useState(serveWindow.end_timestamp);
  const [splitMode, setSplitMode] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [splitPoint, setSplitPoint] = useState(
    (serveWindow.start_timestamp + serveWindow.end_timestamp) / 2
  );
  const [error, setError] = useState<string | null>(null);
  // The timestamp the video should be showing right now
  const [previewTime, setPreviewTime] = useState(serveWindow.start_timestamp);

  const timelineRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const draggingRef = useRef<'left' | 'right' | 'split' | null>(null);

  // Seek video whenever previewTime changes
  useEffect(() => {
    const vid = videoRef.current;
    if (!vid) return;
    if (Math.abs(vid.currentTime - previewTime) > 0.05) {
      vid.currentTime = previewTime;
    }
  }, [previewTime]);

  // Sort sibling windows by start time
  const sortedWindows = useMemo(
    () =>
      [...allWindows]
        .filter((w) => w.is_active)
        .sort((a, b) => a.start_timestamp - b.start_timestamp),
    [allWindows]
  );

  const currentIndex = sortedWindows.findIndex((w) => w.id === serveWindow.id);
  const prevEnd =
    currentIndex > 0 ? sortedWindows[currentIndex - 1].end_timestamp : 0;
  const nextStart =
    currentIndex < sortedWindows.length - 1
      ? sortedWindows[currentIndex + 1].start_timestamp
      : videoDuration;

  // Reset state when serveWindow changes
  useEffect(() => {
    setStartTime(serveWindow.start_timestamp);
    setEndTime(serveWindow.end_timestamp);
    setSplitMode(false);
    setConfirmingDelete(false);
    setSplitPoint(
      (serveWindow.start_timestamp + serveWindow.end_timestamp) / 2
    );
    setPreviewTime(serveWindow.start_timestamp);
    setError(null);
  }, [serveWindow]);

  // Escape to close
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  const clampStart = useCallback(
    (val: number) =>
      Math.min(Math.max(val, prevEnd), endTime - MIN_WINDOW_DURATION),
    [prevEnd, endTime]
  );

  const clampEnd = useCallback(
    (val: number) =>
      Math.max(Math.min(val, nextStart), startTime + MIN_WINDOW_DURATION),
    [nextStart, startTime]
  );

  const clampSplit = useCallback(
    (val: number) =>
      Math.max(
        startTime + MIN_WINDOW_DURATION,
        Math.min(val, endTime - MIN_WINDOW_DURATION)
      ),
    [startTime, endTime]
  );

  const timeToPercent = useCallback(
    (t: number) => (videoDuration > 0 ? (t / videoDuration) * 100 : 0),
    [videoDuration]
  );

  const percentToTime = useCallback(
    (pct: number) => (pct / 100) * videoDuration,
    [videoDuration]
  );

  const getTimeFromMouseEvent = useCallback(
    (e: MouseEvent | React.MouseEvent) => {
      const rect = timelineRef.current?.getBoundingClientRect();
      if (!rect) return 0;
      const pct = Math.max(
        0,
        Math.min(100, ((e.clientX - rect.left) / rect.width) * 100)
      );
      return percentToTime(pct);
    },
    [percentToTime]
  );

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      const time = getTimeFromMouseEvent(e);
      if (draggingRef.current === 'left') {
        const clamped = clampStart(time);
        setStartTime(clamped);
        setPreviewTime(clamped);
      } else if (draggingRef.current === 'right') {
        const clamped = clampEnd(time);
        setEndTime(clamped);
        setPreviewTime(clamped);
      } else if (draggingRef.current === 'split') {
        const clamped = clampSplit(time);
        setSplitPoint(clamped);
        setPreviewTime(clamped);
      }
    },
    [getTimeFromMouseEvent, clampStart, clampEnd, clampSplit]
  );

  const handleMouseUp = useCallback(() => {
    draggingRef.current = null;
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
  }, [handleMouseMove]);

  const startDrag = useCallback(
    (handle: 'left' | 'right' | 'split') => (e: React.MouseEvent) => {
      e.preventDefault();
      draggingRef.current = handle;
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    },
    [handleMouseMove, handleMouseUp]
  );

  // Mutations
  const updateMutation = useMutation({
    mutationFn: () =>
      serveWindowApi.update(serveWindow.id, {
        start_timestamp: startTime,
        end_timestamp: endTime,
      }),
    onSuccess: (updated) => {
      onSaved(updated);
      onClose();
    },
    onError: (err: unknown) => {
      setError(getApiErrorMessage(err, 'Failed to save changes.'));
    },
  });

  const splitMutation = useMutation({
    mutationFn: () =>
      serveWindowApi.split(serveWindow.id, { split_at: splitPoint }),
    onSuccess: (response) => {
      onSplit(response);
      onClose();
    },
    onError: (err: unknown) => {
      setError(getApiErrorMessage(err, 'Failed to split window.'));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      if (onDelete) await onDelete(serveWindow.id);
    },
    onSuccess: () => {
      onClose();
    },
    onError: (err: unknown) => {
      setError(getApiErrorMessage(err, 'Failed to delete serve window.'));
      setConfirmingDelete(false);
    },
  });

  const isPending =
    updateMutation.isPending ||
    splitMutation.isPending ||
    deleteMutation.isPending;

  const handleSave = () => {
    setError(null);
    if (splitMode) {
      splitMutation.mutate();
    } else {
      updateMutation.mutate();
    }
  };

  if (!isOpen) return null;

  const splitDurationA = splitPoint - startTime;
  const splitDurationB = endTime - splitPoint;

  return (
    <div
      className="sw-edit-overlay"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 'var(--z-modal-backdrop)' as string,
        background: 'var(--color-modal-overlay)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--spacing-lg)',
      }}
    >
      <div
        className="sw-edit-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="sw-edit-title"
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--color-surface)',
          borderRadius: 'var(--radius-2xl)',
          width: '100%',
          maxWidth: '640px',
          maxHeight: '90vh',
          boxShadow: 'var(--shadow-2xl)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: 'var(--spacing-lg) var(--spacing-2xl)',
            borderBottom: '1px solid var(--color-border)',
            flexShrink: 0,
          }}
        >
          <h2
            id="sw-edit-title"
            style={{
              fontFamily: 'var(--font-family-sans)',
              fontSize: 'var(--font-size-lg)',
              fontWeight: 'var(--font-weight-semibold)',
              color: 'var(--color-text)',
              margin: 0,
            }}
          >
            Edit Serve Window
          </h2>
          <button
            onClick={onClose}
            aria-label="Close"
            type="button"
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--color-text-muted)',
              padding: 'var(--spacing-xs)',
              borderRadius: 'var(--radius-sm)',
              display: 'flex',
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Scrollable body */}
        <div
          style={{
            overflowY: 'auto',
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--spacing-2xl)',
            padding: 'var(--spacing-2xl)',
          }}
        >
          {/* Video preview */}
          <div
            style={{
              background: '#000',
              borderRadius: 'var(--radius-lg)',
              overflow: 'hidden',
              aspectRatio: '16 / 9',
              flexShrink: 0,
            }}
          >
            <video
              ref={videoRef}
              src={videoUrl}
              muted
              playsInline
              preload="auto"
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'contain',
                display: 'block',
              }}
            />
          </div>

          {/* Timeline */}
          <div>
            <div
              style={{
                fontFamily: 'var(--font-family-sans)',
                fontSize: 'var(--font-size-sm)',
                fontWeight: 'var(--font-weight-medium)',
                color: 'var(--color-text-muted)',
                textTransform: 'uppercase' as const,
                letterSpacing: 'var(--letter-spacing-wide)',
                marginBottom: 'var(--spacing-sm)',
              }}
            >
              Timeline
            </div>
            <div
              ref={timelineRef}
              style={{
                position: 'relative',
                height: '48px',
                background: 'var(--color-surface-secondary)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border)',
                overflow: 'visible',
                userSelect: 'none',
                marginBottom: '24px',
              }}
            >
              {/* Sibling windows */}
              {sortedWindows.map((w) =>
                w.id !== serveWindow.id ? (
                  <div
                    key={w.id}
                    style={{
                      position: 'absolute',
                      left: `${timeToPercent(w.start_timestamp)}%`,
                      width: `${timeToPercent(w.end_timestamp - w.start_timestamp)}%`,
                      top: 0,
                      bottom: 0,
                      background: 'var(--color-border)',
                      opacity: 0.5,
                    }}
                  />
                ) : null
              )}

              {/* Current window highlight */}
              <div
                style={{
                  position: 'absolute',
                  left: `${timeToPercent(startTime)}%`,
                  width: `${timeToPercent(endTime - startTime)}%`,
                  top: 0,
                  bottom: 0,
                  background: 'var(--color-court-blue-soft)',
                  border: '2px solid var(--color-court-blue)',
                  borderRadius: 'var(--radius-xs)',
                }}
              />

              {/* Left drag handle */}
              <div
                onMouseDown={startDrag('left')}
                style={{
                  position: 'absolute',
                  left: `${timeToPercent(startTime)}%`,
                  top: 0,
                  bottom: 0,
                  width: '10px',
                  transform: 'translateX(-50%)',
                  cursor: 'ew-resize',
                  zIndex: 2,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <div
                  style={{
                    width: '4px',
                    height: '20px',
                    background: 'var(--color-court-blue)',
                    borderRadius: 'var(--radius-full)',
                  }}
                />
              </div>

              {/* Right drag handle */}
              <div
                onMouseDown={startDrag('right')}
                style={{
                  position: 'absolute',
                  left: `${timeToPercent(endTime)}%`,
                  top: 0,
                  bottom: 0,
                  width: '10px',
                  transform: 'translateX(-50%)',
                  cursor: 'ew-resize',
                  zIndex: 2,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <div
                  style={{
                    width: '4px',
                    height: '20px',
                    background: 'var(--color-court-blue)',
                    borderRadius: 'var(--radius-full)',
                  }}
                />
              </div>

              {/* Split marker */}
              {splitMode && (
                <div
                  onMouseDown={startDrag('split')}
                  style={{
                    position: 'absolute',
                    left: `${timeToPercent(splitPoint)}%`,
                    top: 0,
                    bottom: 0,
                    width: '14px',
                    transform: 'translateX(-50%)',
                    cursor: 'ew-resize',
                    zIndex: 3,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <div
                    style={{
                      width: '2px',
                      height: '100%',
                      background: 'var(--color-error)',
                      position: 'relative',
                    }}
                  >
                    <div
                      style={{
                        position: 'absolute',
                        top: '-6px',
                        left: '50%',
                        transform: 'translateX(-50%)',
                        width: '10px',
                        height: '10px',
                        borderRadius: 'var(--radius-full)',
                        background: 'var(--color-error)',
                      }}
                    />
                  </div>
                </div>
              )}

              {/* Timestamp labels */}
              <div
                style={{
                  position: 'absolute',
                  left: `${timeToPercent(startTime)}%`,
                  bottom: '-20px',
                  transform: 'translateX(-50%)',
                  fontFamily: 'var(--font-family-mono)',
                  fontSize: 'var(--font-size-xs)',
                  color: 'var(--color-text-muted)',
                  whiteSpace: 'nowrap',
                }}
              >
                {formatTimestamp(startTime)}
              </div>
              <div
                style={{
                  position: 'absolute',
                  left: `${timeToPercent(endTime)}%`,
                  bottom: '-20px',
                  transform: 'translateX(-50%)',
                  fontFamily: 'var(--font-family-mono)',
                  fontSize: 'var(--font-size-xs)',
                  color: 'var(--color-text-muted)',
                  whiteSpace: 'nowrap',
                }}
              >
                {formatTimestamp(endTime)}
              </div>
            </div>
          </div>

          {/* Numeric inputs */}
          <div
            style={{
              display: 'flex',
              gap: 'var(--spacing-lg)',
              marginTop: 'var(--spacing-sm)',
            }}
          >
            <div style={{ flex: 1 }}>
              <label
                style={{
                  display: 'block',
                  fontFamily: 'var(--font-family-sans)',
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 'var(--font-weight-medium)',
                  color: 'var(--color-text-muted)',
                  marginBottom: 'var(--spacing-xs)',
                }}
              >
                Start (s)
              </label>
              <input
                type="number"
                step={0.01}
                min={prevEnd}
                max={endTime - MIN_WINDOW_DURATION}
                value={Number(startTime.toFixed(2))}
                onChange={(e) => {
                  const clamped = clampStart(Number(e.target.value));
                  setStartTime(clamped);
                  setPreviewTime(clamped);
                }}
                disabled={isPending || splitMode}
                style={{
                  width: '100%',
                  padding: 'var(--input-padding)',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--input-border-radius)',
                  fontFamily: 'var(--font-family-mono)',
                  fontSize: 'var(--font-size-base)',
                  color: 'var(--color-text)',
                  background: splitMode
                    ? 'var(--color-surface-secondary)'
                    : 'var(--color-surface)',
                  boxSizing: 'border-box' as const,
                }}
              />
            </div>
            <div style={{ flex: 1 }}>
              <label
                style={{
                  display: 'block',
                  fontFamily: 'var(--font-family-sans)',
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 'var(--font-weight-medium)',
                  color: 'var(--color-text-muted)',
                  marginBottom: 'var(--spacing-xs)',
                }}
              >
                End (s)
              </label>
              <input
                type="number"
                step={0.01}
                min={startTime + MIN_WINDOW_DURATION}
                max={nextStart}
                value={Number(endTime.toFixed(2))}
                onChange={(e) => {
                  const clamped = clampEnd(Number(e.target.value));
                  setEndTime(clamped);
                  setPreviewTime(clamped);
                }}
                disabled={isPending || splitMode}
                style={{
                  width: '100%',
                  padding: 'var(--input-padding)',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--input-border-radius)',
                  fontFamily: 'var(--font-family-mono)',
                  fontSize: 'var(--font-size-base)',
                  color: 'var(--color-text)',
                  background: splitMode
                    ? 'var(--color-surface-secondary)'
                    : 'var(--color-surface)',
                  boxSizing: 'border-box' as const,
                }}
              />
            </div>
          </div>

          {/* Split mode toggle */}
          <button
            type="button"
            onClick={() => {
              setSplitMode(!splitMode);
              if (!splitMode) {
                const mid = clampSplit((startTime + endTime) / 2);
                setSplitPoint(mid);
                setPreviewTime(mid);
              }
            }}
            disabled={isPending}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 'var(--spacing-sm)',
              padding: 'var(--button-padding-sm)',
              border: splitMode
                ? '1px solid var(--color-error)'
                : '1px solid var(--color-border)',
              borderRadius: 'var(--button-border-radius)',
              background: splitMode
                ? 'var(--color-error-soft)'
                : 'var(--color-surface)',
              color: splitMode
                ? 'var(--color-error-dark)'
                : 'var(--color-text)',
              fontFamily: 'var(--font-family-sans)',
              fontSize: 'var(--font-size-base)',
              fontWeight: 'var(--font-weight-medium)',
              cursor: 'pointer',
              alignSelf: 'flex-start',
              transition: 'var(--transition-fast)',
            }}
          >
            <Scissors size={14} />
            {splitMode ? 'Cancel split' : 'Split window'}
          </button>

          {/* Split preview */}
          {splitMode && (
            <div
              style={{
                display: 'flex',
                gap: 'var(--spacing-lg)',
                padding: 'var(--spacing-lg)',
                background: 'var(--color-surface-secondary)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border)',
              }}
            >
              <div style={{ flex: 1 }}>
                <div
                  style={{
                    fontFamily: 'var(--font-family-sans)',
                    fontSize: 'var(--font-size-sm)',
                    fontWeight: 'var(--font-weight-medium)',
                    color: 'var(--color-text-muted)',
                    textTransform: 'uppercase' as const,
                    letterSpacing: 'var(--letter-spacing-wide)',
                    marginBottom: 'var(--spacing-xs)',
                  }}
                >
                  Segment A
                </div>
                <div
                  style={{
                    fontFamily: 'var(--font-family-mono)',
                    fontSize: 'var(--font-size-display-sm)',
                    fontWeight: 'var(--font-weight-medium)',
                    color: 'var(--color-ink-heavy)',
                  }}
                >
                  {splitDurationA.toFixed(2)}s
                </div>
                <div
                  style={{
                    fontFamily: 'var(--font-family-mono)',
                    fontSize: 'var(--font-size-xs)',
                    color: 'var(--color-text-muted)',
                    marginTop: 'var(--spacing-xs)',
                  }}
                >
                  {formatTimestamp(startTime)} → {formatTimestamp(splitPoint)}
                </div>
              </div>
              <div
                style={{ width: '1px', background: 'var(--color-border)' }}
              />
              <div style={{ flex: 1 }}>
                <div
                  style={{
                    fontFamily: 'var(--font-family-sans)',
                    fontSize: 'var(--font-size-sm)',
                    fontWeight: 'var(--font-weight-medium)',
                    color: 'var(--color-text-muted)',
                    textTransform: 'uppercase' as const,
                    letterSpacing: 'var(--letter-spacing-wide)',
                    marginBottom: 'var(--spacing-xs)',
                  }}
                >
                  Segment B
                </div>
                <div
                  style={{
                    fontFamily: 'var(--font-family-mono)',
                    fontSize: 'var(--font-size-display-sm)',
                    fontWeight: 'var(--font-weight-medium)',
                    color: 'var(--color-ink-heavy)',
                  }}
                >
                  {splitDurationB.toFixed(2)}s
                </div>
                <div
                  style={{
                    fontFamily: 'var(--font-family-mono)',
                    fontSize: 'var(--font-size-xs)',
                    color: 'var(--color-text-muted)',
                    marginTop: 'var(--spacing-xs)',
                  }}
                >
                  {formatTimestamp(splitPoint)} → {formatTimestamp(endTime)}
                </div>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div
              style={{
                padding: 'var(--spacing-md) var(--spacing-lg)',
                background: 'var(--color-error-soft)',
                border: '1px solid var(--color-error-light)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--color-error-dark)',
                fontFamily: 'var(--font-family-sans)',
                fontSize: 'var(--font-size-sm)',
              }}
            >
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            gap: 'var(--spacing-md)',
            padding: 'var(--spacing-lg) var(--spacing-2xl)',
            borderTop: '1px solid var(--color-border)',
            flexShrink: 0,
          }}
        >
          {/* Left: delete */}
          <div>
            {onDelete &&
              !splitMode &&
              (confirmingDelete ? (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--spacing-sm)',
                  }}
                >
                  <span
                    style={{
                      fontFamily: 'var(--font-family-sans)',
                      fontSize: 'var(--font-size-sm)',
                      color: 'var(--color-error-dark)',
                    }}
                  >
                    Delete this serve?
                  </span>
                  <button
                    type="button"
                    onClick={() => deleteMutation.mutate()}
                    disabled={isPending}
                    style={{
                      padding: 'var(--button-padding-sm)',
                      border: 'none',
                      borderRadius: 'var(--button-border-radius)',
                      background: 'var(--color-error)',
                      color: '#fff',
                      fontFamily: 'var(--font-family-sans)',
                      fontSize: 'var(--font-size-sm)',
                      fontWeight: 'var(--font-weight-medium)',
                      cursor: isPending ? 'not-allowed' : 'pointer',
                      opacity: isPending ? 0.7 : 1,
                    }}
                  >
                    {deleteMutation.isPending ? 'Deleting...' : 'Confirm'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirmingDelete(false)}
                    disabled={isPending}
                    style={{
                      padding: 'var(--button-padding-sm)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--button-border-radius)',
                      background: 'var(--color-surface)',
                      color: 'var(--color-text)',
                      fontFamily: 'var(--font-family-sans)',
                      fontSize: 'var(--font-size-sm)',
                      fontWeight: 'var(--font-weight-medium)',
                      cursor: 'pointer',
                    }}
                  >
                    No
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => setConfirmingDelete(true)}
                  disabled={isPending}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 'var(--spacing-xs)',
                    padding: 'var(--button-padding-sm)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--button-border-radius)',
                    background: 'var(--color-surface)',
                    color: 'var(--color-text-muted)',
                    fontFamily: 'var(--font-family-sans)',
                    fontSize: 'var(--font-size-sm)',
                    fontWeight: 'var(--font-weight-medium)',
                    cursor: 'pointer',
                    transition: 'var(--transition-fast)',
                  }}
                >
                  <Trash2 size={14} />
                  Delete
                </button>
              ))}
          </div>

          {/* Right: cancel + save */}
          <div style={{ display: 'flex', gap: 'var(--spacing-md)' }}>
            <button
              type="button"
              onClick={onClose}
              disabled={isPending}
              style={{
                padding: 'var(--button-padding-md)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--button-border-radius)',
                background: 'var(--color-surface)',
                color: 'var(--color-text)',
                fontFamily: 'var(--font-family-sans)',
                fontSize: 'var(--font-size-base)',
                fontWeight: 'var(--font-weight-medium)',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={isPending}
              style={{
                padding: 'var(--button-padding-md)',
                border: 'none',
                borderRadius: 'var(--button-border-radius)',
                background: splitMode
                  ? 'var(--color-error)'
                  : 'var(--color-primary)',
                color: '#fff',
                fontFamily: 'var(--font-family-sans)',
                fontSize: 'var(--font-size-base)',
                fontWeight: 'var(--font-weight-semibold)',
                cursor: isPending ? 'not-allowed' : 'pointer',
                opacity: isPending ? 0.7 : 1,
              }}
            >
              {isPending
                ? 'Saving...'
                : splitMode
                  ? 'Confirm split'
                  : 'Save changes'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ServeWindowEditModal;
