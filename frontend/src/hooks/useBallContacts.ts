import { useCallback, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ballContactApi, BallContact, BallContactCreate, BallContactUpdate } from '../services/ballContactApi';

interface UseBallContactsOptions {
  videoId: number;
  autoRefresh?: boolean;
  onContactsLoaded?: (contacts: BallContact[]) => void;
  onError?: (error: string) => void;
}

interface UseBallContactsResult {
  contacts: BallContact[];
  timestamps: number[];
  loading: boolean;
  error: string | null;
  refreshContacts: () => Promise<void>;
  createContact: (contact: BallContactCreate) => Promise<BallContact>;
  updateContact: (contactId: number, updates: BallContactUpdate) => Promise<BallContact>;
  deleteContact: (contactId: number) => Promise<void>;
}

export const useBallContacts = ({
  videoId,
  autoRefresh = true,
  onContactsLoaded,
  onError,
}: UseBallContactsOptions): UseBallContactsResult => {
  const queryClient = useQueryClient();

  // Fetch contacts using React Query
  const contactsQuery = useQuery<BallContact[]>({
    queryKey: ['ball-contacts', videoId],
    queryFn: async () => {
      if (!videoId) return [];
      return await ballContactApi.getContacts(videoId);
    },
    enabled: !!videoId && autoRefresh,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  // Fetch timestamps using React Query
  const timestampsQuery = useQuery<number[]>({
    queryKey: ['ball-contacts-timestamps', videoId],
    queryFn: async () => {
      if (!videoId) return [];
      return await ballContactApi.getContactTimestamps(videoId);
    },
    enabled: !!videoId && autoRefresh,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  // Call onContactsLoaded callback when contacts are loaded
  useEffect(() => {
    if (contactsQuery.data && onContactsLoaded) {
      onContactsLoaded(contactsQuery.data);
    }
  }, [contactsQuery.data, onContactsLoaded]);

  // Call onError callback when there's an error
  useEffect(() => {
    if (contactsQuery.error && onError) {
      const axiosError = contactsQuery.error as { response?: { data?: { detail?: string } }; message?: string };
      const errorMessage = axiosError?.response?.data?.detail || axiosError?.message || 'Failed to load ball contacts';
      onError(errorMessage);
    }
  }, [contactsQuery.error, onError]);

  // Create contact mutation
  const createMutation = useMutation({
    mutationFn: (contact: BallContactCreate) => ballContactApi.createContact(contact),
    onSuccess: (newContact) => {
      // Invalidate and refetch contacts and timestamps
      queryClient.invalidateQueries({ queryKey: ['ball-contacts', videoId] });
      queryClient.invalidateQueries({ queryKey: ['ball-contacts-timestamps', videoId] });
    },
  });

  // Update contact mutation
  const updateMutation = useMutation({
    mutationFn: ({ contactId, updates }: { contactId: number; updates: BallContactUpdate }) =>
      ballContactApi.updateContact(contactId, updates),
    onSuccess: () => {
      // Invalidate and refetch contacts and timestamps
      queryClient.invalidateQueries({ queryKey: ['ball-contacts', videoId] });
      queryClient.invalidateQueries({ queryKey: ['ball-contacts-timestamps', videoId] });
    },
  });

  // Delete contact mutation
  const deleteMutation = useMutation({
    mutationFn: (contactId: number) => ballContactApi.deleteContact(contactId),
    onSuccess: () => {
      // Invalidate and refetch contacts and timestamps
      queryClient.invalidateQueries({ queryKey: ['ball-contacts', videoId] });
      queryClient.invalidateQueries({ queryKey: ['ball-contacts-timestamps', videoId] });
    },
  });

  const refreshContacts = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ['ball-contacts', videoId] });
    await queryClient.invalidateQueries({ queryKey: ['ball-contacts-timestamps', videoId] });
  }, [queryClient, videoId]);

  const createContact = useCallback(
    async (contact: BallContactCreate): Promise<BallContact> => {
      try {
        return await createMutation.mutateAsync(contact);
      } catch (err: unknown) {
        const axiosError = err as { response?: { data?: { detail?: string } }; message?: string };
        const errorMessage = axiosError?.response?.data?.detail || axiosError?.message || 'Failed to create ball contact';
        throw new Error(errorMessage);
      }
    },
    [createMutation]
  );

  const updateContact = useCallback(
    async (contactId: number, updates: BallContactUpdate): Promise<BallContact> => {
      try {
        return await updateMutation.mutateAsync({ contactId, updates });
      } catch (err: unknown) {
        const axiosError = err as { response?: { data?: { detail?: string } }; message?: string };
        const errorMessage = axiosError?.response?.data?.detail || axiosError?.message || 'Failed to update ball contact';
        throw new Error(errorMessage);
      }
    },
    [updateMutation]
  );

  const deleteContact = useCallback(
    async (contactId: number): Promise<void> => {
      try {
        await deleteMutation.mutateAsync(contactId);
      } catch (err: unknown) {
        const axiosError = err as { response?: { data?: { detail?: string } }; message?: string };
        const errorMessage = axiosError?.response?.data?.detail || axiosError?.message || 'Failed to delete ball contact';
        throw new Error(errorMessage);
      }
    },
    [deleteMutation]
  );

  // Combine loading states
  const loading = contactsQuery.isLoading || timestampsQuery.isLoading;

  // Combine error states
  const error = contactsQuery.error || timestampsQuery.error
    ? (() => {
        const err = contactsQuery.error || timestampsQuery.error;
        const axiosError = err as { response?: { data?: { detail?: string } }; message?: string };
        return axiosError?.response?.data?.detail || axiosError?.message || 'Failed to load ball contacts';
      })()
    : null;

  return {
    contacts: contactsQuery.data || [],
    timestamps: timestampsQuery.data || [],
    loading,
    error,
    refreshContacts,
    createContact,
    updateContact,
    deleteContact,
  };
};
