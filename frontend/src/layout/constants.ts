import type { FlowLane } from "@/types/plan";

/** Global layout spacing (px) */
export const LAYOUT = {
  marginLeft: 148,
  marginTop: 48,
  marginRight: 80,
  marginBottom: 64,
  laneGap: 56,
  nodeGapX: 80,
  nodeGapY: 48,
  parallelGapX: 96,
  parallelGapY: 40,
  parallelPad: 32,
  lanePadY: 28,
  lanePadX: 24,
  hitlExtraGap: 80,
  collisionMargin: 24,
  defaultNodeWidth: 248,
  minNodeHeight: 84,
  maxDescLines: 2,
  laneLabelWidth: 120,
};

export const LANE_ORDER: FlowLane[] = [
  "input",
  "orchestration",
  "execution",
  "merge",
  "hitl",
];

export const LANE_LABELS: Record<FlowLane, string> = {
  input: "INPUT",
  orchestration: "ORCHESTRATION",
  execution: "EXECUTION",
  merge: "MERGE & DECISION",
  hitl: "HUMAN-IN-THE-LOOP",
};

export const DEBUG_LAYOUT =
  typeof window !== "undefined" &&
  (window.location.search.includes("layoutDebug=1") ||
    window.localStorage.getItem("launchpad_layout_debug") === "1");
