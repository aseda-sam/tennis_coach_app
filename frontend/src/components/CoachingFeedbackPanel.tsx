import React, { useCallback, useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  useCachedCoachingFeedback,
  useCoachingFeedback,
  useCoachingNotes,
  useSaveCoachingNote,
} from '../hooks/useCoachingFeedback';
import './CoachingFeedbackPanel.css';

interface CoachingFeedbackPanelProps {
  serveWindowId: number | null;
  isDemo: boolean;
}

const CoachingFeedbackPanel: React.FC<CoachingFeedbackPanelProps> = ({
  serveWindowId,
  isDemo,
}) => {
  const [noteText, setNoteText] = useState('');
  const [justSaved, setJustSaved] = useState(false);

  // Auto-fetch cached trace
  const { data: cachedFeedback, isLoading: cachedLoading } =
    useCachedCoachingFeedback(serveWindowId);

  // Manual regenerate
  const {
    data: freshFeedback,
    isLoading: freshLoading,
    isFetching: freshFetching,
    refetch,
  } = useCoachingFeedback(serveWindowId);

  const { data: notes } = useCoachingNotes(serveWindowId, !isDemo);
  const saveNote = useSaveCoachingNote(serveWindowId);

  // Use fresh feedback if available, otherwise cached
  const feedback = freshFeedback ?? cachedFeedback;
  const isGenerating = freshLoading || freshFetching;

  // Clear the "Saved" indicator after 2 seconds
  useEffect(() => {
    if (!justSaved) return;
    const timer = setTimeout(() => setJustSaved(false), 2000);
    return () => clearTimeout(timer);
  }, [justSaved]);

  // Reset justSaved when switching serves
  useEffect(() => {
    setJustSaved(false);
  }, [serveWindowId]);

  const handleRegenerate = () => {
    refetch();
  };

  const handleSaveNote = useCallback(() => {
    if (!noteText.trim()) return;
    saveNote.mutate(noteText.trim(), {
      onSuccess: () => {
        setNoteText('');
        setJustSaved(true);
      },
    });
  }, [noteText, saveNote]);

  if (isDemo || !serveWindowId) return null;

  return (
    <div className="coaching-panel">
      {/* Loading cached trace */}
      {cachedLoading && !feedback && (
        <div className="coaching-panel__loading">
          <span className="coaching-panel__loading-text">
            Loading feedback...
          </span>
        </div>
      )}

      {/* No cached trace — offer to generate */}
      {!cachedLoading && !feedback && !isGenerating && (
        <button
          type="button"
          className="coaching-panel__trigger-btn"
          onClick={handleRegenerate}
        >
          Get Coaching Feedback
        </button>
      )}

      {/* Generating fresh feedback */}
      {isGenerating && (
        <div className="coaching-panel__loading">
          <span className="coaching-panel__loading-text">
            Thinking about your serve...
          </span>
        </div>
      )}

      {/* Show feedback */}
      {feedback && !isGenerating && (
        <div className="coaching-panel__feedback">
          <div className="coaching-panel__feedback-text">
            <ReactMarkdown>{feedback.feedback}</ReactMarkdown>
          </div>
          <div className="coaching-panel__meta">
            {feedback.input_tokens + feedback.output_tokens} tokens &middot;{' '}
            {feedback.latency_ms < 1000
              ? `${Math.round(feedback.latency_ms)}ms`
              : feedback.latency_ms < 60000
                ? `${(feedback.latency_ms / 1000).toFixed(1)}s`
                : `${Math.floor(feedback.latency_ms / 60000)}m ${Math.round((feedback.latency_ms % 60000) / 1000)}s`}
            <button
              type="button"
              className="coaching-panel__regenerate-btn"
              onClick={handleRegenerate}
            >
              Regenerate
            </button>
          </div>
        </div>
      )}

      {/* Notes section */}
      <div className="coaching-panel__notes">
        <div className="coaching-panel__notes-header">
          <label className="coaching-panel__notes-label">EVAL NOTES</label>
          {justSaved && (
            <span className="coaching-panel__saved-badge">
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <polyline points="20 6 9 17 4 12" />
              </svg>
              Saved
            </span>
          )}
        </div>
        {notes && notes.length > 0 && (
          <div className="coaching-panel__notes-list">
            {notes.map((n, i) => (
              <div key={i} className="coaching-panel__note-item">
                {n.note}
              </div>
            ))}
          </div>
        )}
        <textarea
          className="coaching-panel__notes-input"
          placeholder="What's the first upstream error in this output?"
          value={noteText}
          onChange={(e) => setNoteText(e.target.value)}
          rows={3}
        />
        <button
          type="button"
          className="coaching-panel__save-btn"
          onClick={handleSaveNote}
          disabled={!noteText.trim() || saveNote.isPending}
        >
          {saveNote.isPending ? 'Saving...' : 'Save Note'}
        </button>
      </div>
    </div>
  );
};

export default CoachingFeedbackPanel;
