import React, { useCallback, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import {
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
  const {
    data: feedback,
    isLoading,
    isFetching,
    refetch,
  } = useCoachingFeedback(serveWindowId);
  const { data: notes } = useCoachingNotes(serveWindowId, !isDemo);
  const saveNote = useSaveCoachingNote(serveWindowId);

  const handleGetFeedback = () => {
    refetch();
  };

  const handleSaveNote = useCallback(() => {
    if (!noteText.trim()) return;
    saveNote.mutate(noteText.trim(), {
      onSuccess: () => setNoteText(''),
    });
  }, [noteText, saveNote]);

  if (isDemo || !serveWindowId) return null;

  return (
    <div className="coaching-panel">
      {/* Trigger button */}
      {!feedback && !isLoading && !isFetching && (
        <button
          type="button"
          className="coaching-panel__trigger-btn"
          onClick={handleGetFeedback}
        >
          Get Coaching Feedback
        </button>
      )}

      {(isLoading || isFetching) && (
        <div className="coaching-panel__loading">
          <span className="coaching-panel__loading-text">
            Thinking about your serve...
          </span>
        </div>
      )}

      {feedback && !isFetching && (
        <div className="coaching-panel__feedback">
          <div className="coaching-panel__feedback-text">
            <ReactMarkdown>{feedback.feedback}</ReactMarkdown>
          </div>
          <div className="coaching-panel__meta">
            {feedback.input_tokens + feedback.output_tokens} tokens &middot;{' '}
            {Math.round(feedback.latency_ms)}ms
          </div>
        </div>
      )}

      {/* Notes section */}
      <div className="coaching-panel__notes">
        <label className="coaching-panel__notes-label">EVAL NOTES</label>
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
