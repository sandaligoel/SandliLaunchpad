export type AgentType =
  | "mcp"
  | "retrieval"
  | "text-to-sql"
  | "text-to-sap"
  | "text-to-salesforce"
  | "web-search"
  | "email-gen"
  | "sql-insight"
  | "router"
  | "answer-gen"
  | "query-transformer"
  | "tool"
  | "video-gen"
  | "image-gen"
  | "semantic-search";

export type RunStatus = "success" | "failed" | "running" | "queued";
export type WorkflowStatus = "draft" | "published" | "archived";

export type FieldType =
  | "text"
  | "textarea"
  | "number"
  | "select"
  | "multiselect"
  | "radio"
  | "slider"
  | "file"
  | "tags"
  | "toggle";

export interface FieldDef {
  key: string;
  label: string;
  type: FieldType;
  required?: boolean;
  description?: string;
  placeholder?: string;
  options?: string[];
  min?: number;
  max?: number;
  step?: number;
  default?: unknown;
}

export interface OutputDef {
  name: string;
  description: string;
}

export interface AgentDef {
  type: AgentType;
  name: string;
  category: string;
  description: string;
  summary: string;
  color: string;
  icon: string;
  inputs: string[];
  outputs: string[];
  fields: FieldDef[];
  outputFields: OutputDef[];
  defaultConfig: Record<string, unknown>;
}

const buildDefaults = (fields: FieldDef[]): Record<string, unknown> => {
  const out: Record<string, unknown> = {};
  fields.forEach((f) => {
    if (f.default !== undefined) out[f.key] = f.default;
    else if (f.type === "toggle") out[f.key] = false;
    else if (f.type === "multiselect" || f.type === "tags") out[f.key] = [];
    else if (f.type === "number" || f.type === "slider") out[f.key] = f.min ?? 0;
    else out[f.key] = "";
  });
  return out;
};

/* ------------------------------------------------------------------ */
/*  Field definitions per agent type                                   */
/* ------------------------------------------------------------------ */

const MCP_FIELDS: FieldDef[] = [
  { key: "mcpServerType", label: "MCP Server Type", type: "select", required: true, options: ["Filesystem", "PostgreSQL", "GitHub", "Slack", "Custom HTTP"] },
  { key: "transportProtocol", label: "Transport Protocol", type: "select", required: true, options: ["stdio", "SSE", "WebSocket"] },
  { key: "toolDefinitions", label: "Tool Definitions", type: "textarea", description: "List of tool names + descriptions the agent can call" },
  { key: "authType", label: "Authentication Type", type: "select", options: ["None", "API Key", "OAuth2", "Bearer Token"], default: "None" },
  { key: "connectionConfig", label: "Connection Config", type: "textarea", description: "Host, port, base URL, env var name for secrets" },
  { key: "llmBackend", label: "LLM Backend", type: "select", required: true, options: ["OpenAI", "Azure OpenAI", "Anthropic", "Local (Ollama)"], default: "OpenAI" },
  { key: "systemPrompt", label: "System Prompt", type: "textarea", description: "Agent persona and task instructions" },
  { key: "maxToolCallRounds", label: "Max Tool Call Rounds", type: "number", description: "Loop limit before forcing a final answer", default: 10, min: 1, max: 50 },
];

const MCP_OUTPUTS: OutputDef[] = [
  { name: "MCP client setup file", description: "Server connection + transport initialization code" },
  { name: "Tool registry module", description: "Tool definitions with input schemas and handlers" },
  { name: "Agent loop script", description: "LLM → tool call → result → next-step loop" },
  { name: "Auth config snippet", description: "Env-var wiring and token injection pattern" },
  { name: "requirements.txt / package.json", description: "mcp, anthropic/openai sdk, transport deps" },
  { name: "README with run instructions", description: "How to start the MCP server and run the agent" },
];

const RETRIEVAL_FIELDS: FieldDef[] = [
  { key: "vectorStoreType", label: "Vector Store Type", type: "select", required: true, options: ["Azure AI Search", "Pinecone", "Weaviate", "Chroma", "pgvector", "FAISS (local)"] },
  { key: "indexName", label: "Index / Collection Name", type: "text", required: true, placeholder: "my-search-index" },
  { key: "embeddingModel", label: "Embedding Model", type: "select", required: true, options: ["text-embedding-3-small", "ada-002", "Cohere", "BGE", "Custom"], default: "text-embedding-3-small" },
  { key: "searchMode", label: "Search Mode", type: "select", required: true, options: ["Semantic", "Keyword", "Hybrid", "MMR"], default: "Hybrid" },
  { key: "topK", label: "Top K", type: "number", default: 5, min: 1, max: 100 },
  { key: "metadataFilters", label: "Metadata Filters", type: "textarea", description: "Fields and values to pre-filter results" },
  { key: "fieldsToReturn", label: "Fields to Return", type: "tags", description: "Which document fields to include in results" },
  { key: "minScoreThreshold", label: "Min Score Threshold", type: "number", default: 0.5, min: 0, max: 1, step: 0.05 },
  { key: "reranker", label: "Reranker", type: "toggle", description: "Apply cross-encoder reranking after retrieval", default: false },
];

const RETRIEVAL_OUTPUTS: OutputDef[] = [
  { name: "Vector store client module", description: "Connection + authentication to chosen store" },
  { name: "Embedding function", description: "Encodes query using selected embedding model" },
  { name: "Retrieval function", description: "Executes search with mode, top_k, filters" },
  { name: "Reranker module (optional)", description: "Cross-encoder scoring and re-sorting" },
  { name: "Result formatter", description: "Shapes returned docs into a standard dict/JSON" },
  { name: "Config file (.env / YAML)", description: "Endpoint, API keys, index name as env vars" },
  { name: "requirements.txt", description: "SDK deps for chosen vector store + embeddings" },
];

