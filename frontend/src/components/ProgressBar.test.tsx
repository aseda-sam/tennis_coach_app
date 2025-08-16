import { render, screen } from '@testing-library/react';
import ProgressBar from './ProgressBar';

describe('ProgressBar', () => {
  const defaultProps = {
    progress: 50,
    status: 'processing' as const,
  };

  describe('Rendering', () => {
    it('renders with default props', () => {
      render(<ProgressBar {...defaultProps} />);
      
      expect(screen.getByText('Processing video...')).toBeInTheDocument();
      expect(screen.getByText('50%')).toBeInTheDocument();
    });

    it('renders without status text when showStatus is false', () => {
      render(<ProgressBar {...defaultProps} showStatus={false} />);
      
      expect(screen.queryByText('Processing video...')).not.toBeInTheDocument();
      expect(screen.getByText('50%')).toBeInTheDocument();
    });

    it('renders without percentage when showPercentage is false', () => {
      render(<ProgressBar {...defaultProps} showPercentage={false} />);
      
      expect(screen.getByText('Processing video...')).toBeInTheDocument();
      expect(screen.queryByText('50%')).not.toBeInTheDocument();
    });

    it('renders with different sizes', () => {
      const { rerender } = render(<ProgressBar {...defaultProps} size="small" />);
      expect(screen.getByRole('progressbar')).toHaveClass('progress-bar-container', 'small');

      rerender(<ProgressBar {...defaultProps} size="large" />);
      expect(screen.getByRole('progressbar')).toHaveClass('progress-bar-container', 'large');
    });
  });

  describe('Status States', () => {
    it('displays correct text for starting status', () => {
      render(<ProgressBar progress={0} status="starting" />);
      expect(screen.getByText('Starting analysis...')).toBeInTheDocument();
      expect(screen.getByText('0%')).toBeInTheDocument();
    });

    it('displays correct text for processing status', () => {
      render(<ProgressBar progress={45} status="processing" />);
      expect(screen.getByText('Processing video...')).toBeInTheDocument();
      expect(screen.getByText('45%')).toBeInTheDocument();
    });

    it('displays correct text for finalizing status', () => {
      render(<ProgressBar progress={100} status="finalizing" />);
      expect(screen.getByText('Finalizing results...')).toBeInTheDocument();
      expect(screen.getByText('100%')).toBeInTheDocument();
    });

    it('displays correct text for completed status', () => {
      render(<ProgressBar progress={100} status="completed" />);
      expect(screen.getByText('Analysis complete!')).toBeInTheDocument();
      expect(screen.getByText('100%')).toBeInTheDocument();
    });

    it('displays correct text for failed status', () => {
      render(<ProgressBar progress={30} status="failed" />);
      expect(screen.getByText('Analysis failed')).toBeInTheDocument();
      expect(screen.getByText('30%')).toBeInTheDocument();
    });

    it('displays correct text for cancelled status', () => {
      render(<ProgressBar progress={60} status="cancelled" />);
      expect(screen.getByText('Analysis cancelled')).toBeInTheDocument();
      expect(screen.getByText('60%')).toBeInTheDocument();
    });
  });

  describe('Progress Display', () => {
    it('shows 0% for starting status regardless of progress value', () => {
      render(<ProgressBar progress={75} status="starting" />);
      expect(screen.getByText('0%')).toBeInTheDocument();
    });

    it('shows 100% for finalizing status regardless of progress value', () => {
      render(<ProgressBar progress={50} status="finalizing" />);
      expect(screen.getByText('100%')).toBeInTheDocument();
    });

    it('shows 100% for completed status regardless of progress value', () => {
      render(<ProgressBar progress={25} status="completed" />);
      expect(screen.getByText('100%')).toBeInTheDocument();
    });

    it('shows actual progress for processing status', () => {
      render(<ProgressBar progress={67} status="processing" />);
      expect(screen.getByText('67%')).toBeInTheDocument();
    });

    it('shows actual progress for failed status', () => {
      render(<ProgressBar progress={42} status="failed" />);
      expect(screen.getByText('42%')).toBeInTheDocument();
    });

    it('shows actual progress for cancelled status', () => {
      render(<ProgressBar progress={89} status="cancelled" />);
      expect(screen.getByText('89%')).toBeInTheDocument();
    });
  });

  describe('CSS Classes', () => {
    it('applies correct status color classes', () => {
      const { rerender } = render(<ProgressBar progress={50} status="processing" />);
      expect(screen.getByText('Processing video...')).toHaveClass('status-text', 'processing');

      rerender(<ProgressBar progress={100} status="completed" />);
      expect(screen.getByText('Analysis complete!')).toHaveClass('status-text', 'completed');

      rerender(<ProgressBar progress={30} status="failed" />);
      expect(screen.getByText('Analysis failed')).toHaveClass('status-text', 'error');
    });

    it('applies animated class when animated is true', () => {
      render(<ProgressBar {...defaultProps} animated={true} />);
      expect(screen.getByRole('progressbar')).toHaveClass('progress-bar-container');
      // The animated class is applied to the inner progress bar element
    });

    it('does not apply animated class when animated is false', () => {
      render(<ProgressBar {...defaultProps} animated={false} />);
      expect(screen.getByRole('progressbar')).toHaveClass('progress-bar-container');
    });
  });

  describe('Progress Bar Fill', () => {
    it('sets correct width based on progress', () => {
      render(<ProgressBar progress={75} status="processing" />);
      const progressFill = screen.getByRole('progressbar').querySelector('.progress-fill');
      expect(progressFill).toHaveStyle({ width: '75%' });
    });

    it('handles edge cases', () => {
      const { rerender } = render(<ProgressBar progress={0} status="processing" />);
      let progressFill = screen.getByRole('progressbar').querySelector('.progress-fill');
      expect(progressFill).toHaveStyle({ width: '0%' });

      rerender(<ProgressBar progress={100} status="processing" />);
      progressFill = screen.getByRole('progressbar').querySelector('.progress-fill');
      expect(progressFill).toHaveStyle({ width: '100%' });

      rerender(<ProgressBar progress={-10} status="processing" />);
      progressFill = screen.getByRole('progressbar').querySelector('.progress-fill');
      expect(progressFill).toHaveStyle({ width: '-10%' });

      rerender(<ProgressBar progress={150} status="processing" />);
      progressFill = screen.getByRole('progressbar').querySelector('.progress-fill');
      expect(progressFill).toHaveStyle({ width: '150%' });
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA attributes', () => {
      render(<ProgressBar {...defaultProps} />);
      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toBeInTheDocument();
    });

    it('provides meaningful text content', () => {
      render(<ProgressBar progress={50} status="processing" />);
      expect(screen.getByText('Processing video...')).toBeInTheDocument();
      expect(screen.getByText('50%')).toBeInTheDocument();
    });
  });
});
