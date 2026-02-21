import { useCallback, useEffect, useRef, useState } from 'react';

type MarkerType = 'start' | 'end' | 'contact' | null;

interface UseTimelineDragOptions {
  startTime: number;
  endTime: number;
  videoDuration: number;
  windowDuration: number;
  zoomToWindow: boolean;
  contactTime: number | null;
  onStartChange: (time: number) => void;
  onEndChange: (time: number) => void;
  onContactChange?: (time: number | null) => void;
  onSeek?: (time: number) => void;
}

export function useTimelineDrag({
  startTime,
  endTime,
  videoDuration,
  windowDuration,
  zoomToWindow,
  contactTime,
  onStartChange,
  onEndChange,
  onContactChange,
  onSeek,
}: UseTimelineDragOptions) {
  const timelineRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState<MarkerType>(null);
  const [hoverTime, setHoverTime] = useState<number | null>(null);

  // Get time from mouse position
  // When zoomed to window, map to the window range; otherwise map to video duration
  const getTimeFromPosition = useCallback(
    (clientX: number): number => {
      if (!timelineRef.current) return zoomToWindow ? startTime : 0;
      const rect = timelineRef.current.getBoundingClientRect();
      const x = clientX - rect.left;
      const percent = Math.max(0, Math.min(100, (x / rect.width) * 100));

      if (zoomToWindow) {
        // Map to window range: 0% = startTime, 100% = endTime
        return startTime + (percent / 100) * windowDuration;
      } else {
        // Map to video duration: 0% = 0, 100% = videoDuration
        return (percent / 100) * videoDuration;
      }
    },
    [zoomToWindow, startTime, windowDuration, videoDuration]
  );

  // Handle mouse down on marker
  const handleMarkerMouseDown = useCallback(
    (e: React.MouseEvent, markerType: MarkerType) => {
      e.preventDefault();
      e.stopPropagation();
      setDragging(markerType);
    },
    []
  );

  // Handle mouse move during drag
  useEffect(() => {
    if (!dragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      const time = getTimeFromPosition(e.clientX);

      if (dragging === 'start') {
        // When zoomed to window, allow slight expansion beyond current window
        // but still respect video bounds
        const minTime = zoomToWindow
          ? Math.max(0, startTime - windowDuration * 0.5)
          : 0;
        const maxTime = endTime - 0.1;
        const clampedTime = Math.max(minTime, Math.min(time, maxTime));
        onStartChange(clampedTime);
        if (onSeek) onSeek(clampedTime);
      } else if (dragging === 'end') {
        // When zoomed to window, allow slight expansion beyond current window
        // but still respect video bounds
        const minTime = startTime + 0.1;
        const maxTime = zoomToWindow
          ? Math.min(videoDuration, endTime + windowDuration * 0.5)
          : videoDuration;
        const clampedTime = Math.max(minTime, Math.min(time, maxTime));
        onEndChange(clampedTime);
        if (onSeek) onSeek(clampedTime);
      } else if (dragging === 'contact' && onContactChange) {
        const clampedTime = Math.max(startTime, Math.min(time, endTime));
        onContactChange(clampedTime);
        if (onSeek) onSeek(clampedTime);
      }
    };

    const handleMouseUp = () => {
      setDragging(null);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [
    dragging,
    getTimeFromPosition,
    startTime,
    endTime,
    videoDuration,
    windowDuration,
    zoomToWindow,
    onStartChange,
    onEndChange,
    onContactChange,
    onSeek,
  ]);

  // Handle timeline click
  const handleTimelineClick = useCallback(
    (e: React.MouseEvent) => {
      if (dragging) return; // Don't handle clicks while dragging
      const time = getTimeFromPosition(e.clientX);

      // Determine which marker to set based on click position
      const distToStart = Math.abs(time - startTime);
      const distToEnd = Math.abs(time - endTime);
      const distToContact =
        contactTime !== null ? Math.abs(time - contactTime) : Infinity;

      // If clicking near a marker, don't do anything (let drag handle it)
      if (distToStart < 0.5 || distToEnd < 0.5 || distToContact < 0.5) {
        return;
      }

      // If clicking before start, set start
      if (time < startTime) {
        onStartChange(Math.max(0, time));
        if (onSeek) onSeek(time);
      }
      // If clicking after end, set end
      else if (time > endTime) {
        onEndChange(Math.min(videoDuration, time));
        if (onSeek) onSeek(time);
      }
      // If clicking between start and end, set contact (if handler exists) or move nearest marker
      else {
        if (onContactChange && e.shiftKey === false) {
          // Shift+click to move start/end, regular click to set contact
          const clampedTime = Math.max(startTime, Math.min(time, endTime));
          onContactChange(clampedTime);
          if (onSeek) onSeek(clampedTime);
        } else {
          // Move the nearest marker (start or end)
          if (distToStart <= distToEnd) {
            const clampedTime = Math.max(0, Math.min(time, endTime - 0.1));
            onStartChange(clampedTime);
            if (onSeek) onSeek(clampedTime);
          } else {
            const clampedTime = Math.max(
              startTime + 0.1,
              Math.min(time, videoDuration)
            );
            onEndChange(clampedTime);
            if (onSeek) onSeek(clampedTime);
          }
        }
      }
    },
    [
      dragging,
      getTimeFromPosition,
      startTime,
      endTime,
      contactTime,
      videoDuration,
      onStartChange,
      onEndChange,
      onContactChange,
      onSeek,
    ]
  );

  // Handle timeline hover
  const handleTimelineMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (dragging) return;
      const time = getTimeFromPosition(e.clientX);
      setHoverTime(time);
    },
    [dragging, getTimeFromPosition]
  );

  const handleTimelineMouseLeave = useCallback(() => {
    if (!dragging) {
      setHoverTime(null);
    }
  }, [dragging]);

  return {
    timelineRef,
    dragging,
    hoverTime,
    handleMarkerMouseDown,
    handleTimelineClick,
    handleTimelineMouseMove,
    handleTimelineMouseLeave,
  };
}
