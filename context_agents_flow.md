# PHASE 4: SINGLE-DOMAIN ROUTING & CONTEXT AGENT EXECUTION MATRIX

**Subsystem Reference:** Input Validation, Intent Discrimination, and Domain-Isolated RAG

**Infrastructure Target:** Bare-Metal NVIDIA H200 Cluster (`node-04`) — GPU 0-1 (Inference), GPU 4 (Vector Core)

**Operational Classification:** Production Integration Technical Document

---

## 📋 Step 1: The Inbound Gate (GR-In)

**Operational Objective:** Establish an immutable security and topical perimeter before invoking any generative or parsing models, eliminating unnecessary GPU cycle expenditure on invalid inputs.

* [ ] **Colang Policy Binding:** Load and compile the baseline `config.yml` configuration tree and initialization scripts for the NVIDIA NeMo Guardrails engine.
* [ ] **Input Rail Activation:** Enforce an inbound validation rail to intercept prompt injection vectors, malicious execution scripting, and advanced jailbreak syntaxes before token extraction passes.
* [ ] **Topical Perimeter Check:** Enforce rigid domain-classification rules. If an incoming prompt falls outside the three certified enterprise business domains (`Tourism`, `Fishery/Commercial Fleet`, or `Construction`), the gate must intercept the request payload, log a standard out-of-scope exception, and terminate the graph trace execution immediately.
* [ ] **Handoff Deserialization:** Pass the sanitized string token directly to the parsing layer payload signature without mutating the original user context.

---

## 📋 Step 2: The Discriminator Node (Orchestrator)

**Operational Objective:** Perform single-intent extraction to determine the target domain context agent while executing zero vector or meteorological operations at this layer.

* [ ] **Schema Constraint Enforcement:** Invoke the local NIM LLM instance on GPUs 0-1 using strict JSON-schema tracking forced directly by the `DiscriminatorRoutingMatrix` structured output model.
* [ ] **Intent Truncation Logic:** Force the model's top-k choice parameters to resolve exactly one primary intent string primitive: `tourism`, `fishery`, `construction`, or `REJECT_OUT_OF_SCOPE`. Secondary intents must be explicitly truncated from the output state object.
* [ ] **Extraction Key Isolation:** Isolate the target entity parameter (`extraction_key`) from the token stream (e.g., matching a localized site index, coordinate string layout, or place name).
* [ ] **State Population:** Write the `primary_intent`, `routing_confidence`, and `extraction_key` primitives natively into the LangGraph global state container, exiting the execution node synchronously.

---

## 📋 Step 3: The Conditional Edge (Switch-Block)

**Operational Objective:** Execute deterministic routing of the state token to a single context agent node, bypassing parallel fan-out or task allocation risks.

* [ ] **Route Parameter Evaluation:** Construct a synchronous LangGraph router function tasked exclusively with reading the state data matrix generated in Step 2.
* [ ] **String-to-Node Mapping:** Map the extracted `primary_intent` string directly to the target processing node identifiers:
* `tourism` $\rightarrow$ `tourism_context_agent`
* `fishery` $\rightarrow$ `fishery_context_agent`
* `construction` $\rightarrow$ `construction_context_agent`


* [ ] **Exception Redirection:** If `primary_intent` is flagged as `REJECT_OUT_OF_SCOPE` or if the calculated value falls below a strict `routing_confidence` threshold metric of $0.70$, bypass the domain context agents completely and route the state object straight to the terminal error handler.
* [ ] **Parallel Thread Locking:** Ensure zero concurrent threads are instantiated at this junction. The LangGraph routing map must return exactly one scalar string target, passing the single execution token forward.

---

## 📋 Step 4: The Context Agent Loop

**Operational Objective:** Execute domain-isolated data gathering by intersecting static vector lookups with dynamic professional MCP fallbacks, completely divorced from meteorological processing.

* [ ] **First-Pass Schema Population:** Instantiate the targeted agent context layer and populate the `AgentExecutionPlan` validation schema using the state's isolated `extraction_key`.
* [ ] **Vector Store Hybrid Interrogation (Tier 1):** Execute an asynchronous vector similarity search against the assigned Milvus database collection using `nv-embedqa-e5-v5` on GPU 4. Fetch static parameters, structural safety margins, and localized coordinates from the collection metadata arrays.
* [ ] **Professional MCP Server Invocation (Tier 2 Fallback):** If the Milvus vector lookup returns an empty array, or if the connection pool triggers a timeout exception, intercept the error and execute a fallback call across the network to the assigned Professional Model Context Protocol (MCP) server. Extract the live operational data structures (e.g., active port capacity markers, live structural concrete logs, or museum scheduling states) directly from the server stream.
* [ ] **Polymorphic Serialization:** Ingest the data payloads harvested from Tier 1 or Tier 2. Instantiate and fill the explicit domain model object layout: `TourismDomainSchema`, `FisheryDomainSchema`, or `ConstructionDomainSchema`.
* [ ] **Envelope Assembly:** Encapsulate the completed domain schema inside the unified `ContextAgentPayload` class wrapper. Set `execution_status` cleanly to `SUCCESS_RAG` or `SUCCESS_MCP_FALLBACK`.

---

## 📋 Step 4.2: Terminal Handoff

**Operational Objective:** Format and attach the exclusive, non-generative data contract to the state matrix, transferring graph control cleanly to the downstream Intelligence Layer.

* [ ] **Zero-Prose Cleansing:** Scrutinize the payload string parameters. Ensure no conversational sentences, advisory text, or descriptive filler tokens have been generated by the Context Agent. The data structure must contain only raw parameters and metadata.
* [ ] **Exclusivity Verification:** Run internal validation to ensure that only the single data block corresponding to the active domain is populated within the outbound object, leaving the remaining two domain reference schemas strictly `null`.
* [ ] **State Transition Invalidation:** Lock the completed `ContextAgentPayload` instance against mutation. Append the serialized schema object directly into the global LangGraph state container.
* [ ] **Downstream Signal Generation:** Terminate node execution. Hand off the finalized data block to the independent engineering cell managing the terminal Intelligence Layer, signaling readiness for weather mashing and final client streaming.