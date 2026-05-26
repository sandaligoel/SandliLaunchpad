import { LAYOUT } from "@/layout/constants";

export interface Bounds {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

export function boundsOverlap(a: Bounds, b: Bounds, margin = LAYOUT.collisionMargin): boolean {
  return !(
    a.x + a.width + margin <= b.x ||
    b.x + b.width + margin <= a.x ||
    a.y + a.height + margin <= b.y ||
    b.y + b.height + margin <= a.y
  );
}

/** Push colliding boxes apart (prefer vertical separation in same lane). */
export function resolveCollisions(
  boxes: Bounds[],
  margin = LAYOUT.collisionMargin,
  maxPasses = 12
): Bounds[] {
  const out = boxes.map((b) => ({ ...b }));

  for (let pass = 0; pass < maxPasses; pass++) {
    let moved = false;
    for (let i = 0; i < out.length; i++) {
      for (let j = i + 1; j < out.length; j++) {
        if (!boundsOverlap(out[i], out[j], margin)) continue;
        const a = out[i];
        const b = out[j];
        const overlapX =
          Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x) + margin;
        const overlapY =
          Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y) + margin;

        if (overlapY <= overlapX) {
          if (a.y + a.height / 2 <= b.y + b.height / 2) {
            b.y = a.y + a.height + margin;
          } else {
            a.y = b.y + b.height + margin;
          }
        } else {
          if (a.x + a.width / 2 <= b.x + b.width / 2) {
            b.x = a.x + a.width + margin;
          } else {
            a.x = b.x + b.width + margin;
          }
        }
        moved = true;
      }
    }
    if (!moved) break;
  }
  return out;
}

export function logCollisionReport(boxes: Bounds[]): void {
  let hits = 0;
  for (let i = 0; i < boxes.length; i++) {
    for (let j = i + 1; j < boxes.length; j++) {
      if (boundsOverlap(boxes[i], boxes[j], 12)) {
        hits++;
        console.warn("[layout] overlap", boxes[i].id, boxes[j].id);
      }
    }
  }
  console.info("[layout] collision check", { nodes: boxes.length, overlaps: hits });
}
