import { screen } from '@testing-library/react';
import { renderWithProviders } from '../test-utils';
import LoadingIndicator from './LoadingIndicator';

// The spinner ring uses aria-hidden="true", so it cannot be found via accessible
// queries. querySelector is the only way to reach it in tests.

describe('LoadingIndicator', () => {
  describe('Rendering', () => {
    it('renders with default label text', () => {
      renderWithProviders(<LoadingIndicator />);

      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('renders with custom label text', () => {
      renderWithProviders(<LoadingIndicator label="Analysing serve..." />);

      expect(screen.getByText('Analysing serve...')).toBeInTheDocument();
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });

    it('renders the spinner ring element', () => {
      renderWithProviders(<LoadingIndicator />);

      const statusContainer = screen.getByRole('status');
      const ring = statusContainer.querySelector('.tc-loading__ring');
      expect(ring).toBeInTheDocument();
    });
  });

  describe('Size Variants', () => {
    it('applies the sm size class', () => {
      renderWithProviders(<LoadingIndicator size="sm" />);

      const ring = screen
        .getByRole('status')
        .querySelector('.tc-loading__ring');
      expect(ring).toHaveClass('tc-loading__ring--sm');
    });

    it('applies the md size class by default', () => {
      renderWithProviders(<LoadingIndicator />);

      const ring = screen
        .getByRole('status')
        .querySelector('.tc-loading__ring');
      expect(ring).toHaveClass('tc-loading__ring--md');
    });

    it('applies the lg size class', () => {
      renderWithProviders(<LoadingIndicator size="lg" />);

      const ring = screen
        .getByRole('status')
        .querySelector('.tc-loading__ring');
      expect(ring).toHaveClass('tc-loading__ring--lg');
    });
  });

  describe('Tone Variants', () => {
    it('applies the default tone classes by default', () => {
      renderWithProviders(<LoadingIndicator />);

      const statusContainer = screen.getByRole('status');
      const ring = statusContainer.querySelector('.tc-loading__ring');
      const label = screen.getByText('Loading...');

      expect(ring).toHaveClass('tc-loading__ring--default');
      expect(label).toHaveClass('tc-loading__label--default');
    });

    it('applies the light tone classes', () => {
      renderWithProviders(<LoadingIndicator tone="light" />);

      const statusContainer = screen.getByRole('status');
      const ring = statusContainer.querySelector('.tc-loading__ring');
      const label = screen.getByText('Loading...');

      expect(ring).toHaveClass('tc-loading__ring--light');
      expect(label).toHaveClass('tc-loading__label--light');
    });
  });

  describe('Centered Layout', () => {
    it('applies centered class by default', () => {
      renderWithProviders(<LoadingIndicator />);

      const statusContainer = screen.getByRole('status');
      expect(statusContainer).toHaveClass('tc-loading--centered');
    });

    it('does not apply centered class when centered is false', () => {
      renderWithProviders(<LoadingIndicator centered={false} />);

      const statusContainer = screen.getByRole('status');
      expect(statusContainer).not.toHaveClass('tc-loading--centered');
    });
  });

  describe('Accessibility', () => {
    it('has role="status" on the container', () => {
      renderWithProviders(<LoadingIndicator />);

      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('has aria-live="polite" for screen reader announcements', () => {
      renderWithProviders(<LoadingIndicator />);

      const statusContainer = screen.getByRole('status');
      expect(statusContainer).toHaveAttribute('aria-live', 'polite');
    });

    it('hides the spinner ring from assistive technology', () => {
      renderWithProviders(<LoadingIndicator />);

      const ring = screen
        .getByRole('status')
        .querySelector('.tc-loading__ring');
      expect(ring).toHaveAttribute('aria-hidden', 'true');
    });

    it('exposes the label text to assistive technology', () => {
      renderWithProviders(<LoadingIndicator label="Uploading video..." />);

      const label = screen.getByText('Uploading video...');
      expect(label).toBeInTheDocument();
      expect(label).not.toHaveAttribute('aria-hidden');
    });
  });
});