const TEXT_TO_SQL_FIELDS: FieldDef[] = [
  { key: "dbEngine", label: "Database Engine", type: "select", required: true, options: ["PostgreSQL", "MySQL", "Azure SQL", "Snowflake", "BigQuery", "SQLite"] },
  { key: "schemaInputMethod", label: "Schema Input Method", type: "select", options: ["Paste DDL", "Describe tables in plain text", "Connect and auto-introspect"] },
  { key: "tableScope", label: "Table / Schema Scope", type: "tags", description: "Which tables the agent is allowed to query" },
  { key: "schemaContext", label: "Schema Context / Glossary", type: "textarea", description: "Business term definitions, column aliases" },
  { key: "llmModel", label: "LLM Model", type: "select", required: true, options: ["GPT-4o", "GPT-4-turbo", "Claude", "Gemini"], default: "GPT-4o" },
  { key: "queryMode", label: "Query Mode", type: "select", required: true, options: ["Generate only", "Generate + execute", "Generate + validate only"], default: "Generate + execute" },
  { key: "outputFormat", label: "Output Format", type: "select", options: ["Table", "JSON", "CSV", "Pandas DataFrame"], default: "JSON" },
  { key: "rowLimit", label: "Row Limit", type: "number", default: 100, min: 1, max: 10000 },
  { key: "sqlDialectGuard", label: "SQL Dialect Guard", type: "toggle", description: "Enforce read-only / no DDL / no DELETE in generated SQL", default: true },
];

const TEXT_TO_SQL_OUTPUTS: OutputDef[] = [
  { name: "Schema loader", description: "Reads DDL or introspects DB to build context string" },
  { name: "Prompt builder", description: "Composes schema + glossary + question into LLM prompt" },
  { name: "LLM SQL generator", description: "Calls chosen LLM and extracts SQL from response" },
  { name: "SQL validator", description: "Checks for dialect correctness and safety guardrails" },
  { name: "DB execution module", description: "Runs validated SQL and returns result set" },
  { name: "Output formatter", description: "Converts result to table / JSON / CSV / DataFrame" },
  { name: "Connection config (.env)", description: "DB host, port, user, password, DB name as env vars" },
];

const TEXT_TO_SAP_FIELDS: FieldDef[] = [
  { key: "sapSystemType", label: "SAP System Type", type: "select", required: true, options: ["SAP S/4HANA", "SAP ECC", "SAP BTP", "SAP SuccessFactors"] },
  { key: "integrationMethod", label: "Integration Method", type: "select", required: true, options: ["OData API", "BAPI/RFC", "SAP GUI Scripting", "REST Connector"] },
  { key: "targetModule", label: "Target Module", type: "select", required: true, options: ["FI (Finance)", "MM (Materials)", "SD (Sales)", "PP (Production)", "HR"] },
  { key: "availableEntities", label: "Available Entities / Endpoints", type: "textarea", description: "OData entity names or BAPI names to expose" },
  { key: "authMethod", label: "Auth Method", type: "select", options: ["Basic Auth", "SAP OAuth2", "X.509 Certificate"], default: "Basic Auth" },
  { key: "llmModel", label: "LLM Model", type: "select", required: true, options: ["GPT-4o", "Claude", "Gemini"], default: "GPT-4o" },
  { key: "operationType", label: "Operation Type", type: "select", options: ["Read only", "Read + write", "Transactional"], default: "Read only" },
  { key: "outputFormat", label: "Output Format", type: "select", options: ["JSON", "Table", "SAP-native XML", "Pandas"], default: "JSON" },
];

const TEXT_TO_SAP_OUTPUTS: OutputDef[] = [
  { name: "SAP connector module", description: "OData/BAPI client with auth and session handling" },
  { name: "Entity/BAPI registry", description: "Maps business intent keywords to SAP endpoints" },
  { name: "Intent parser", description: "LLM call that converts NL query into API params" },
  { name: "Request builder", description: "Constructs OData $filter, $select, $top expressions" },
  { name: "Response normalizer", description: "Flattens SAP XML/JSON into clean output format" },
  { name: "Error handler", description: "SAP-specific error code mapping and retry logic" },
  { name: "Config + .env template", description: "SAP host, client ID, credentials as env vars" },
];

const TEXT_TO_SF_FIELDS: FieldDef[] = [
  { key: "salesforceCloud", label: "Salesforce Cloud", type: "select", required: true, options: ["Sales Cloud", "Service Cloud", "Marketing Cloud", "Custom Org"] },
  { key: "apiType", label: "API Type", type: "select", required: true, options: ["REST API", "SOQL", "Bulk API", "Metadata API", "Apex REST"] },
  { key: "targetObjects", label: "Target Objects", type: "tags", description: "Account, Contact, Lead, Opportunity, Case, custom objects" },
  { key: "authFlow", label: "Auth Flow", type: "select", required: true, options: ["OAuth2 Web Server Flow", "JWT Bearer", "Username-Password"], default: "OAuth2 Web Server Flow" },
  { key: "operationType", label: "Operation Type", type: "select", options: ["Query only", "Create", "Update", "Upsert", "Delete"], default: "Query only" },
  { key: "llmModel", label: "LLM Model", type: "select", required: true, options: ["GPT-4o", "Claude"], default: "GPT-4o" },
  { key: "outputFormat", label: "Output Format", type: "select", options: ["JSON", "Table", "CSV", "Pandas"], default: "JSON" },
  { key: "fieldContext", label: "Field Context", type: "textarea", description: "Custom field API names and their business descriptions" },
];

const TEXT_TO_SF_OUTPUTS: OutputDef[] = [
  { name: "Salesforce auth module", description: "OAuth2/JWT flow with token refresh handling" },
  { name: "SOQL generator", description: "LLM prompt → SOQL query with field and object context" },
  { name: "SOQL validator", description: "Syntax check and field existence validation" },
  { name: "API executor", description: "Runs query or DML against Salesforce REST/Bulk API" },
  { name: "Response formatter", description: "Normalizes Salesforce response to target format" },
  { name: "Object schema loader", description: "Fetches object describe metadata for context building" },
  { name: ".env template", description: "SF_CLIENT_ID, SF_CLIENT_SECRET, SF_USERNAME, instance URL" },
];

const WEB_SEARCH_FIELDS: FieldDef[] = [
  { key: "searchProvider", label: "Search Provider", type: "select", required: true, options: ["Tavily", "Serper", "SerpAPI", "Bing Search API", "Google Custom Search", "DuckDuckGo"] },
  { key: "searchDepth", label: "Search Depth", type: "select", options: ["Basic (snippets)", "Advanced (full page content)", "News-only"], default: "Basic (snippets)" },
  { key: "maxResults", label: "Max Results", type: "number", default: 10, min: 1, max: 50 },
  { key: "includeDomains", label: "Include Domains", type: "tags", description: "Whitelist specific domains (optional)" },
  { key: "excludeDomains", label: "Exclude Domains", type: "tags", description: "Blacklist domains to skip" },
  { key: "contentScraping", label: "Content Scraping", type: "toggle", description: "Scrape and parse full page content beyond snippets", default: false },
  { key: "summarization", label: "Summarization", type: "toggle", description: "LLM-summarize results before returning", default: false },
  { key: "llmModel", label: "LLM Model (if summarizing)", type: "select", options: ["GPT-4o", "Claude", "Gemini"], default: "GPT-4o" },
  { key: "agentFramework", label: "Agent Framework", type: "select", options: ["Standalone", "LangChain Tool", "LlamaIndex Tool", "Custom"], default: "Standalone" },
];

