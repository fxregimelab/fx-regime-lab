/** Shell app paths — single source for links (no scattered string literals). */
export const ROUTES = {
  home: '/',
  brief: '/brief',
  performance: '/performance',
  about: '/about',
  /** Shell research nav entry (not under `(terminal)` segment). */
  fxRegime: '/fx-regime',
} as const;

/** Named path constants (plan aliases). */
export const HOME = ROUTES.home;
export const BRIEF = ROUTES.brief;
export const PERFORMANCE = ROUTES.performance;
export const ABOUT = ROUTES.about;
