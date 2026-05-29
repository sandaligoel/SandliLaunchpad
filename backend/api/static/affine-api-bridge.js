/**
 * Connects Launchpad shell UI (from Agentic-LaunchPad-Final) to AFFINE backend (/api/sessions).
 */
(function () {
  const API = "/api";

  function specToLaunchpadFormat(spec) {
    if (!spec) return { slots: [], completion_pct: 0, status: "draft" };
    if (Array.isArray(spec.slots)) return spec;

    const fields = spec.fields || {};
    const slots = Object.entries(fields).map(([key, f]) => ({
      key,
      label: (f && f.label) || key.replace(/_/g, " "),
      value: (f && f.value) || "",
      confidence: f && typeof f.confidence === "number" ? f.confidence : null,
      status:
        f && f.status === "known" && f.value
          ? "confirmed"
          : f && f.source === "inferred"
            ? "inferred"
            : "empty",
    }));
    const known = slots.filter((s) => s.value).length;
    const completion_pct =
      slots.length > 0 ? Math.round((known / slots.length) * 100) : 0;
    return {
      ...spec,
      slots,
      completion_pct,
      status: spec.status || "draft",
    };
  }

  function sessionToInterviewPayload(session) {
    const spec = specToLaunchpadFormat(session.spec);
    const pq = session.pending_question;
    const is_complete = session.spec?.status === "ready";
    const field = pq?.field_key ? session.spec?.fields?.[pq.field_key] : null;
    const fieldConfidence =
      field && typeof field.confidence === "number" ? field.confidence : null;
    const chips = pq?.chips || [];
    const options = chips.map((chip, i) => {
      const conf =
        fieldConfidence != null
          ? Math.max(0.55, fieldConfidence - i * 0.05)
          : Math.max(0.62, 0.94 - i * 0.08);
      return {
        id: `chip_${i}`,
        label: chip,
        value: chip,
        confidence: Math.round(conf * 100) / 100,
        suggested: i === 0,
      };
    });
    const suggestedOptionId = options.find((o) => o.suggested)?.id || null;
    return {
      session_id: session.id,
      spec,
      is_complete,
      completion_pct: spec.completion_pct,
      question: pq?.question || null,
      options,
      suggested_option_id: suggestedOptionId,
      field_confidence: fieldConfidence,
      target_slot: pq?.field_key || null,
      target_slot_label: field?.label || (pq?.field_key || "").replace(/_/g, " "),
      is_followup: false,
      answered_slot: session.last_answered_field || null,
      answered_slot_label: session.last_answered_field
        ? session.spec?.fields?.[session.last_answered_field]?.label
        : null,
      message: "",
    };
  }

  function normLabel(s) {
    return String(s || "")
      .trim()
      .toLowerCase()
      .replace(/\s+/g, " ");
  }

  function findReuseDec(reuseDecisions, node) {
    const list = reuseDecisions || [];
    const byId = list.find((d) => d && d.node_id === node.id);
    if (byId) return byId;
    const label = normLabel(node.label);
    if (label) {
      const byLabel = list.find((d) => normLabel(d.node_label) === label);
      if (byLabel) return byLabel;
      const slug = label.replace(/[^a-z0-9]+/g, "-");
      const bySlug = list.find(
        (d) => normLabel(d.node_id).replace(/_/g, "-") === slug
      );
      if (bySlug) return bySlug;
    }
    return null;
  }

  function mergeReuseOntoNodes(nodes, reuseDecisions) {
    return (nodes || []).map((n) => {
      const dec = findReuseDec(reuseDecisions, n);
      const agentType =
        n.type === "custom" || n.type === "agent" ? "agent" : n.type;
      const decision =
        dec?.decision || n.reuse_decision || "build";
      return {
        ...n,
        type: agentType,
        reuse_decision: decision,
        catalog_agent_id:
          dec?.agent_id || n.catalog_agent_id || n.agent_id || null,
        catalog_score:
          dec?.catalog_score != null ? dec.catalog_score : n.catalog_score,
        source_project: n.source_project || dec?.agent_name || null,
      };
    });
  }

  function normalizePlan(plan) {
    if (!plan) return plan;
    const reuseDecisions = plan.reuse_decisions || [];
    if (plan.graph && !plan.nodes) {
      const nodes = mergeReuseOntoNodes(plan.graph.nodes, reuseDecisions);
      const edges = (plan.graph.edges || []).map((e, i) => ({
        id: e.id || `e_${i}`,
        source: e.from_id ?? e.source,
        target: e.to_id ?? e.target,
        type: e.type,
        label: e.label,
      }));
      const capabilities = (plan.capabilities || []).length
        ? plan.capabilities
        : (plan.catalog_matches || []).map((m) => ({
            capability: m.matched_for || m.name || m.agent_id,
            decision: (m.score || 0) >= 0.75 ? "reuse" : "adapt",
            catalog_agent_name: m.name,
            catalog_project: m.origin_project,
            search_score: m.score,
            rationale: m.function_summary,
          }));
      let reuse = 0;
      let adapt = 0;
      let build = 0;
      nodes.forEach((n) => {
        if (n.type !== "agent") return;
        const d = (n.reuse_decision || "build").toLowerCase();
        if (d === "reuse") reuse++;
        else if (d === "adapt") adapt++;
        else build++;
      });
      return {
        ...plan,
        nodes,
        edges,
        reuse_decisions: reuseDecisions,
        capabilities,
        reuse_count: reuse + adapt,
        build_count: build,
        narrative: plan.summary_markdown || plan.narrative || "",
      };
    }
    if (plan.nodes?.length) {
      return {
        ...plan,
        nodes: mergeReuseOntoNodes(plan.nodes, reuseDecisions),
      };
    }
    return plan;
  }

  async function parseJson(res) {
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, data };
  }

  window.AffineApi = {
    async startInterview(problemStatement) {
      const res = await fetch(`${API}/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ problem_statement: problemStatement }),
      });
      const { ok, data } = await parseJson(res);
      if (!ok) return { ok, data };
      return { ok: true, data: sessionToInterviewPayload(data.session) };
    },

    async answerInterview(sessionId, answer, optionId, forceComplete) {
      let text = answer;
      if (forceComplete) {
        text = "Proceed with best-effort specification.";
      }
      const res = await fetch(`${API}/sessions/${sessionId}/turn`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answer: text }),
      });
      const { ok, data } = await parseJson(res);
      if (!ok) return { ok, data };
      const payload = sessionToInterviewPayload(data.session);
      if (forceComplete) {
        payload.is_complete = data.session?.spec?.status === "ready";
      }
      return { ok: true, data: payload };
    },

    async generatePlan(sessionId) {
      const res = await fetch(`${API}/sessions/${sessionId}/architecture`, {
        method: "POST",
      });
      const { ok, data } = await parseJson(res);
      if (!ok) return { ok, data };
      return { ok: true, data: normalizePlan(data.plan) };
    },
  };
})();