const WEB_SEARCH_OUTPUTS: OutputDef[] = [
  { name: "Search client module", description: "Provider SDK/API call with auth and param handling" },
  { name: "Content scraper (optional)", description: "BeautifulSoup/Playwright page extraction function" },
  { name: "Result normalizer", description: "Standardizes results across providers into {title, url, snippet}" },
  { name: "Summarizer module (optional)", description: "Passes results to LLM for synthesis" },
  { name: "Tool wrapper (if framework)", description: "LangChain/LlamaIndex tool class wrapping the search fn" },
  { name: ".env template", description: "SEARCH_API_KEY and provider endpoint" },
  { name: "requirements.txt", description: "Provider SDK, scraping libs, LLM client deps" },
];

const EMAIL_GEN_FIELDS: FieldDef[] = [
  { key: "emailUseCase", label: "Email Use Case", type: "select", required: true, options: ["Sales Outreach", "Follow-up", "Support Response", "Marketing Campaign", "Internal Comms", "Alert/Notification"] },
  { key: "tone", label: "Tone", type: "select", required: true, options: ["Formal", "Professional", "Friendly", "Urgent", "Empathetic"], default: "Professional" },
  { key: "contextInputType", label: "Context Input Type", type: "select", options: ["Free-text brief", "CRM data (JSON)", "Prior email thread (text)", "Structured template vars"] },
  { key: "personalizationFields", label: "Personalization Fields", type: "tags", description: "Recipient name, company, role, product interest, etc." },
  { key: "llmModel", label: "LLM Model", type: "select", required: true, options: ["GPT-4o", "Claude", "Gemini"], default: "GPT-4o" },
  { key: "outputVariants", label: "Output Variants", type: "number", description: "Number of alternative email drafts to generate", default: 1, min: 1, max: 5 },
  { key: "sendIntegration", label: "Send Integration", type: "select", options: ["None (generate only)", "SendGrid", "Gmail API", "Outlook API", "SMTP"], default: "None (generate only)" },
  { key: "subjectLineGeneration", label: "Subject Line Generation", type: "toggle", description: "Generate subject line alongside email body", default: true },
  { key: "language", label: "Language", type: "select", options: ["English", "Spanish", "French", "German", "Japanese", "Auto-detect"], default: "English" },
];

const EMAIL_GEN_OUTPUTS: OutputDef[] = [
  { name: "Context builder", description: "Assembles recipient data + brief into a prompt context block" },
  { name: "Prompt template", description: "Tone + use case + personalization fields baked into system prompt" },
  { name: "Email generator function", description: "LLM call returning subject + body (+ N variants)" },
  { name: "Send integration module", description: "SendGrid/Gmail/SMTP client wired to generator output" },
  { name: "Batch generation loop (optional)", description: "Iterates over list of recipients and generates per-person emails" },
  { name: ".env template", description: "LLM key, send provider API key, sender address" },
];

const SQL_INSIGHT_FIELDS: FieldDef[] = [
  { key: "dbEngine", label: "Database Engine", type: "select", required: true, options: ["PostgreSQL", "MySQL", "Snowflake", "BigQuery", "Azure SQL", "DuckDB"] },
  { key: "dataInputType", label: "Data Input Type", type: "select", options: ["Live DB connection", "Pre-executed result set (JSON/CSV)", "SQL query output"] },
  { key: "targetTablesQuery", label: "Target Tables / Query", type: "textarea", description: "Table names, or the SQL query whose results to analyze" },
  { key: "insightTypes", label: "Insight Types", type: "multiselect", options: ["Trends", "Anomalies", "Top/Bottom N", "Correlations", "Forecasts", "Executive Summary"] },
  { key: "businessContext", label: "Business Context", type: "textarea", description: "What the data represents, KPIs that matter, audience for the insight" },
  { key: "llmModel", label: "LLM Model", type: "select", required: true, options: ["GPT-4o", "Claude", "Gemini"], default: "GPT-4o" },
  { key: "outputFormat", label: "Output Format", type: "select", options: ["Bullet points", "Paragraph narrative", "Markdown report", "JSON structured insights"], default: "Markdown report" },
  { key: "chartGeneration", label: "Chart Generation", type: "toggle", description: "Auto-generate matplotlib / plotly charts alongside insights", default: true },
];

const SQL_INSIGHT_OUTPUTS: OutputDef[] = [
  { name: "Data loader", description: "Connects to DB or reads result set CSV/JSON" },
  { name: "Statistical summarizer", description: "Computes describe(), correlations, outlier flags on the data" },
  { name: "Insight prompt builder", description: "Formats stats + business context into LLM insight request" },
  { name: "LLM insight generator", description: "Returns structured insight text in chosen format" },
  { name: "Chart generator (optional)", description: "Matplotlib/plotly code for auto-detected chart types" },
  { name: "Report assembler", description: "Combines charts + insights into markdown or HTML report" },
  { name: ".env + requirements.txt", description: "DB credentials, LLM key, pandas/plotly/sqlalchemy deps" },
];

const ROUTER_FIELDS: FieldDef[] = [
  { key: "routingStrategy", label: "Routing Strategy", type: "select", required: true, options: ["LLM-based intent classification", "Keyword rules", "Embedding similarity", "Hybrid"], default: "LLM-based intent classification" },
  { key: "availableRoutes", label: "Available Routes / Sub-agents", type: "tags", description: "Names and descriptions of downstream agents to route to" },
  { key: "routeDefinitions", label: "Route Definitions", type: "textarea", description: "Per-route: trigger intent, description, handler function name" },
  { key: "fallbackBehavior", label: "Fallback Behavior", type: "select", options: ["Default route", "Ask for clarification", "Return error"], default: "Ask for clarification" },
  { key: "llmModel", label: "LLM Model", type: "select", options: ["GPT-4o-mini", "Claude Haiku"], default: "GPT-4o-mini" },
  { key: "multiRoute", label: "Multi-route", type: "toggle", description: "Allow a single query to route to multiple agents in parallel", default: false },
  { key: "confidenceThreshold", label: "Confidence Threshold", type: "number", description: "Min classification confidence to commit to a route", default: 0.7, min: 0, max: 1, step: 0.05 },
];

