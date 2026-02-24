import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import { renderWithProviders } from '../test-utils';
import { AuthForm } from './AuthForm';

// Mock useAuth hook
const mockSignIn = jest.fn();
const mockSignUp = jest.fn();
const mockSignInWithMagicLink = jest.fn();
const mockResendConfirmationEmail = jest.fn();

jest.mock('../hooks/useAuth', () => ({
  useAuth: () => ({
    user: null,
    session: null,
    loading: false,
    signIn: mockSignIn,
    signUp: mockSignUp,
    signInWithMagicLink: mockSignInWithMagicLink,
    signOut: jest.fn(),
    resendConfirmationEmail: mockResendConfirmationEmail,
    updateUserMetadata: jest.fn(),
  }),
}));

jest.mock('../services/playerApi', () => ({
  playerApi: {
    upsertMe: jest.fn().mockResolvedValue({}),
  },
}));

describe('AuthForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSignIn.mockResolvedValue({
      data: { user: null, session: null },
      error: null,
    });
    mockSignUp.mockResolvedValue({
      data: { user: null, session: null },
      error: null,
    });
    mockSignInWithMagicLink.mockResolvedValue({ data: null, error: null });
    mockResendConfirmationEmail.mockResolvedValue({ data: null, error: null });
    // Clear any URL hash
    window.history.replaceState(null, '', window.location.pathname);
    localStorage.clear();
  });

  describe('Login form (default)', () => {
    it('renders login form by default', () => {
      renderWithProviders(<AuthForm />);

      expect(screen.getByText('Welcome back')).toBeInTheDocument();
      expect(
        screen.getByText('Sign in to continue to Second Serve')
      ).toBeInTheDocument();
    });

    it('shows email and password fields', () => {
      renderWithProviders(<AuthForm />);

      expect(screen.getByPlaceholderText('Email')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Password')).toBeInTheDocument();
    });

    it('shows sign in button', () => {
      renderWithProviders(<AuthForm />);

      expect(
        screen.getByRole('button', { name: 'Sign in' })
      ).toBeInTheDocument();
    });

    it('shows link to switch to signup', () => {
      renderWithProviders(<AuthForm />);

      expect(
        screen.getByRole('button', { name: 'Need an account? Register' })
      ).toBeInTheDocument();
    });

    it('calls signIn on form submission', async () => {
      const user = userEvent.setup();
      mockSignIn.mockResolvedValue({
        data: { user: { id: '1' }, session: { access_token: 'tok' } },
        error: null,
      });

      renderWithProviders(<AuthForm />);

      await user.type(screen.getByPlaceholderText('Email'), 'test@example.com');
      await user.type(screen.getByPlaceholderText('Password'), 'password123');
      await user.click(screen.getByRole('button', { name: 'Sign in' }));

      await waitFor(() => {
        expect(mockSignIn).toHaveBeenCalledWith(
          'test@example.com',
          'password123'
        );
      });
    });

    it('shows error message when sign in fails', async () => {
      const user = userEvent.setup();
      mockSignIn.mockResolvedValue({
        data: null,
        error: { message: 'Invalid login credentials' },
      });

      renderWithProviders(<AuthForm />);

      await user.type(screen.getByPlaceholderText('Email'), 'test@example.com');
      await user.type(screen.getByPlaceholderText('Password'), 'wrong');
      await user.click(screen.getByRole('button', { name: 'Sign in' }));

      await waitFor(() => {
        expect(
          screen.getByText('Invalid login credentials')
        ).toBeInTheDocument();
      });
    });
  });

  describe('Toggle between login and signup', () => {
    it('switches to signup form when register link is clicked', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuthForm />);

      await user.click(
        screen.getByRole('button', { name: 'Need an account? Register' })
      );

      expect(screen.getByText('Create your account')).toBeInTheDocument();
      expect(
        screen.getByText('Join Second Serve to analyze your serve')
      ).toBeInTheDocument();
    });

    it('switches back to login form from signup', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuthForm />);

      // Switch to signup
      await user.click(
        screen.getByRole('button', { name: 'Need an account? Register' })
      );
      expect(screen.getByText('Create your account')).toBeInTheDocument();

      // Switch back to login
      await user.click(
        screen.getByRole('button', { name: 'Have an account? Sign in' })
      );
      expect(screen.getByText('Welcome back')).toBeInTheDocument();
    });

    it('clears error when switching modes', async () => {
      const user = userEvent.setup();
      mockSignIn.mockResolvedValue({
        data: null,
        error: { message: 'Invalid login credentials' },
      });

      renderWithProviders(<AuthForm />);

      // Trigger an error on login
      await user.type(screen.getByPlaceholderText('Email'), 'test@example.com');
      await user.type(screen.getByPlaceholderText('Password'), 'wrong');
      await user.click(screen.getByRole('button', { name: 'Sign in' }));

      await waitFor(() => {
        expect(
          screen.getByText('Invalid login credentials')
        ).toBeInTheDocument();
      });

      // Switch to signup - error should be cleared
      await user.click(
        screen.getByRole('button', { name: 'Need an account? Register' })
      );

      expect(
        screen.queryByText('Invalid login credentials')
      ).not.toBeInTheDocument();
    });
  });

  describe('Signup form', () => {
    it('renders signup form fields', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuthForm />);

      await user.click(
        screen.getByRole('button', { name: 'Need an account? Register' })
      );

      expect(screen.getByPlaceholderText('Email')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Password')).toBeInTheDocument();
      expect(
        screen.getByPlaceholderText('Player name (e.g., Alex)')
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: 'Create account' })
      ).toBeInTheDocument();
    });

    it('shows dominant hand and backhand style selects', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuthForm />);

      await user.click(
        screen.getByRole('button', { name: 'Need an account? Register' })
      );

      expect(screen.getByDisplayValue('Right-handed')).toBeInTheDocument();
      expect(
        screen.getByDisplayValue('Backhand style (optional)')
      ).toBeInTheDocument();
    });

    it('calls signUp on form submission', async () => {
      const user = userEvent.setup();
      mockSignUp.mockResolvedValue({
        data: { user: { id: '1' }, session: null },
        error: null,
      });

      renderWithProviders(<AuthForm />);

      await user.click(
        screen.getByRole('button', { name: 'Need an account? Register' })
      );

      await user.type(screen.getByPlaceholderText('Email'), 'new@example.com');
      await user.type(screen.getByPlaceholderText('Password'), 'securepass');
      await user.type(
        screen.getByPlaceholderText('Player name (e.g., Alex)'),
        'Alex'
      );
      await user.click(screen.getByRole('button', { name: 'Create account' }));

      await waitFor(() => {
        expect(mockSignUp).toHaveBeenCalledWith(
          'new@example.com',
          'securepass'
        );
      });
    });

    it('shows error when signup fails', async () => {
      const user = userEvent.setup();
      mockSignUp.mockResolvedValue({
        data: null,
        error: { message: 'User already registered' },
      });

      renderWithProviders(<AuthForm />);

      await user.click(
        screen.getByRole('button', { name: 'Need an account? Register' })
      );

      await user.type(screen.getByPlaceholderText('Email'), 'dup@example.com');
      await user.type(screen.getByPlaceholderText('Password'), 'securepass');
      await user.type(
        screen.getByPlaceholderText('Player name (e.g., Alex)'),
        'Alex'
      );
      await user.click(screen.getByRole('button', { name: 'Create account' }));

      await waitFor(() => {
        expect(screen.getByText('User already registered')).toBeInTheDocument();
      });
    });

    it('shows success message and resend link after signup with email confirmation', async () => {
      const user = userEvent.setup();
      mockSignUp.mockResolvedValue({
        data: { user: { id: '1' }, session: null },
        error: null,
      });

      renderWithProviders(<AuthForm />);

      await user.click(
        screen.getByRole('button', { name: 'Need an account? Register' })
      );

      await user.type(screen.getByPlaceholderText('Email'), 'new@example.com');
      await user.type(screen.getByPlaceholderText('Password'), 'securepass');
      await user.type(
        screen.getByPlaceholderText('Player name (e.g., Alex)'),
        'Alex'
      );
      await user.click(screen.getByRole('button', { name: 'Create account' }));

      await waitFor(() => {
        expect(
          screen.getByText(
            'Please check your email to confirm your account before logging in.'
          )
        ).toBeInTheDocument();
      });

      expect(
        screen.getByRole('button', { name: 'Resend confirmation email' })
      ).toBeInTheDocument();
    });
  });

  describe('Magic link login', () => {
    it('switches to magic link mode and hides password field', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuthForm />);

      await user.click(
        screen.getByRole('button', { name: 'Use magic link instead' })
      );

      expect(screen.getByPlaceholderText('Email')).toBeInTheDocument();
      expect(screen.queryByPlaceholderText('Password')).not.toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: 'Send magic link' })
      ).toBeInTheDocument();
    });

    it('calls signInWithMagicLink on submission', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuthForm />);

      await user.click(
        screen.getByRole('button', { name: 'Use magic link instead' })
      );

      await user.type(
        screen.getByPlaceholderText('Email'),
        'magic@example.com'
      );
      await user.click(screen.getByRole('button', { name: 'Send magic link' }));

      await waitFor(() => {
        expect(mockSignInWithMagicLink).toHaveBeenCalledWith(
          'magic@example.com'
        );
      });
    });

    it('shows success message after magic link sent', async () => {
      const user = userEvent.setup();
      mockSignInWithMagicLink.mockResolvedValue({ data: null, error: null });

      renderWithProviders(<AuthForm />);

      await user.click(
        screen.getByRole('button', { name: 'Use magic link instead' })
      );

      await user.type(
        screen.getByPlaceholderText('Email'),
        'magic@example.com'
      );
      await user.click(screen.getByRole('button', { name: 'Send magic link' }));

      await waitFor(() => {
        expect(
          screen.getByText('Magic link sent. Check your email to sign in.')
        ).toBeInTheDocument();
      });
    });

    it('toggles back to password mode', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuthForm />);

      await user.click(
        screen.getByRole('button', { name: 'Use magic link instead' })
      );
      expect(screen.queryByPlaceholderText('Password')).not.toBeInTheDocument();

      await user.click(
        screen.getByRole('button', { name: 'Use password instead' })
      );
      expect(screen.getByPlaceholderText('Password')).toBeInTheDocument();
    });
  });

  describe('Loading state', () => {
    it('shows loading text and disables form during submission', async () => {
      const user = userEvent.setup();
      // Make signIn hang so we can check loading state
      let resolveSignIn: (value: unknown) => void;
      mockSignIn.mockImplementation(
        () =>
          new Promise((resolve) => {
            resolveSignIn = resolve;
          })
      );

      renderWithProviders(<AuthForm />);

      await user.type(screen.getByPlaceholderText('Email'), 'test@example.com');
      await user.type(screen.getByPlaceholderText('Password'), 'password123');
      await user.click(screen.getByRole('button', { name: 'Sign in' }));

      await waitFor(() => {
        expect(
          screen.getByRole('button', { name: 'Loading...' })
        ).toBeInTheDocument();
      });

      expect(screen.getByRole('button', { name: 'Loading...' })).toBeDisabled();
      expect(screen.getByPlaceholderText('Email')).toBeDisabled();
      expect(screen.getByPlaceholderText('Password')).toBeDisabled();

      // Resolve to clean up
      resolveSignIn!({ data: null, error: null });
    });
  });

  describe('Email confirmation from URL', () => {
    it('shows confirmation success when URL hash has type=signup', () => {
      // Set hash before render
      window.location.hash = '#type=signup';

      renderWithProviders(<AuthForm />);

      expect(
        screen.getByText('Email confirmed! You can now log in.')
      ).toBeInTheDocument();

      // Clean up
      window.location.hash = '';
    });
  });
});
