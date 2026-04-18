export type StrategyStatus = 'live' | 'beta' | 'deprecated';

export interface Strategy {
  id: string;
  name: string;
  asset_class: string;
  live_since: string;
  status: StrategyStatus;
}