const ROUTER_OUTPUTS: OutputDef[] = [
  { name: "Route registry", description: "Dict/config of route names → handler functions + descriptions" },
  { name: "Intent classifier", description: "LLM or embedding call that maps query → route name" },
  { name: "Router dispatcher", description: "Calls the matched handler with the original query" },
  { name: "Fallback handler", description: "Handles low-confidence or unmatched queries" },
  { name: "Parallel executor (optional)", description: "asyncio / ThreadPool runner for multi-route dispatch" },
  { name: "Trace logger", description: "Logs which route was chosen and why, with confidence score" },
  { name: "requirements.txt", description: "LLM client, embedding libs if similarity routing" },
];

const ANSWER_GEN_FIELDS: FieldDef[] = [
  { key: "contextSourceType", label: "Context Source Type", type: "select", options: ["Retrieved chunks", "Structured data (JSON/table)", "Pasted text", "Mixed"] },
  { key: "llmModel", label: "LLM Model", type: "select", required: true, options: ["GPT-4o", "Claude 3.5", "Gemini", "Llama 3 (local)"], default: "GPT-4o" },
  { key: "groundingMode", label: "Grounding Mode", type: "select", options: ["Strict (context only)", "Soft (context + general knowledge)", "Summarize-only"], default: "Strict (context only)" },
  { key: "systemPrompt", label: "System Prompt / Persona", type: "textarea", description: "Custom role, constraints, tone, output format instructions" },
  { key: "citationMode", label: "Citation Mode", type: "select", options: ["None", "Inline [1]", "Footnote", "Structured JSON citations"], default: "Inline [1]" },
  { key: "temperature", label: "Temperature", type: "slider", min: 0, max: 2, step: 0.1, default: 0.7 },
  { key: "maxTokens", label: "Max Tokens", type: "number", default: 1024, min: 64, max: 32000 },
  { key: "outputFormat", label: "Output Format", type: "select", options: ["Plain text", "Markdown", "JSON structured", "HTML"], default: "Markdown" },
  { key: "fallbackBehavior", label: "Fallback Behavior", type: "select", options: ["Say 'I don't know'", "Ask clarification", "Attempt best-effort answer"], default: "Say 'I don't know'" },
];

const ANSWER_GEN_OUTPUTS: OutputDef[] = [
  { name: "Context formatter", description: "Converts chunks/JSON/text into a clean context block for the prompt" },
  { name: "Prompt assembler", description: "Builds final prompt: system prompt + context + question" },
  { name: "LLM caller", description: "API call with temp, max_tokens, and streaming support" },
  { name: "Citation extractor (optional)", description: "Parses answer to attach source references" },
  { name: "Output formatter", description: "Returns answer in plain text / markdown / JSON" },
  { name: "Hallucination guard (optional)", description: "Checks answer against context for unsupported claims" },
  { name: ".env + requirements.txt", description: "LLM API key, model name, provider SDK dep" },
];

const QUERY_TRANSFORMER_FIELDS: FieldDef[] = [
  { key: "transformationType", label: "Transformation Type", type: "multiselect", required: true, options: ["Query rewriting", "HyDE (hypothetical doc)", "Step-back prompting", "Multi-query expansion", "Query decomposition"] },
  { key: "llmModel", label: "LLM Model", type: "select", required: true, options: ["GPT-4o", "Claude", "Gemini"], default: "GPT-4o" },
  { key: "numQueryVariants", label: "Number of Query Variants", type: "number", default: 3, min: 1, max: 10 },
  { key: "domainContext", label: "Domain Context", type: "textarea", description: "Domain vocabulary or knowledge to guide rewriting" },
  { key: "downstreamRetrieverType", label: "Downstream Retriever Type", type: "select", options: ["Vector search", "BM25", "Hybrid"], default: "Hybrid" },
  { key: "deduplication", label: "Deduplication", type: "toggle", description: "Remove duplicate results across multi-query retrievals", default: true },
  { key: "resultMergeStrategy", label: "Result Merge Strategy", type: "select", options: ["Union", "Intersection", "Reciprocal Rank Fusion (RRF)"], default: "Reciprocal Rank Fusion (RRF)" },
];

const QUERY_TRANSFORMER_OUTPUTS: OutputDef[] = [
  { name: "Query rewriter module", description: "LLM prompt that rewrites the input query per selected strategy" },
  { name: "HyDE generator (optional)", description: "Generates a hypothetical answer document to embed for retrieval" },
  { name: "Multi-query expander (optional)", description: "Produces N query variants from the original input" },
  { name: "Decomposer (optional)", description: "Breaks complex questions into sub-questions" },
  { name: "Result merger", description: "Combines multi-query results via union, intersection, or RRF" },
  { name: "Deduplicator", description: "Removes duplicate document chunks across queries" },
  { name: "requirements.txt", description: "LLM client, rank-bm25 or reciprocal-rank-fusion dep" },
];

const TOOL_FIELDS: FieldDef[] = [
  { key: "agentFramework", label: "Agent Framework", type: "select", required: true, options: ["LangChain", "LlamaIndex", "Custom Function-calling", "Semantic Kernel", "CrewAI"] },
  { key: "llmModel", label: "LLM Model", type: "select", required: true, options: ["GPT-4o", "Claude 3.5", "Gemini"], default: "GPT-4o" },
  { key: "toolsToInclude", label: "Tools to Include", type: "multiselect", options: ["Calculator", "Web Search", "Code Executor", "DB Query", "File Reader", "API Caller", "Custom"] },
  { key: "customToolDefinitions", label: "Custom Tool Definitions", type: "textarea", description: "Name, description, input schema for each custom tool" },
  { key: "maxIterations", label: "Max Iterations", type: "number", description: "Max tool call rounds before forcing final answer", default: 10, min: 1, max: 50 },
  { key: "memoryType", label: "Memory Type", type: "select", options: ["None", "Conversation Buffer", "Summary Memory", "Entity Memory"], default: "None" },
  { key: "systemPrompt", label: "System Prompt", type: "textarea", description: "Agent persona, task scope, output constraints" },
  { key: "executionMode", label: "Execution Mode", type: "select", options: ["ReAct Loop", "OpenAI Function Calling", "Parallel Tool Use"], default: "ReAct Loop" },
];

