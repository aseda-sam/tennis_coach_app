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
    body: 'Every joint is tracked across the entire serve. Slow it down to spot details you\u2019d miss at full speed.',
    onEnter: (controls) => {
      controls.setPlaybackSpeed(0.25);
    },
  },
  {
    id: 'view-toggle',
    target: '[data-tour-step="view-toggle"]',
    placement: 'bottom',
    title: 'Skeleton or Video',
    body: 'Switch between the pose skeleton and the original footage.',
  },
  {
    id: 'thumbnail-strip',
    target: '[data-tour-step="thumbnail-strip"]',
    placement: 'bottom',
    title: 'One Video, Multiple Serves',
    body: 'Each serve attempt was detected automatically. Click a thumbnail to switch between them.',
  },
  {
    id: 'phase-tabs',
    target: '[data-tour-step="phase-tabs"]',
    placement: 'top',
    title: 'Jump to Any Phase',
    body: 'Each tab jumps the video to that phase of the serve. Click one and the video snaps straight to it.',
    onEnter: (controls) => {
      controls.pause();
      controls.seekToPhase('toss');
      setTimeout(() => {
        controls.seekToPhase('acceleration');
      }, 1200);
    },
  },
  {
    id: 'feature-charts',
    target: '[data-tour-step="feature-charts"]',
    placement: 'left',
    title: 'The Body as a Graph',
    body: 'Each curve traces one joint angle through the entire serve. Drag anywhere on a chart to jump the video to that moment.',
  },
];
