import { DemoTourContext } from '../../types/video';

export type { DemoTourContext };

export interface TourPlaybackControls {
  seekToPhase: (phaseKey: string) => void;
  setPlaybackSpeed: (speed: number) => void;
  pause: () => void;
}

export interface TourStep {
  id: string;
  target: string | null;
  placement: 'top' | 'bottom' | 'left' | 'right' | 'center';
  title: string;
  body: string;
  /** Factual context line shown below body (populated from tour_context.player_note). */
  playerNote?: string;
  actionHint?: string;
  onEnter?: (controls: TourPlaybackControls) => void;
}

const BASE_STEPS: TourStep[] = [
  {
    id: 'hero-display',
    target: '[data-tour-step="hero-display"]',
    placement: 'bottom',
    title: 'Every Joint, Every Frame',
    body: 'The AI tracked every joint across the entire serve. Watch the knees load, then the arm whip forward.',
    onEnter: (controls) => {
      controls.setPlaybackSpeed(0.25);
    },
  },
  {
    id: 'view-toggle',
    target: '[data-tour-step="view-toggle"]',
    placement: 'bottom',
    title: 'Skeleton or Video',
    body: 'Switch between the AI pose overlay and the original footage. Both stay perfectly in sync.',
  },
  {
    id: 'thumbnail-strip',
    target: '[data-tour-step="thumbnail-strip"]',
    placement: 'bottom',
    title: 'One Video, Multiple Serves',
    body: 'The app found each serve attempt automatically. Click a thumbnail to switch between them.',
  },
  {
    id: 'phase-tabs',
    target: '[data-tour-step="phase-tabs"]',
    placement: 'top',
    title: 'Jump to Any Phase',
    body: 'Each tab jumps the video to that phase of the serve. Click one — the video snaps straight to it.',
    onEnter: (controls) => {
      controls.pause();
      controls.seekToPhase('loading');
      setTimeout(() => {
        controls.seekToPhase('contact');
      }, 1200);
    },
  },
  {
    id: 'feature-charts',
    target: '[data-tour-step="feature-charts"]',
    placement: 'left',
    title: 'The Body as a Graph',
    body: "Each curve traces one joint angle through the entire serve. Find the lowest point on the Knee Flexion line — that's the Loading phase, the deepest bend before the legs drive the swing upward.\n\nDrag anywhere on a chart to jump the video to that moment.",
  },
];

/**
 * Build the tour step array, optionally enriched with per-video context
 * from the backend's tour_context field. Context is observational — it
 * highlights what's interesting to notice, never prescriptive coaching.
 */
export function buildTourSteps(context?: DemoTourContext | null): TourStep[] {
  if (!context) return BASE_STEPS;

  return BASE_STEPS.map((step) => {
    const stepNote = context.step_notes?.[step.id];
    const playerNote =
      step.id === 'hero-display' ? context.player_note : undefined;

    if (!stepNote && !playerNote) return step;

    return {
      ...step,
      body: stepNote ? `${step.body}\n\n${stepNote}` : step.body,
      playerNote: playerNote ?? step.playerNote,
    };
  });
}
