import type { ArchitecturePlan } from "@/api/affine/types";
import type { AgentDef } from "@/types/api";
import { buildStepDetailView } from "@/utils/stepIo";
import { computeFlowOrder } from "@/utils/flowOrder";
import { EditableStringList } from "./EditableStringList";

interface Props {
  plan: ArchitecturePlan;
  nodeId: string;
  catalogAgents: AgentDef[];
  flowOrder?: string[];
  onChange: (patch: {
    inputs?: string[];
    outputs?: string[];
    description?: string;
  }) => void;
  disabled?: boolean;
}

export function StepIoEditor({
  plan,
  nodeId,
  catalogAgents,
  flowOrder: flowOrderProp,
  onChange,
  disabled = false,
}: Props) {
  const flowOrder = flowOrderProp ?? computeFlowOrder(plan.graph);
  const view = buildStepDetailView(plan, nodeId, catalogAgents, flowOrder);
  const node = plan.graph.nodes.find((n) => n.id === nodeId);
  const decision = plan.reuse_decisions.find((d) => d.node_id === nodeId);
  const agentLabel = decision?.agent_name ?? node?.label;

  return (
    <div className="space-y-3 pt-1 border-t border-border">
      <div>
        <label className="text-[11px] text-muted-foreground block mb-1">
          What this step does
        </label>
        <textarea
          rows={4}
          disabled={disabled}
          className="w-full text-sm rounded-md border border-border bg-background px-2.5 py-2 outline-none focus:ring-2 ring-primary/30 disabled:opacity-50"
          placeholder="Describe how this node works in your workflow…"
          value={view.description}
          onChange={(e) => onChange({ description: e.target.value })}
        />
        {view.descriptionFromCatalog && agentLabel ? (
          <p className="text-[10px] text-muted-foreground mt-1">
            Based on catalog agent: {agentLabel}
          </p>
        ) : null}
      </div>

      <div>
        <h4 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          Inputs &amp; outputs
        </h4>
        {view.inputsFromCatalog && agentLabel ? (
          <p className="text-[10.5px] text-muted-foreground mt-0.5">
            Inputs from catalog spec ({agentLabel}
            {view.inputsFromPrevious ? (
              <>
                ); upstream data from{" "}
                <span className="font-medium text-foreground">
                  {view.inputsFromPrevious}
                </span>
              </>
            ) : (
              <>)</>
            )}
            .
          </p>
        ) : view.inputsFromPrevious ? (
          <p className="text-[10.5px] text-muted-foreground mt-0.5">
            Inputs flow from previous step:{" "}
            <span className="font-medium text-foreground">
              {view.inputsFromPrevious}
            </span>
          </p>
        ) : (
          <p className="text-[10.5px] text-muted-foreground mt-0.5">
            First step — entry inputs from the workflow trigger.
          </p>
        )}
        {view.outputsFromCatalog && agentLabel ? (
          <p className="text-[10.5px] text-muted-foreground">
            Outputs from catalog agent:{" "}
            <span className="font-medium text-foreground">{agentLabel}</span>
          </p>
        ) : view.outputsInferred ? (
          <p className="text-[10.5px] text-amber-700/90">
            Outputs suggested from step type and upstream inputs — edit to match
            your workflow.
          </p>
        ) : null}
      </div>

      <EditableStringList
        label={
          view.inputsFromCatalog
            ? "Inputs (from catalog spec)"
            : "Inputs (from previous step)"
        }
        items={view.inputs}
        placeholder="Add input for this step"
        disabled={disabled}
        onChange={(inputs) => onChange({ inputs })}
      />
      <EditableStringList
        label="Outputs (from this agent)"
        items={view.outputs}
        placeholder="Add output this step produces"
        disabled={disabled}
        onChange={(outputs) => onChange({ outputs })}
      />
    </div>
  );
}
