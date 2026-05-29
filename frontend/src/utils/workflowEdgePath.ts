/**
 * Rounded orthogonal paths for left→right pipeline layouts (enterprise flowchart style).
 */
export function getWorkflowEdgePath(params: {
  sourceX: number;
  sourceY: number;
  targetX: number;
  targetY: number;
  borderRadius?: number;
  laneGap?: number;
  spread?: number;
}): [path: string, labelX: number, labelY: number] {
  const {
    sourceX,
    sourceY,
    targetX,
    targetY,
    borderRadius = 22,
    laneGap = 36,
    spread = 0,
  } = params;

  const sy = sourceY + spread * 36;
  const ty = targetY + spread * 36;
  const dx = targetX - sourceX;
  const dy = ty - sy;
  const absDy = Math.abs(dy);

  if (dx <= laneGap * 2) {
    const path = `M ${sourceX} ${sy} L ${targetX} ${ty}`;
    return [path, (sourceX + targetX) / 2, (sy + ty) / 2];
  }

  const centerX = sourceX + Math.max(laneGap, dx * 0.46);
  const r = Math.min(borderRadius, absDy / 2, (centerX - sourceX) / 2, dx / 4);

  if (absDy < 4) {
    const path = `M ${sourceX} ${sy} L ${targetX} ${ty}`;
    return [path, (sourceX + targetX) / 2, sy];
  }

  const dir = dy > 0 ? 1 : -1;
  const path = [
    `M ${sourceX} ${sy}`,
    `L ${centerX - r} ${sy}`,
    `Q ${centerX} ${sy} ${centerX} ${sy + r * dir}`,
    `L ${centerX} ${ty - r * dir}`,
    `Q ${centerX} ${ty} ${centerX + r} ${ty}`,
    `L ${targetX} ${ty}`,
  ].join(" ");

  return [path, centerX, (sy + ty) / 2];
}

export function workflowEdgeGradientId(edgeId: string): string {
  return `wf-edge-grad-${edgeId.replace(/[^a-zA-Z0-9_-]/g, "_")}`;
}
