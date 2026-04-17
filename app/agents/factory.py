from __future__ import annotations

from typing import cast

from agno.agent import Agent
from agno.team import Team
from agno.workflow import Workflow


class AgentFactory:
    def __init__(self, model: str | None = None) -> None:
        self._model = model

    def build_briefing_agent(self) -> Agent:
        return Agent(
            model=self._model,
            name="briefing-agent",
            role="briefing specialist",
            instructions=[
                "Analyze the raw video idea and produce a concise strategic briefing.",
                "Focus on audience, hook, promise, tone, and structure.",
            ],
        )

    def build_script_agent(self) -> Agent:
        return Agent(
            model=self._model,
            name="script-agent",
            role="scriptwriter",
            instructions=[
                "Turn the approved briefing into a clear YouTube script.",
                "Keep the pacing practical and friendly for a production team.",
            ],
        )

    def build_metadata_agent(self) -> Agent:
        return Agent(
            model=self._model,
            name="metadata-agent",
            role="metadata strategist",
            instructions=[
                "Generate title, description, tags, and thumbnail prompt.",
                "Optimize for clarity, click-through, and YouTube discoverability.",
            ],
        )

    def build_production_agent(self) -> Agent:
        return Agent(
            model=self._model,
            name="production-agent",
            role="production planner",
            instructions=[
                "Generate a production plan covering scenes, assets, and editing steps.",
                "Keep the output practical for an MVP video pipeline.",
            ],
        )

    def build_content_team(self) -> Team:
        members = cast(
            list[Agent | Team],
            [
            self.build_briefing_agent(),
            self.build_script_agent(),
            self.build_metadata_agent(),
            self.build_production_agent(),
            ],
        )
        return Team(
            members=members,
            model=self._model,
            name="youtube-content-team",
            description="Agno team that coordinates content generation for a YouTube video.",
            instructions=[
                "Coordinate specialists to produce briefing, script, metadata, "
                "and production plan.",
                "Preserve consistency across all generated artifacts.",
            ],
        )

    def build_workflow(self) -> Workflow:
        return Workflow(
            name="youtube_content_pipeline",
            description="Workflow that orchestrates the YouTube content generation pipeline.",
        )
