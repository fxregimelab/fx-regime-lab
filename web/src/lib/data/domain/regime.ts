/** Latest regime call for a pair (domain shape, no DB column names). */
export interface RegimeCall {
  pair: string;
  date: string;
  regime: string;
  confidence: number | null;
  signalComposite: number | null;
  rateSignal: string | null;
  cotSignal: string | null;
  volSignal: string | null;
  rrSignal: string | null;
  oiSignal: string | null;
  primaryDriver: string | null;
  specialSignalValue: number | null;
  specialSignalLabel: string | null;
  modelVersion: string | null;
  dataQualityScore: number | null;
  stressLevel: string | null;
  createdAt: string | null;
  predictedDirection: string | null;
  entryTiming: string | null;
  positionSize: string | null;
  stopLevel: number | null;
}

/** Latest signal snapshot for a pair. */
export interface SignalSnapshot {
  pair: string;
  date: string;
  spot: number | null;
  rateDiff2y: number | null;
  cotPercentile: number | null;
  realizedVol20d: number | null;
  realizedVol5d: number | null;
  impliedVol30d: number | null;
  dayChange: number | null;
  dayChangePct: number | null;
  crossAssetUs10y: number | null;
  realizedVolRank: number | null;
  rateZTactical: number | null;
  rateZStructural: number | null;
  zBlended: number | null;
  rateDiff10yReal: number | null;
  breakevenInflation10y: number | null;
  skewAlignment: number | null;
  riskReversal25d: number | null;
  fpiFlow: number | null;
  cotNetPos: number | null;
  cotAssetMgrNet: number | null;
  cotLevMoneyNet: number | null;
  indiaVix: number | null;
  inrForwardPremium: number | null;
  oiDelta: number | null;
  volumeRvol: number | null;
  structuralInstability: boolean;
  ecbBalanceSheet: number | null;
  bundBtpSpread: number | null;
  bojPolicyRate: number | null;
  createdAt: string | null;
}
