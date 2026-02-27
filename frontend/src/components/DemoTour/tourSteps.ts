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
    id: 'hero-view',
    target: '[data-tour-step="hero-view"]',
    placement: 'bottom',
    title: 'Every Joint, Every Frame',
    body: 'The AI tracked every joint across the entire serve. Watch the knees load, then the arm whip forward.',
    onEnter: (controls) => {
      controls.setPlaybackSpeed(0.25);
    },
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
    title: '8 Moments in One Motion',
    body: 'What looks like one swing is actually 8 distinct moments. Each tab jumps the video to that phase — so you can study what matters most.',
    onEnter: (controls) => {
      controls.pause();
      controls.seekToPhase('loading');
      setTimeout(() => {
        controls.seekToPhase('contact');
      }, 1200);
    },
  },
  {
    id: 'metrics-section',
    target: '[data-tour-step="metrics-section"]',
    placement: 'left',
    title: 'What the Numbers Mean',
    body: 'Knee Flexion: how much you bend before the swing. More bend = more leg power into the ball.\n\nClick any card to jump to the exact frame it was measured.',
  },
  {
    id: 'your-turn',
    target: null,
    placement: 'center',
    title: 'Your Turn',
    body: 'You just saw one serve broken into 8 phases and measured frame by frame.\n\nWhat does yours look like? Upload a video — it takes about 60 seconds.',
    onEnter: (controls) => {
      controls.pause();
    },
  },
];
