"use client";

import { useState } from "react";
import { SignalInspector } from "./signal-inspector";

interface RegimeInspectorTriggerProps {
  pairLabel: string;
  pairColor?: string;
  regime: string | null;
  confidence: number | null;
  signalComposite: number | null;
  rateSignal: string | null;
  cotSignal: string | null;
  volSignal: string | null;
  rrSignal: string | null;
  oiSignal: string | null;
  primaryDriver: string | null;
  spot: number | null;
  rateDiff2y: number | null;
  rateDiff10y: number | null;
  rateZTactical: number | null;
  rateZStructural: number | null;
  zBlended?: number | null;
  realizedVol20d: number | null;
  realizedVol5d: number | null;
  impliedVol30d: number | null;
  dayChangePct: number | null;
  crossAssetUs10y: number | null;
  skewAlignment: number | null;
  breakevenInflation10y: number | null;
  children: React.ReactNode;
}

/** Client wrapper that manages SignalInspector drawer state.
 *  Wraps any clickable element that should open the inspector.
 */
export function RegimeInspectorTrigger({
  pairLabel,
  pairColor,
  regime,
  confidence,
  signalComposite,
  rateSignal,
  cotSignal,
  volSignal,
  rrSignal,
  oiSignal,
  primaryDriver,
  spot,
  rateDiff2y,
  rateDiff10y,
  rateZTactical,
  rateZStructural,
  zBlended,
  realizedVol20d,
  realizedVol5d,
  impliedVol30d,
  dayChangePct,
  crossAssetUs10y,
  skewAlignment,
  breakevenInflation10y,
  children,
}: RegimeInspectorTriggerProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-left w-full cursor-pointer group"
        aria-label={`Inspect ${pairLabel} signals`}
      >
        {children}
      </button>
      <SignalInspector
        open={open}
        onClose={() => setOpen(false)}
        pairLabel={pairLabel}
        pairColor={pairColor}
        regime={regime}
        confidence={confidence}
        signalComposite={signalComposite}
        rateSignal={rateSignal}
        cotSignal={cotSignal}
        volSignal={volSignal}
        rrSignal={rrSignal}
        oiSignal={oiSignal}
        primaryDriver={primaryDriver}
        spot={spot}
        rateDiff2y={rateDiff2y}
        rateDiff10y={rateDiff10y}
        rateZTactical={rateZTactical}
        rateZStructural={rateZStructural}
        zBlended={zBlended}
        realizedVol20d={realizedVol20d}
        realizedVol5d={realizedVol5d}
        impliedVol30d={impliedVol30d}
        dayChangePct={dayChangePct}
        crossAssetUs10y={crossAssetUs10y}
        skewAlignment={skewAlignment}
        breakevenInflation10y={breakevenInflation10y}
      />
    </>
  );
}
