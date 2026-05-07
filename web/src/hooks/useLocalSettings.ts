"use client";

import { useState, useEffect, useCallback } from "react";

export interface LocalSettings {
  [key: string]: string | number | boolean;
}

function readSettings(): LocalSettings {
  try {
    const raw = localStorage.getItem("fxrl-settings");
    return raw ? (JSON.parse(raw) as LocalSettings) : {};
  } catch {
    return {};
  }
}

function writeSettings(settings: LocalSettings) {
  try {
    localStorage.setItem("fxrl-settings", JSON.stringify(settings));
  } catch {
    // ignore
  }
}

export function useLocalSettings() {
  const [settings, setSettingsState] = useState<LocalSettings>({});

  useEffect(() => {
    setSettingsState(readSettings());
  }, []);

  const setSetting = useCallback((key: string, value: string | number | boolean) => {
    setSettingsState((prev) => {
      const next = { ...prev, [key]: value };
      writeSettings(next);
      return next;
    });
  }, []);

  const removeSetting = useCallback((key: string) => {
    setSettingsState((prev) => {
      const next = { ...prev };
      delete next[key];
      writeSettings(next);
      return next;
    });
  }, []);

  const getSetting = useCallback(
    (key: string, fallback?: string | number | boolean) => {
      return settings[key] ?? fallback;
    },
    [settings]
  );

  return { settings, setSetting, removeSetting, getSetting };
}

export default useLocalSettings;