const TOOL_OUTPUTS: OutputDef[] = [
  { name: "Tool definitions file", description: "Each tool as a typed function with name, description, and input schema" },
  { name: "Agent executor", description: "LLM + tool loop with chosen framework (ReAct / function-calling)" },
  { name: "Memory module", description: "Conversation history or summary memory wired into the agent" },
  { name: "Tool result parser", description: "Normalizes each tool's output for LLM consumption" },
  { name: "Trace / step logger", description: "Logs thought → tool call → observation at each step" },
  { name: "requirements.txt", description: "Framework deps (langchain, llama-index, etc.) + tool deps" },
  { name: ".env template", description: "LLM API key + any tool-specific credentials" },
];

const VIDEO_GEN_FIELDS: FieldDef[] = [
  { key: "videoProvider", label: "Video Model / Provider", type: "select", required: true, options: ["Sora (OpenAI)", "Runway Gen-3", "Pika", "Kling", "Stable Video Diffusion", "CogVideoX"] },
  { key: "promptInputType", label: "Prompt Input Type", type: "select", options: ["Text-to-video", "Image-to-video", "Video-to-video (style transfer)"], default: "Text-to-video" },
  { key: "promptConstruction", label: "Prompt Construction", type: "select", options: ["Direct user text", "LLM-enhanced prompt", "Structured template"], default: "Direct user text" },
  { key: "duration", label: "Duration", type: "select", options: ["4s", "8s", "16s", "Custom"], default: "4s" },
  { key: "resolution", label: "Resolution", type: "select", options: ["480p", "720p", "1080p"], default: "720p" },
  { key: "aspectRatio", label: "Aspect Ratio", type: "select", options: ["16:9", "9:16", "1:1"], default: "16:9" },
  { key: "motionIntensity", label: "Motion Intensity", type: "select", options: ["Low", "Medium", "High"], default: "Medium" },
  { key: "outputHandling", label: "Output Handling", type: "select", options: ["Download URL only", "Auto-download to disk", "Upload to blob storage"], default: "Auto-download to disk" },
  { key: "batchGeneration", label: "Batch Generation", type: "toggle", description: "Generate multiple videos from a list of prompts", default: false },
];

const VIDEO_GEN_OUTPUTS: OutputDef[] = [
  { name: "Prompt enhancer (optional)", description: "LLM call that enriches bare user text into a cinematic video prompt" },
  { name: "API client module", description: "Provider SDK/REST call with auth, resolution, duration params" },
  { name: "Async poller", description: "Polls generation job status and waits for completion" },
  { name: "Output downloader", description: "Downloads generated video to local path or blob storage" },
  { name: "Batch runner (optional)", description: "Iterates over prompt list and runs generation with rate limit handling" },
  { name: ".env template", description: "VIDEO_API_KEY, output directory, storage credentials" },
  { name: "requirements.txt", description: "Provider SDK + requests + storage client deps" },
];

const IMAGE_GEN_FIELDS: FieldDef[] = [
  { key: "imageProvider", label: "Image Model / Provider", type: "select", required: true, options: ["DALL-E 3", "Stable Diffusion", "Midjourney API", "Flux", "Ideogram", "Adobe Firefly"] },
  { key: "generationMode", label: "Generation Mode", type: "select", options: ["Text-to-image", "Image-to-image", "Inpainting", "Outpainting", "Upscaling"], default: "Text-to-image" },
  { key: "promptConstruction", label: "Prompt Construction", type: "select", options: ["Direct text", "LLM-enhanced prompt", "Structured style + subject template"], default: "Direct text" },
  { key: "styleAesthetic", label: "Style / Aesthetic", type: "select", options: ["Photorealistic", "Illustration", "3D Render", "Sketch", "Watercolor", "Corporate/Clean"], default: "Photorealistic" },
  { key: "sizeAspectRatio", label: "Size / Aspect Ratio", type: "select", options: ["1024×1024", "1792×1024", "1024×1792", "Custom"], default: "1024×1024" },
  { key: "numberOfImages", label: "Number of Images", type: "number", default: 1, min: 1, max: 10 },
  { key: "negativePrompt", label: "Negative Prompt", type: "textarea", description: "What to exclude from the generated image (SD/Flux)" },
  { key: "outputHandling", label: "Output Handling", type: "select", options: ["URL only", "Download to disk", "Upload to blob/S3", "Base64 return"], default: "Download to disk" },
  { key: "batchGeneration", label: "Batch Generation", type: "toggle", description: "Generate images from a list of prompts in a loop", default: false },
];

const IMAGE_GEN_OUTPUTS: OutputDef[] = [
  { name: "Prompt enhancer (optional)", description: "LLM call that adds style, lighting, and composition details to bare input" },
  { name: "API client module", description: "Provider SDK/REST call with size, style, n params + auth" },
  { name: "Image downloader / saver", description: "Downloads URL response or decodes base64 to disk" },
  { name: "Storage uploader (optional)", description: "Uploads generated image to S3/Azure Blob with metadata" },
  { name: "Batch runner (optional)", description: "Reads prompt list and generates with concurrency + rate limit" },
  { name: "Metadata writer", description: "Saves prompt, model, timestamp, size alongside each image" },
  { name: ".env + requirements.txt", description: "IMAGE_API_KEY, output path, provider SDK dep" },
];

