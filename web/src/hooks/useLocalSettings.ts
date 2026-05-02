'use client';

import { useCallback, useEffect, useState } from 'react';

/** Persisted chart range (GTM vault / Open Vault). */
export type ChartRange = '1M' | '1Y' | 'MAX';

export type LocalSettings = {
  selectedPair: string;
  chartRange: ChartRange;
  sidebarExpanded: boolean;
};

export const FX_VAULT_STORAGE_KEY = 'fx_regime_lab_local_settings_v1';
export const FX_VAULT_IMPORT_EVENT = 'fx-regime-vault-imported';
/** Fired after a successful vault import write (UI pulse on import control). */
export const FX_VAULT_STATUS_SUCCESS = 'fx-regime-vault-status-success';

const DEFAULT_SETTINGS: LocalSettings = {
  selectedPair: 'EURUSD',
  chartRange: '1Y',
  sidebarExpanded: false,
};

function parseStored(raw: string | null): LocalSettings {
  if (!raw) return { ...DEFAULT_SETTINGS };
  try {
    const p = JSON.parse(raw) as Partial<LocalSettings>;
    const chartRange =
      p.chartRange === '1M' || p.chartRange === '1Y' || p.chartRange === 'MAX'
        ? p.chartRange
        : DEFAULT_SETTINGS.chartRange;
    return {
      selectedPair: typeof p.selectedPair === 'string' && p.selectedPair ? p.selectedPair : DEFAULT_SETTINGS.selectedPair,
      chartRange,
      sidebarExpanded: typeof p.sidebarExpanded === 'boolean' ? p.sidebarExpanded : DEFAULT_SETTINGS.sidebarExpanded,
    };
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

function readFromStorage(): LocalSettings {
  if (typeof window === 'undefined') return { ...DEFAULT_SETTINGS };
  return parseStored(localStorage.getItem(FX_VAULT_STORAGE_KEY));
}

function writeToStorage(next: LocalSettings) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(FX_VAULT_STORAGE_KEY, JSON.stringify(next));
}

/**
 * Terminal preferences synced to localStorage. `hydrated` is false on first SSR paint;
 * read settings only after hydrated to avoid hydration mismatches.
 */
export function useLocalSettings() {
  const [settings, setSettingsState] = useState<LocalSettings>(DEFAULT_SETTINGS);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setSettingsState(readFromStorage());
    setHydrated(true);

    const onImport = () => setSettingsState(readFromStorage());
    window.addEventListener(FX_VAULT_IMPORT_EVENT, onImport);
    return () => window.removeEventListener(FX_VAULT_IMPORT_EVENT, onImport);
  }, []);

  const setSettings = useCallback((patch: Partial<LocalSettings>) => {
    setSettingsState((prev) => {
      const next = { ...prev, ...patch };
      writeToStorage(next);
      return next;
    });
  }, []);

  return { ...settings, setSettings, hydrated };
}

export type VaultExportFile = {
  version: number;
  exportedAt: string;
  settings: LocalSettings;
};

export function buildVaultExportJson(): string {
  const settings = readFromStorage();
  const payload: VaultExportFile = {
    version: 1,
    exportedAt: new Date().toISOString(),
    settings,
  };
  return JSON.stringify(payload, null, 2);
}

/** Apply imported vault file; dispatches import event so hooks reload. */
export function applyVaultImportJson(text: string): { ok: true } | { ok: false; error: string } {
  try {
    const data = JSON.parse(text) as Partial<VaultExportFile> & Partial<LocalSettings>;
    const settingsRaw =
      data.settings && typeof data.settings === 'object'
        ? data.settings
        : {
            selectedPair: data.selectedPair,
            chartRange: data.chartRange,
            sidebarExpanded: data.sidebarExpanded,
          };
    const merged = parseStored(JSON.stringify(settingsRaw));
    writeToStorage(merged);
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new Event(FX_VAULT_IMPORT_EVENT));
      window.dispatchEvent(new Event(FX_VAULT_STATUS_SUCCESS));
    }
    return { ok: true };
  } catch {
    return { ok: false, error: 'Invalid vault file' };
  }
}
