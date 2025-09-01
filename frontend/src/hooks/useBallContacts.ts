import { useState, useEffect, useCallback } from 'react';
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
  const [contacts, setContacts] = useState<BallContact[]>([]);
  const [timestamps, setTimestamps] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadContacts = useCallback(async () => {
    if (!videoId) return;

    try {
      setLoading(true);
      setError(null);

      // Load both contacts and timestamps in parallel
      const [contactsData, timestampsData] = await Promise.all([
        ballContactApi.getContacts(videoId),
        ballContactApi.getContactTimestamps(videoId),
      ]);

      setContacts(contactsData);
      setTimestamps(timestampsData);

      if (onContactsLoaded) {
        onContactsLoaded(contactsData);
      }
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err?.message || 'Failed to load ball contacts';
      setError(errorMessage);
      if (onError) {
        onError(errorMessage);
      }
      console.error('Error loading ball contacts:', err);
    } finally {
      setLoading(false);
    }
  }, [videoId, onContactsLoaded, onError]);

  const refreshContacts = useCallback(async () => {
    await loadContacts();
  }, [loadContacts]);

  const createContact = useCallback(async (contact: BallContactCreate): Promise<BallContact> => {
    try {
      const newContact = await ballContactApi.createContact(contact);
      setContacts(prev => [...prev, newContact]);
      setTimestamps(prev => [...prev, newContact.video_timestamp].sort((a, b) => a - b));
      return newContact;
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err?.message || 'Failed to create ball contact';
      throw new Error(errorMessage);
    }
  }, []);

  const updateContact = useCallback(async (contactId: number, updates: BallContactUpdate): Promise<BallContact> => {
    try {
      const updatedContact = await ballContactApi.updateContact(contactId, updates);
      setContacts(prev => prev.map(contact => 
        contact.id === contactId ? updatedContact : contact
      ));
      
      // Update timestamps if video_timestamp changed
      if (updates.video_timestamp !== undefined) {
        setTimestamps(prev => {
          const filtered = prev.filter(t => t !== contacts.find(c => c.id === contactId)?.video_timestamp);
          return [...filtered, updatedContact.video_timestamp].sort((a, b) => a - b);
        });
      }
      
      return updatedContact;
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err?.message || 'Failed to update ball contact';
      throw new Error(errorMessage);
    }
  }, [contacts]);

  const deleteContact = useCallback(async (contactId: number): Promise<void> => {
    try {
      await ballContactApi.deleteContact(contactId);
      const deletedContact = contacts.find(c => c.id === contactId);
      setContacts(prev => prev.filter(contact => contact.id !== contactId));
      
      if (deletedContact) {
        setTimestamps(prev => prev.filter(t => t !== deletedContact.video_timestamp));
      }
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err?.message || 'Failed to delete ball contact';
      throw new Error(errorMessage);
    }
  }, [contacts]);

  // Load contacts when videoId changes
  useEffect(() => {
    if (autoRefresh) {
      loadContacts();
    }
  }, [videoId, autoRefresh, loadContacts]);

  return {
    contacts,
    timestamps,
    loading,
    error,
    refreshContacts,
    createContact,
    updateContact,
    deleteContact,
  };
};