const SEMANTIC_SEARCH_FIELDS: FieldDef[] = [
  { key: "docSourceType", label: "Document Source Type", type: "select", required: true, options: ["Local files (PDF/TXT/DOCX)", "S3/Blob Storage", "Database Column", "Web URLs", "In-memory List"] },
  { key: "chunkingStrategy", label: "Chunking Strategy", type: "select", options: ["Fixed-size", "Sentence", "Paragraph", "Semantic (embedding-based)", "Parent-child"], default: "Fixed-size" },
  { key: "chunkSize", label: "Chunk Size", type: "number", description: "Tokens or characters per chunk", default: 512, min: 64, max: 8192 },
  { key: "chunkOverlap", label: "Chunk Overlap", type: "number", description: "Token/char overlap between consecutive chunks", default: 64, min: 0, max: 1024 },
  { key: "embeddingModel", label: "Embedding Model", type: "select", required: true, options: ["text-embedding-3-small", "ada-002", "Cohere", "BGE", "Sentence-transformers (local)"], default: "text-embedding-3-small" },
  { key: "vectorStore", label: "Vector Store", type: "select", required: true, options: ["Chroma (local)", "FAISS (local)", "Pinecone", "Weaviate", "Azure AI Search", "pgvector"] },
  { key: "metadataToAttach", label: "Metadata to Attach", type: "tags", description: "Source filename, page number, date, category, custom fields" },
  { key: "searchType", label: "Search Type", type: "select", options: ["Similarity only", "Hybrid (semantic + BM25)", "MMR diversity"], default: "Similarity only" },
  { key: "topK", label: "Top K", type: "number", default: 5, min: 1, max: 100 },
  { key: "persistIndex", label: "Persist Index", type: "toggle", description: "Save index to disk/cloud vs. rebuild in memory each run", default: true },
];

const SEMANTIC_SEARCH_OUTPUTS: OutputDef[] = [
  { name: "Document loader", description: "Reads source files/URLs/DB column into raw text" },
  { name: "Chunker", description: "Splits text per chosen strategy with overlap" },
  { name: "Embedder", description: "Encodes chunks with chosen embedding model (batch)" },
  { name: "Index builder", description: "Upserts chunk vectors + metadata into chosen vector store" },
  { name: "Search function", description: "Embeds query and retrieves top-k with score and metadata" },
  { name: "Index persistence handler", description: "Save/load index from disk or cloud if persist is on" },
  { name: "Result formatter", description: "Returns ranked chunks as {text, score, source, metadata}" },
  { name: ".env + requirements.txt", description: "Embedding API key, vector store creds, chunking/parsing deps" },
];

/* ================================================================== */
/*  AGENT REGISTRY                                                     */
/* ================================================================== */
export const AGENT_REGISTRY: AgentDef[] = [
  {
    type: "mcp", name: "MCP Agent", category: "Protocol",
    description: "Connects to an MCP server and invokes tools via an LLM-driven loop.",
    summary: "Generates a working MCP client agent that connects to a chosen server type and calls tools via an LLM loop",
    color: "#5B5EA6", icon: "Cpu", inputs: ["MCP config", "tools", "prompt"], outputs: ["client code", "tool registry", "agent loop"],
    fields: MCP_FIELDS, outputFields: MCP_OUTPUTS, defaultConfig: buildDefaults(MCP_FIELDS),
  },
  {
    type: "retrieval", name: "Retrieval Agent", category: "RAG",
    description: "Performs semantic / hybrid search over a vector store.",
    summary: "Generates a retrieval pipeline for the chosen vector store — pluggable into any RAG stack",
    color: "#2E86C1", icon: "Database", inputs: ["query", "filters"], outputs: ["documents", "scores"],
    fields: RETRIEVAL_FIELDS, outputFields: RETRIEVAL_OUTPUTS, defaultConfig: buildDefaults(RETRIEVAL_FIELDS),
  },
  {
    type: "text-to-sql", name: "Text-to-SQL Agent", category: "Query Gen",
    description: "Converts natural language to SQL and optionally executes it.",
    summary: "Generates a natural language → SQL pipeline with validation and execution for the chosen DB engine",
    color: "#16A085", icon: "Table", inputs: ["question", "schema"], outputs: ["SQL", "results"],
    fields: TEXT_TO_SQL_FIELDS, outputFields: TEXT_TO_SQL_OUTPUTS, defaultConfig: buildDefaults(TEXT_TO_SQL_FIELDS),
  },
  {
    type: "text-to-sap", name: "Text-to-SAP Agent", category: "ERP",
    description: "Bridges natural language queries to SAP APIs and modules.",
    summary: "Generates a natural language → SAP API bridge for the chosen module and integration method",
    color: "#D4AC0D", icon: "Building", inputs: ["query", "SAP config"], outputs: ["API response", "formatted data"],
    fields: TEXT_TO_SAP_FIELDS, outputFields: TEXT_TO_SAP_OUTPUTS, defaultConfig: buildDefaults(TEXT_TO_SAP_FIELDS),
  },
  {
    type: "text-to-salesforce", name: "Text-to-Salesforce Agent", category: "CRM",
    description: "Translates natural language to SOQL / Salesforce API calls.",
    summary: "Generates a natural language → SOQL/Salesforce API bridge with auth, generation, and execution",
    color: "#00A1E0", icon: "Cloud", inputs: ["query", "SF config"], outputs: ["SOQL", "records"],
    fields: TEXT_TO_SF_FIELDS, outputFields: TEXT_TO_SF_OUTPUTS, defaultConfig: buildDefaults(TEXT_TO_SF_FIELDS),
  },
  {
    type: "web-search", name: "Web Search Agent", category: "Search",
    description: "Searches the web via a chosen provider with optional scraping and summarization.",
    summary: "Generates a web search pipeline wired to a chosen provider, with optional scraping and LLM summarization",
    color: "#2C3E50", icon: "Globe", inputs: ["query", "config"], outputs: ["results", "summary"],
    fields: WEB_SEARCH_FIELDS, outputFields: WEB_SEARCH_OUTPUTS, defaultConfig: buildDefaults(WEB_SEARCH_FIELDS),
  },
  {
    type: "email-gen", name: "Email Generation Agent", category: "Content",
    description: "Drafts personalized emails for various use cases and tones.",
    summary: "Generates an email drafting pipeline for the chosen use case, tone, and optional send integration",
    color: "#E74C3C", icon: "Mail", inputs: ["brief", "recipient data"], outputs: ["email drafts", "subject lines"],
    fields: EMAIL_GEN_FIELDS, outputFields: EMAIL_GEN_OUTPUTS, defaultConfig: buildDefaults(EMAIL_GEN_FIELDS),
  },
  {
    type: "sql-insight", name: "SQL Insight Generation Agent", category: "Analytics",
    description: "Analyzes SQL data and produces LLM-narrated insights and charts.",
    summary: "Generates a pipeline that runs analysis on SQL data and produces LLM-narrated insights and charts",
    color: "#8E44AD", icon: "BarChart3", inputs: ["data source", "context"], outputs: ["insights", "charts"],
    fields: SQL_INSIGHT_FIELDS, outputFields: SQL_INSIGHT_OUTPUTS, defaultConfig: buildDefaults(SQL_INSIGHT_FIELDS),
  },
  {
    type: "router", name: "Router Agent", category: "Orchestration",
    description: "Routes queries to downstream agents based on intent classification.",
    summary: "Generates an intelligent query router that dispatches to named agents based on intent classification",
    color: "#E67E22", icon: "GitBranch", inputs: ["query", "route definitions"], outputs: ["routed result", "trace"],
    fields: ROUTER_FIELDS, outputFields: ROUTER_OUTPUTS, defaultConfig: buildDefaults(ROUTER_FIELDS),
  },
  {
    type: "answer-gen", name: "Answer Generation Agent", category: "RAG",
    description: "Generates grounded answers with citation and formatting options.",
    summary: "Generates a grounded answer synthesis module with citation, formatting, and optional hallucination checking",
    color: "#6A1B9A", icon: "Sparkles", inputs: ["question", "context"], outputs: ["answer", "citations"],
    fields: ANSWER_GEN_FIELDS, outputFields: ANSWER_GEN_OUTPUTS, defaultConfig: buildDefaults(ANSWER_GEN_FIELDS),
  },
  {
    type: "query-transformer", name: "Query Transformer Agent", category: "RAG",
    description: "Rewrites and expands queries for better retrieval recall.",
    summary: "Generates a query preprocessing layer that improves retrieval recall through rewriting and expansion strategies",
    color: "#F39C12", icon: "Wand2", inputs: ["query"], outputs: ["transformed queries"],
    fields: QUERY_TRANSFORMER_FIELDS, outputFields: QUERY_TRANSFORMER_OUTPUTS, defaultConfig: buildDefaults(QUERY_TRANSFORMER_FIELDS),
  },
  {
    type: "tool", name: "Tool Agent", category: "Orchestration",
    description: "Multi-tool LLM agent with configurable framework and memory.",
    summary: "Generates a multi-tool LLM agent with chosen framework, memory, and a configurable tool registry",
    color: "#3498DB", icon: "Wrench", inputs: ["task", "tools"], outputs: ["result", "trace"],
    fields: TOOL_FIELDS, outputFields: TOOL_OUTPUTS, defaultConfig: buildDefaults(TOOL_FIELDS),
  },
  {
    type: "video-gen", name: "Video Generation Agent", category: "Generative",
    description: "Creates videos from prompts using a chosen generation provider.",
    summary: "Generates a video creation pipeline for the chosen provider — from prompt to downloaded file",
    color: "#C0392B", icon: "Video", inputs: ["prompt", "config"], outputs: ["video file", "metadata"],
    fields: VIDEO_GEN_FIELDS, outputFields: VIDEO_GEN_OUTPUTS, defaultConfig: buildDefaults(VIDEO_GEN_FIELDS),
  },
  {
    type: "image-gen", name: "Image Generation Agent", category: "Generative",
    description: "Creates images from prompts using a chosen generation provider.",
    summary: "Generates an image creation pipeline for the chosen provider and mode — from prompt to saved file",
    color: "#00897B", icon: "ImageIcon", inputs: ["prompt", "config"], outputs: ["image files", "metadata"],
    fields: IMAGE_GEN_FIELDS, outputFields: IMAGE_GEN_OUTPUTS, defaultConfig: buildDefaults(IMAGE_GEN_FIELDS),
  },
  {
    type: "semantic-search", name: "Semantic Search Agent", category: "Search",
    description: "Full index-and-search pipeline: load, chunk, embed, store, query.",
    summary: "Generates a full index-and-search pipeline: load → chunk → embed → store → query, for the chosen source and store",
    color: "#1ABC9C", icon: "Search", inputs: ["documents", "query"], outputs: ["indexed chunks", "search results"],
    fields: SEMANTIC_SEARCH_FIELDS, outputFields: SEMANTIC_SEARCH_OUTPUTS, defaultConfig: buildDefaults(SEMANTIC_SEARCH_FIELDS),
  },
];

