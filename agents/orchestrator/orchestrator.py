"""
Orchestrator Agent — routes parsed JSON to the correct Context Agent.
Uses LangGraph state machine for workflow control.
"""
from agents.orchestrator.state import WorkflowState
from agents.context_agents.tourism_agent.agent import TourismContextAgent
from agents.context_agents.construction_agent.agent import ConstructionContextAgent
from agents.context_agents.agriculture_agent.agent import AgricultureContextAgent
from apps.api.app.schemas.context_schema import ParserOutput, FullyProcessedPayload


class Orchestrator:
    def __init__(self):
        self.agents = {
            "tourism": TourismContextAgent(),
            "construction": ConstructionContextAgent(),
            "agriculture": AgricultureContextAgent(),
        }

    async def run(self, parsed: ParserOutput) -> FullyProcessedPayload:
        """Route parser output to the correct context agent."""
        domain = parsed.domain.lower()

        print(f"[Orchestrator] Domain detected: {domain}")

        agent = self.agents.get(domain)
        if agent is None:
            print(f"[Orchestrator] Unknown domain '{domain}', falling back to tourism agent")
            agent = self.agents["tourism"]

        # Context agent fills involved_context, queries KB, calls MCP
        processed = await agent.process(parsed)
        return processed
