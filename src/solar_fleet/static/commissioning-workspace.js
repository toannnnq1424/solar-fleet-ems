// One commissioning workflow; manual records never certify electrical compliance.
export function createCommissioningWorkspace(ctx) {
  return { openCommissioningWorkflow(siteId) {
    ctx.state.site = siteId;
    return ctx.go('operations', '', 'handover');
  } };
}
