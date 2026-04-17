from __future__ import annotations

from dataclasses import dataclass

from agno.workflow import Workflow

from app.services.content_generation import ContentWorkflowProvider, GeneratedContentBundle


@dataclass(slots=True)
class WorkflowExecutionSummary:
    workflow_name: str
    team_name: str
    agent_names: list[str]


class YoutubeContentWorkflow:
    def __init__(
        self,
        workflow: Workflow,
        provider: ContentWorkflowProvider,
        team_name: str,
        agent_names: list[str],
    ) -> None:
        self._workflow = workflow
        self._provider = provider
        self._summary = WorkflowExecutionSummary(
            workflow_name=workflow.name or "youtube_content_pipeline",
            team_name=team_name,
            agent_names=agent_names,
        )

    @property
    def summary(self) -> WorkflowExecutionSummary:
        return self._summary

    def run(self, *, video_idea: str, title_hint: str) -> GeneratedContentBundle:
        bundle = self._provider.generate(video_idea=video_idea, title_hint=title_hint)
        return GeneratedContentBundle(
            briefing=bundle.briefing,
            script=bundle.script,
            metadata=bundle.metadata,
            production_plan=bundle.production_plan,
            workflow_name=self._summary.workflow_name,
            team_name=self._summary.team_name,
            agent_names=self._summary.agent_names,
        )
