import React from 'react';
import { usePlayerProfile } from '../../hooks/usePlayerProfile';
import { usePlayerTrophyHistory } from '../../hooks/usePlayerTrophyHistory';
import { TrophyFrameCell } from '../TrophyFilmstripModal';
import LoadingIndicator from '../LoadingIndicator';
import './PlayerAnalysisPage.css';

function PlayerAnalysisPage() {
  const { data: player, isLoading: playerLoading } = usePlayerProfile();
  const { entries, isLoading: historyLoading } = usePlayerTrophyHistory(
    player?.id ?? null
  );

  const isLoading = playerLoading || historyLoading;

  return (
    <div className="app-container">
      <div className="player-analysis">
        <header className="player-analysis__header">
          <h1 className="player-analysis__title">Analysis</h1>
          {player && (
            <span className="player-analysis__subtitle">{player.name}</span>
          )}
        </header>

        <section className="player-analysis__section">
          <h2 className="player-analysis__section-title">Trophy Position</h2>

          {isLoading ? (
            <div className="player-analysis__loading">
              <LoadingIndicator size="md" label="Loading history..." />
            </div>
          ) : entries.length === 0 ? (
            <div className="player-analysis__empty">
              <p>No trophy position data yet.</p>
              <p className="player-analysis__empty-hint">
                Upload and analyze serve videos to see your trophy positions
                across sessions.
              </p>
            </div>
          ) : (
            <div className="player-analysis__filmstrip">
              {entries.map((entry, i) => (
                <div
                  key={entry.serveWindowId}
                  className="player-analysis__filmstrip-item"
                >
                  <TrophyFrameCell
                    serveWindowId={entry.serveWindowId}
                    label={`Serve ${i + 1}`}
                    method={entry.method}
                    confidence={entry.confidence}
                  />
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

export default PlayerAnalysisPage;
