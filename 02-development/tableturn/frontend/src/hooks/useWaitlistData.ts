import { useCallback, useEffect, useState } from "react";

import { getStats, listParties, listTables } from "../api/client";
import type { Party, Stats, Table } from "../api/types";

/** Spec §9: poll every 5 s so two host stands see the same data. */
export const POLL_INTERVAL_MS = 5000;

export interface WaitlistData {
  parties: Party[];
  tables: Table[];
  stats: Stats | null;
  loading: boolean;
  connectionError: string | null;
  refresh: () => Promise<void>;
}

/**
 * Loads parties, tables and stats together and keeps them fresh.
 *
 * `paused` stops the interval — the App pauses polling while the seat dialog
 * is open so the host's selection cannot vanish mid-action (AGENTS.md).
 */
export function useWaitlistData(paused = false): WaitlistData {
  const [parties, setParties] = useState<Party[]>([]);
  const [tables, setTables] = useState<Table[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [nextParties, nextTables, nextStats] = await Promise.all([
        listParties(),
        listTables(),
        getStats(),
      ]);
      setParties(nextParties);
      setTables(nextTables);
      setStats(nextStats);
      setConnectionError(null);
    } catch (error) {
      setConnectionError(error instanceof Error ? error.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (paused) return;
    const timer = setInterval(() => {
      void refresh();
    }, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [paused, refresh]);

  return { parties, tables, stats, loading, connectionError, refresh };
}
