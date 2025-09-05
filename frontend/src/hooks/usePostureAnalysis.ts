import { useCallback, useState } from 'react';
import {
  ballContactApi,
  PostureAnalysisRequest,
  PostureAnalysisResponse,
} from '../services/ballContactApi';

interface UsePostureAnalysisReturn {
  // State
  isAnalyzing: boolean;
  analysisResults: Record<number, PostureAnalysisResponse>;
  error: string | null;

  // Actions
  analyzeContact: (
    contactId: number,
    forceReanalysis?: boolean
  ) => Promise<PostureAnalysisResponse>;
  analyzeVideo: (
    videoId: number,
    forceReanalysis?: boolean
  ) => Promise<PostureAnalysisResponse[]>;
  getContactAnalysis: (contactId: number) => Promise<PostureAnalysisResponse>;
  clearError: () => void;
  clearResults: () => void;
}

export const usePostureAnalysis = (): UsePostureAnalysisReturn => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResults, setAnalysisResults] = useState<
    Record<number, PostureAnalysisResponse>
  >({});
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const clearResults = useCallback(() => {
    setAnalysisResults({});
  }, []);

  const analyzeContact = useCallback(
    async (
      contactId: number,
      forceReanalysis = false
    ): Promise<PostureAnalysisResponse> => {
      try {
        setIsAnalyzing(true);
        setError(null);

        const request: PostureAnalysisRequest = {
          force_reanalysis: forceReanalysis,
        };

        const result = await ballContactApi.analyzePosture(contactId, request);

        // Store the result
        setAnalysisResults((prev) => ({
          ...prev,
          [contactId]: result,
        }));

        return result;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to analyze posture';
        setError(errorMessage);
        throw err;
      } finally {
        setIsAnalyzing(false);
      }
    },
    []
  );

  const analyzeVideo = useCallback(
    async (
      videoId: number,
      forceReanalysis = false
    ): Promise<PostureAnalysisResponse[]> => {
      try {
        setIsAnalyzing(true);
        setError(null);

        const request: PostureAnalysisRequest = {
          force_reanalysis: forceReanalysis,
        };

        const results = await ballContactApi.analyzeVideoPosture(
          videoId,
          request
        );

        // Store all results
        const resultsMap: Record<number, PostureAnalysisResponse> = {};
        results.forEach((result) => {
          resultsMap[result.ball_contact_id] = result;
        });

        setAnalysisResults((prev) => ({
          ...prev,
          ...resultsMap,
        }));

        return results;
      } catch (err) {
        const errorMessage =
          err instanceof Error
            ? err.message
            : 'Failed to analyze video posture';
        setError(errorMessage);
        throw err;
      } finally {
        setIsAnalyzing(false);
      }
    },
    []
  );

  const getContactAnalysis = useCallback(
    async (contactId: number): Promise<PostureAnalysisResponse> => {
      try {
        setError(null);
        const result = await ballContactApi.getPostureAnalysis(contactId);

        // Store the result
        setAnalysisResults((prev) => ({
          ...prev,
          [contactId]: result,
        }));

        return result;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to get posture analysis';
        setError(errorMessage);
        throw err;
      }
    },
    []
  );

  return {
    // State
    isAnalyzing,
    analysisResults,
    error,

    // Actions
    analyzeContact,
    analyzeVideo,
    getContactAnalysis,
    clearError,
    clearResults,
  };
};
