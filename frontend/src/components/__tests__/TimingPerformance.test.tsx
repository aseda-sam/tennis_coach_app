import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import TimingPerformance from '../TimingPerformance';

describe('TimingPerformance', () => {
  const mockTimingData = {
    frame_extraction: 2.5,
    ball_detection: 8.3,
    pose_detection: 12.1,
    frame_annotation: 3.2,
    video_creation: 1.8,
    total_analysis: 27.9,
  };

  describe('with detailed timing data', () => {
    it('renders performance breakdown with all stages', () => {
      render(<TimingPerformance timing={mockTimingData} />);

      expect(screen.getByText('Performance Breakdown')).toBeInTheDocument();
      expect(screen.getByText('27.90s')).toBeInTheDocument();
      expect(screen.getByText('Frame Extraction')).toBeInTheDocument();
      expect(screen.getByText('Ball Detection')).toBeInTheDocument();
      expect(screen.getByText('Pose Detection')).toBeInTheDocument();
      expect(screen.getByText('Frame Annotation')).toBeInTheDocument();
      expect(screen.getByText('Video Creation')).toBeInTheDocument();
    });

    it('displays correct timing values for each stage', () => {
      render(<TimingPerformance timing={mockTimingData} />);

      expect(screen.getByText('2.50s')).toBeInTheDocument(); // frame_extraction
      expect(screen.getByText('8.30s')).toBeInTheDocument(); // ball_detection
      expect(screen.getByText('12.10s')).toBeInTheDocument(); // pose_detection
      expect(screen.getByText('3.20s')).toBeInTheDocument(); // frame_annotation
      expect(screen.getByText('1.80s')).toBeInTheDocument(); // video_creation
    });

    it('calculates and displays correct percentages', () => {
      render(<TimingPerformance timing={mockTimingData} />);

      // frame_extraction: 2.5 / 27.9 * 100 = 8.96%
      expect(screen.getByText('9.0%')).toBeInTheDocument();
      // ball_detection: 8.3 / 27.9 * 100 = 29.75%
      expect(screen.getByText('29.7%')).toBeInTheDocument();
      // pose_detection: 12.1 / 27.9 * 100 = 43.37%
      expect(screen.getByText('43.4%')).toBeInTheDocument();
    });

    it('displays performance insights', () => {
      render(<TimingPerformance timing={mockTimingData} />);

      expect(
        screen.getByText(/Analysis completed in a reasonable time/)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Ball detection took 29.7% of total time/)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Pose detection took 43.4% of total time/)
      ).toBeInTheDocument();
    });

    it('renders stage icons correctly', () => {
      render(<TimingPerformance timing={mockTimingData} />);

      expect(screen.getByText('🎬')).toBeInTheDocument(); // frame_extraction
      expect(screen.getByText('⚽')).toBeInTheDocument(); // ball_detection
      expect(screen.getAllByText('👤')).toHaveLength(2); // pose_detection stage + insight
      expect(screen.getByText('✏️')).toBeInTheDocument(); // frame_annotation
      expect(screen.getByText('🎥')).toBeInTheDocument(); // video_creation
    });
  });

  describe('with simple processing time only', () => {
    it('renders simple processing time display', () => {
      render(<TimingPerformance processingTime={15.5} />);

      expect(screen.getByText('Processing Time')).toBeInTheDocument();
      expect(screen.getAllByText('15.50s')).toHaveLength(2); // total-time and stage-duration
      expect(screen.getByText('Total Processing')).toBeInTheDocument();
      expect(screen.getByText('100%')).toBeInTheDocument();
    });

    // Note: Simple timing mode doesn't show insights, only detailed timing mode does
    it('does not show insights in simple mode', () => {
      render(<TimingPerformance processingTime={5.2} />);

      expect(
        screen.queryByText('Fast analysis processing')
      ).not.toBeInTheDocument();
      expect(
        screen.queryByText('Analysis completed in a reasonable time')
      ).not.toBeInTheDocument();
    });
  });

  describe('with no timing data', () => {
    it('renders empty state gracefully', () => {
      render(<TimingPerformance />);

      expect(screen.getByText('Processing Time')).toBeInTheDocument();
      expect(screen.getAllByText('0ms')).toHaveLength(2); // total-time and stage-duration
      expect(screen.getByText('Total Processing')).toBeInTheDocument();
      expect(screen.getByText('100%')).toBeInTheDocument();
    });
  });

  describe('time formatting', () => {
    it('formats milliseconds correctly for times under 1 second', () => {
      const shortTiming = {
        frame_extraction: 0.5,
        total_analysis: 0.5,
      };

      render(<TimingPerformance timing={shortTiming} />);

      expect(screen.getAllByText('500ms')).toHaveLength(2); // total-time and stage-duration
    });

    it('formats seconds correctly for times over 1 second', () => {
      const longTiming = {
        frame_extraction: 1.5,
        total_analysis: 1.5,
      };

      render(<TimingPerformance timing={longTiming} />);

      expect(screen.getAllByText('1.50s')).toHaveLength(2); // total-time and stage-duration
    });
  });

  describe('edge cases', () => {
    it('handles zero timing values', () => {
      const zeroTiming = {
        frame_extraction: 0,
        ball_detection: 0,
        total_analysis: 0,
      };

      render(<TimingPerformance timing={zeroTiming} />);

      expect(screen.getAllByText('0ms')).toHaveLength(3); // total-time and 2 stage-durations
      expect(screen.getAllByText('0.0%')).toHaveLength(2); // 2 stage percentages
    });

    it('handles missing timing stages gracefully', () => {
      const partialTiming = {
        frame_extraction: 2.0,
        total_analysis: 2.0,
      };

      render(<TimingPerformance timing={partialTiming} />);

      expect(screen.getByText('Frame Extraction')).toBeInTheDocument();
      expect(screen.getAllByText('2.00s')).toHaveLength(2); // total-time and stage-duration
      expect(screen.getByText('100.0%')).toBeInTheDocument();
    });

    it('handles unknown stage names', () => {
      const unknownTiming = {
        unknown_stage: 1.0,
        total_analysis: 1.0,
      };

      render(<TimingPerformance timing={unknownTiming} />);

      expect(screen.getByText('Unknown Stage')).toBeInTheDocument();
      expect(screen.getByText('⏱️')).toBeInTheDocument(); // default icon
    });
  });

  describe('component structure', () => {
    it('renders with correct CSS classes', () => {
      render(<TimingPerformance timing={mockTimingData} />);

      // Use data-testid attributes or semantic queries instead of direct DOM access
      const container = screen.getByTestId('timing-performance');
      expect(container).toBeInTheDocument();

      const header = screen.getByTestId('timing-header');
      expect(header).toBeInTheDocument();

      const breakdown = screen.getByTestId('timing-breakdown');
      expect(breakdown).toBeInTheDocument();

      const insights = screen.getByTestId('timing-insights');
      expect(insights).toBeInTheDocument();
    });
  });
});
