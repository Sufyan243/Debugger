import { useState, useEffect } from "react";
import {
  fetchConceptStats,
  fetchWeaknessProfile,
  fetchSessionSummary,
  fetchMetacognitive,
  ConceptStatsResponse,
  WeaknessProfileResponse,
  SessionSummaryResponse,
  MetacognitiveResponse,
} from "../api/client";

export function useDashboard(sessionId: string, ownerToken: string) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conceptStats, setConceptStats] = useState<ConceptStatsResponse | null>(null);
  const [weaknessProfile, setWeaknessProfile] = useState<WeaknessProfileResponse | null>(null);
  const [sessionSummary, setSessionSummary] = useState<SessionSummaryResponse | null>(null);
  const [metacognitive, setMetacognitive] = useState<MetacognitiveResponse | null>(null);

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const [concepts, weakness, summary, meta] = await Promise.all([
        fetchConceptStats(sessionId, ownerToken),
        fetchWeaknessProfile(sessionId, ownerToken),
        fetchSessionSummary(sessionId, ownerToken),
        fetchMetacognitive(sessionId, ownerToken).catch(() => null),
      ]);
      setConceptStats(concepts);
      setWeaknessProfile(weakness);
      setSessionSummary(summary);
      setMetacognitive(meta);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (ownerToken.length === 0) return;
    refresh();
  }, [sessionId, ownerToken]);

  return { loading, error, conceptStats, weaknessProfile, sessionSummary, metacognitive, refresh };
}
