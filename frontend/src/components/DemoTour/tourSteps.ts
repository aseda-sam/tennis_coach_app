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
  actionHint?: string;
  onEnter?: (controls: TourPlaybackControls) => void;
}

export const TOUR_STEPS: TourStep[] = [
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
