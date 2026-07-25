import type { PageLoad } from './$types'

// Just surface the route param — the profile itself is fetched client-side (like
// every other page here), so nothing hits the API during SSR.
export const load: PageLoad = ({ params }) => ({ id: Number(params.id) })
