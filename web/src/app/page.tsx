import { SubstackFeed } from '@/components/SubstackFeed';
import { HomeGatewayShell } from '@/components/gateway/home-gateway-shell';
import { getGatewayLandingData } from '@/lib/queries';

/** Align gateway SSR payload cache with Substack feed (1h). */
export const revalidate = 3600;

export default async function Home() {
  const initial = await getGatewayLandingData();
  return (
    <HomeGatewayShell initial={initial}>
      <SubstackFeed />
    </HomeGatewayShell>
  );
}
