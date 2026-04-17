from __future__ import annotations

from typing import cast

from app.agents.factory import AgentFactory
from app.core.config import Settings
from app.services.content_generation import (
    ContentWorkflowProvider,
    GeneratedContentBundle,
    GeneratedMetadata,
)
from app.workflows.content_pipeline import YoutubeContentWorkflow


class DeterministicContentGenerator(ContentWorkflowProvider):
    def generate(self, *, video_idea: str, title_hint: str) -> GeneratedContentBundle:
        sanitized_title = title_hint.strip() or "Novo Video"
        short_idea = video_idea.strip() or "Ideia sem detalhes"
        tags = [
            "youtube",
            "automation",
            "ai-agent",
            sanitized_title.lower().replace(" ", "-"),
        ]
        return GeneratedContentBundle(
            briefing=(
                f"Objetivo: transformar a ideia '{short_idea}' em um video claro para YouTube.\n"
                "Publico: criadores e operadores de canais.\n"
                "Gancho: mostrar um fluxo simples e pratico.\n"
                "Tom: direto, confiante e util."
            ),
            script=(
                f"Abertura: apresentar '{sanitized_title}'.\n"
                f"Contexto: explicar a dor central ligada a '{short_idea}'.\n"
                "Demonstracao: mostrar o passo a passo principal.\n"
                "Encerramento: reforcar o resultado e proximo passo."
            ),
            metadata=GeneratedMetadata(
                title=f"{sanitized_title}: fluxo assistido para YouTube",
                description=(
                    f"Neste video mostramos como executar '{short_idea}' com um fluxo assistido. "
                    "Cobrimos briefing, roteiro, metadados, producao e publicacao."
                ),
                tags=tags,
                thumbnail_prompt=(
                    "High-contrast YouTube thumbnail, clean layout, creator dashboard, "
                    "AI workflow arrows, bold headline, no clutter"
                ),
            ),
            production_plan=(
                "1. Gravar abertura curta.\n"
                "2. Capturar demo do sistema.\n"
                "3. Inserir supporting visuals e captions.\n"
                "4. Revisar CTA final e exportar versao MVP."
            ),
            workflow_name="youtube_content_pipeline",
            team_name="youtube-content-team",
            agent_names=[
                "briefing-agent",
                "script-agent",
                "metadata-agent",
                "production-agent",
            ],
        )


class AgnoContentWorkflowAdapter(ContentWorkflowProvider):
    def __init__(self, settings: Settings) -> None:
        self._factory = AgentFactory(model=settings.agno_model_id)
        self._team = self._factory.build_content_team()
        self._workflow = self._factory.build_workflow()
        self._fallback_provider = DeterministicContentGenerator()

    def generate(self, *, video_idea: str, title_hint: str) -> GeneratedContentBundle:
        members = cast(list[object], self._team.members)
        workflow = YoutubeContentWorkflow(
            workflow=self._workflow,
            provider=self._fallback_provider,
            team_name=self._team.name or "youtube-content-team",
            agent_names=[str(getattr(member, "name", "agent")) for member in members],
        )
        return workflow.run(video_idea=video_idea, title_hint=title_hint)