/* ================================================================== */
/*  WORKFLOWS                                                          */
/* ================================================================== */
export interface WorkflowSummary {
  id: string;
  name: string;
  description: string;
  status: WorkflowStatus;
  agentCount: number;
  lastRun: string;
  successRate: number;
  version: string;
  owner: string;
}

export const WORKFLOWS: WorkflowSummary[] = [
  { id: "wf_001", name: "RAG Knowledge Base", description: "Retrieval-augmented Q&A over docs", status: "published", agentCount: 5, lastRun: "2025-05-12T10:14:00Z", successRate: 0.97, version: "v1.4", owner: "anika.r" },
  { id: "wf_002", name: "Text-to-SQL Analyst", description: "Converts NL questions to SQL on Snowflake", status: "published", agentCount: 4, lastRun: "2025-05-13T08:02:00Z", successRate: 0.91, version: "v2.0", owner: "marcus.l" },
  { id: "wf_003", name: "Customer Support Router", description: "Triage agent for inbound tickets", status: "draft", agentCount: 6, lastRun: "2025-05-11T22:41:00Z", successRate: 0.84, version: "v0.3", owner: "priya.s" },
  { id: "wf_004", name: "Doc Summarizer", description: "Summarizes long PDFs with eval", status: "published", agentCount: 3, lastRun: "2025-05-13T07:55:00Z", successRate: 0.99, version: "v1.1", owner: "anika.r" },
  { id: "wf_005", name: "Eval Harness", description: "Batch evaluation pipeline", status: "draft", agentCount: 4, lastRun: "2025-05-10T18:00:00Z", successRate: 0.78, version: "v0.6", owner: "jordan.k" },
  { id: "wf_006", name: "Multi-Agent Researcher", description: "Web research + synthesis", status: "published", agentCount: 7, lastRun: "2025-05-13T06:11:00Z", successRate: 0.93, version: "v3.2", owner: "marcus.l" },
  { id: "wf_007", name: "Compliance Reviewer", description: "Reviews policy docs against rubric", status: "archived", agentCount: 5, lastRun: "2025-04-29T11:00:00Z", successRate: 0.88, version: "v1.0", owner: "priya.s" },
  { id: "wf_008", name: "Sales Enablement Bot", description: "Answers reps from CRM + KB", status: "published", agentCount: 6, lastRun: "2025-05-13T09:30:00Z", successRate: 0.95, version: "v2.1", owner: "jordan.k" },
];

