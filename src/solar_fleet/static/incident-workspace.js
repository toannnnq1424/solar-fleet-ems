import { createIncidentCenter } from './incident-center.js';
// All entry points share persisted incidents, revisions, SLA and work orders.
export async function renderIncidentWorkspace(ctx) {
  return await createIncidentCenter(ctx).center();
}
