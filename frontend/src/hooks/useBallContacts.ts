import { useState, useEffect, useCallback, useRef } from 'react';
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
  
  // Use ref to store current contacts state to avoid stale closures
  const contactsRef = useRef<BallContact[]>([]);
  contactsRef.current = contacts;

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
          // Get the old timestamp from the current contacts state using ref
          const oldContact = contactsRef.current.find(c => c.id === contactId);
          const oldTimestamp = oldContact?.video_timestamp;
          const newTimestamp = updatedContact.video_timestamp;
          
          // Remove old timestamp and add new one
          const filtered = oldTimestamp !== undefined ? prev.filter(t => t !== oldTimestamp) : prev;
          return [...filtered, newTimestamp].sort((a, b) => a - b);
        });
      }
      
      return updatedContact;
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err?.message || 'Failed to update ball contact';
      throw new Error(errorMessage);
    }
  }, []); // No dependencies needed since we use ref

  const deleteContact = useCallback(async (contactId: number): Promise<void> => {
    try {
      await ballContactApi.deleteContact(contactId);
      
      // Get the deleted contact from current state using ref
      const deletedContact = contactsRef.current.find(c => c.id === contactId);
      
      setContacts(prev => prev.filter(contact => contact.id !== contactId));
      
      if (deletedContact) {
        setTimestamps(prev => prev.filter(t => t !== deletedContact.video_timestamp));
      }
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err?.message || 'Failed to delete ball contact';
      throw new Error(errorMessage);
    }
  }, []); // No dependencies needed since we use ref

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
