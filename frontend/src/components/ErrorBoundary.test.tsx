import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ErrorBoundary from './ErrorBoundary';
import { renderWithProviders } from '../test-utils';

// Component that throws on render to trigger the error boundary
function ThrowingComponent({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error('Test error');
  }
  return <div>Child content</div>;
}

describe('ErrorBoundary', () => {
  // Suppress console.error for error boundary tests — React logs caught errors
  const originalConsoleError = console.error;

  beforeEach(() => {
    console.error = vi.fn();
  });

  afterEach(() => {
    console.error = originalConsoleError;
  });

  describe('Rendering children', () => {
    it('renders children when no error occurs', () => {
      renderWithProviders(
        <ErrorBoundary>
          <p>Hello world</p>
        </ErrorBoundary>
      );

      expect(screen.getByText('Hello world')).toBeInTheDocument();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  });

  describe('Error fallback', () => {
    it('catches errors and shows fallback UI with default message', () => {
      renderWithProviders(
        <ErrorBoundary>
          <ThrowingComponent shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(
        screen.getByText('Something went wrong in this section.')
      ).toBeInTheDocument();
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: 'Try Again' })
      ).toBeInTheDocument();
      expect(screen.queryByText('Child content')).not.toBeInTheDocument();
    });

    it('shows custom fallback message when provided', () => {
      renderWithProviders(
        <ErrorBoundary fallbackMessage="Video analysis failed to load.">
          <ThrowingComponent shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(
        screen.getByText('Video analysis failed to load.')
      ).toBeInTheDocument();
      expect(
        screen.queryByText('Something went wrong in this section.')
      ).not.toBeInTheDocument();
    });
  });

  describe('Reset behaviour', () => {
    it('"Try Again" button resets error state and re-renders children', async () => {
      const user = userEvent.setup();

      // We need a component whose throw behavior can change between renders.
      // On first render it throws; after reset it should succeed.
      let shouldThrow = true;

      function ConditionalThrower() {
        if (shouldThrow) {
          throw new Error('Test error');
        }
        return <div>Recovered content</div>;
      }

      renderWithProviders(
        <ErrorBoundary>
          <ConditionalThrower />
        </ErrorBoundary>
      );

      // Fallback is showing
      expect(
        screen.getByText('Something went wrong in this section.')
      ).toBeInTheDocument();

      // Fix the "error" so re-render succeeds
      shouldThrow = false;

      await user.click(screen.getByRole('button', { name: 'Try Again' }));

      // Children are rendered again
      expect(screen.getByText('Recovered content')).toBeInTheDocument();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  });
});