/* ================================================================== */
/*  TEMPLATES                                                          */
/* ================================================================== */
export interface Template {
  id: string;
  name: string;
  description: string;
  agents: AgentType[];
  category: string;
}

export const TEMPLATES: Template[] = [
  { id: "tpl_rag", name: "RAG Pipeline", description: "Query → Transform → Retrieve → Answer → Evaluate", category: "Knowledge", agents: ["query-transformer", "retrieval", "answer-gen", "sql-insight"] },
  { id: "tpl_sql", name: "Text-to-SQL", description: "NL question → SQL generation → execution → answer", category: "Analytics", agents: ["query-transformer", "text-to-sql", "answer-gen"] },
  { id: "tpl_index", name: "Document Indexing", description: "Upload → chunk → embed → index", category: "Knowledge", agents: ["semantic-search"] },
  { id: "tpl_router", name: "Multi-Agent Router", description: "Classify intent → route to specialized agents", category: "Orchestration", agents: ["router", "tool", "tool", "mcp"] },
  { id: "tpl_eval", name: "Eval Harness", description: "Run dataset → collect → score with rubric", category: "Evaluation", agents: ["web-search", "sql-insight", "mcp"] },
  { id: "tpl_support", name: "Customer Support Agent", description: "Triage → retrieve KB → respond → escalate", category: "Support", agents: ["router", "retrieval", "answer-gen", "email-gen"] },
];

/* ================================================================== */
/*  RUNS                                                               */
/* ================================================================== */
export interface RunStep {
  nodeId: string;
  agent: AgentType;
  label: string;
  status: RunStatus;
  latencyMs: number;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
}

export interface Run {
  id: string;
  workflowId: string;
  workflowName: string;
  status: RunStatus;
  startedAt: string;
  durationMs: number;
  tokens: number;
  cost: number;
  steps: RunStep[];
}

const seedSteps = (wf: string): RunStep[] => [
  { nodeId: "n1", agent: "query-transformer", label: "Query Transformer", status: "success", latencyMs: 312, input: { query: "What were Q1 revenues?" }, output: { transformed: "Total revenue Q1 2025" } },
  { nodeId: "n2", agent: "retrieval", label: "Retrieval Agent", status: "success", latencyMs: 514, input: { query: "Total revenue Q1 2025" }, output: { documents: ["doc_12", "doc_45", "doc_77"] } },
  { nodeId: "n3", agent: "answer-gen", label: "Answer Generation", status: "success", latencyMs: 1820, input: { docs: 3 }, output: { answer: `Q1 revenue was $42.1M, +12% YoY. (workflow ${wf})` } },
  { nodeId: "n4", agent: "sql-insight", label: "SQL Insight Agent", status: "success", latencyMs: 410, input: { answer: "..." }, output: { score: 0.92, feedback: "Accurate and concise." } },
];

export const RUNS: Run[] = Array.from({ length: 32 }).map((_, i) => {
  const wf = WORKFLOWS[i % WORKFLOWS.length];
  const statuses: RunStatus[] = ["success", "success", "success", "success", "failed", "running"];
  const status = statuses[i % statuses.length];
  return {
    id: `run_${(1000 + i).toString()}`,
    workflowId: wf.id,
    workflowName: wf.name,
    status,
    startedAt: new Date(Date.now() - i * 1000 * 60 * 47).toISOString(),
    durationMs: 1200 + (i * 137) % 4800,
    tokens: 800 + (i * 213) % 6400,
    cost: +(0.002 + (i % 17) * 0.0011).toFixed(4),
    steps: seedSteps(wf.id),
  };
});

/* ================================================================== */
/*  CREDENTIALS                                                        */
/* ================================================================== */
export interface Credential {
  id: string;
  name: string;
  provider: string;
  type: "api_key" | "connection_string" | "oauth";
  masked: string;
  envRef: string;
  createdAt: string;
}

export const CREDENTIALS: Credential[] = [
  { id: "cred_1", name: "OpenAI Production", provider: "OpenAI", type: "api_key", masked: "sk-••••••••••••a91f", envRef: "${OPENAI_API_KEY}", createdAt: "2025-04-01T10:00:00Z" },
  { id: "cred_2", name: "Pinecone Vector", provider: "Pinecone", type: "api_key", masked: "pc-••••••••••••3ee2", envRef: "${PINECONE_API_KEY}", createdAt: "2025-04-12T10:00:00Z" },
  { id: "cred_3", name: "Snowflake Warehouse", provider: "Snowflake", type: "connection_string", masked: "snowflake://••••@analytics", envRef: "${SNOWFLAKE_DSN}", createdAt: "2025-03-21T10:00:00Z" },
  { id: "cred_4", name: "Postgres Reporting", provider: "Postgres", type: "connection_string", masked: "postgres://••••@db/reporting", envRef: "${PG_DSN}", createdAt: "2025-02-08T10:00:00Z" },
  { id: "cred_5", name: "Anthropic", provider: "Anthropic", type: "api_key", masked: "sk-ant-••••••••f12c", envRef: "${ANTHROPIC_API_KEY}", createdAt: "2025-04-22T10:00:00Z" },
  { id: "cred_6", name: "Internal HTTP API", provider: "HTTP", type: "api_key", masked: "Bearer ••••••••8821", envRef: "${INTERNAL_API_TOKEN}", createdAt: "2025-04-18T10:00:00Z" },
  { id: "cred_7", name: "Redis Memory", provider: "Redis", type: "connection_string", masked: "redis://••••@cache:6379", envRef: "${REDIS_URL}", createdAt: "2025-03-30T10:00:00Z" },
  { id: "cred_8", name: "Google OAuth", provider: "Google", type: "oauth", masked: "oauth2:••••••••drive", envRef: "${GOOGLE_OAUTH}", createdAt: "2025-05-02T10:00:00Z" },
];

/* ================================================================== */
/*  CHART DATA                                                         */
/* ================================================================== */
export const RUNS_OVER_TIME = Array.from({ length: 14 }).map((_, i) => ({
  day: `D-${13 - i}`,
  success: 30 + Math.floor(Math.random() * 25),
  failed: Math.floor(Math.random() * 6),
}));

export const AGENT_USAGE = AGENT_REGISTRY.map((a) => ({
  name: a.name.replace(" Agent", ""),
  uses: 20 + Math.floor(Math.random() * 180),
}));
