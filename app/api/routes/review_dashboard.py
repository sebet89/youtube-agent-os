from __future__ import annotations

from html import escape
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_human_review_dashboard_service
from app.services.review import HumanReviewDashboardService, ReviewDashboardSnapshot

router = APIRouter(prefix="/review", include_in_schema=False)


@router.get(
    "/projects/{project_id}",
    response_class=HTMLResponse,
    name="get_project_review_dashboard",
)
def get_project_review_dashboard(
    project_id: str,
    review_service: Annotated[
        HumanReviewDashboardService, Depends(get_human_review_dashboard_service)
    ],
    session: Annotated[Session, Depends(get_db_session)],
) -> HTMLResponse:
    try:
        snapshot = review_service.get_project_snapshot(session, project_id=project_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return HTMLResponse(content=_render_review_dashboard(snapshot))


def _render_review_dashboard(snapshot: ReviewDashboardSnapshot) -> str:
    assets_html = "".join(
        (
            "<li>"
            f"<strong>{escape(asset.asset_type)}</strong> - "
            f"{escape(asset.status)} - "
            f"{escape(asset.storage_path or 'sem caminho')} "
            f"({escape(asset.source_adapter)})"
            "</li>"
        )
        for asset in snapshot.assets
    ) or "<li>Nenhum asset preparado ainda.</li>"
    jobs_html = "".join(
        (
            "<li>"
            f"<strong>{escape(job.job_type)}</strong> - "
            f"{escape(job.status)} - fila {escape(job.queue_name)}"
            f"{_format_optional_job_id(job.celery_task_id)}"
            "</li>"
        )
        for job in snapshot.jobs
    ) or "<li>Nenhum job registrado.</li>"

    generated_title = escape(snapshot.generated_title or "Ainda nao gerado")
    generated_description = escape(snapshot.generated_description or "Ainda nao gerado")
    generated_tags = ", ".join(snapshot.generated_tags) or "Ainda nao gerado"
    generated_script = escape(snapshot.generated_script or "Ainda nao gerado")
    thumbnail_prompt = escape(snapshot.thumbnail_prompt or "Ainda nao gerado")
    production_plan = escape(snapshot.production_plan or "Ainda nao gerado")
    rendered_video_path = escape(snapshot.rendered_video_path or "")
    youtube_video_label = escape(snapshot.youtube_video_id or "Ainda nao enviado")
    rendered_video_label = escape(snapshot.rendered_video_path or "Ainda nao renderizado")
    scheduled_publish_label = escape(
        snapshot.scheduled_publish_at.isoformat()
        if snapshot.scheduled_publish_at
        else "Nao agendado"
    )
    scheduled_task_label = escape(snapshot.scheduled_publish_task_id or "Nenhuma task pendente")
    generated_tags_label = escape(generated_tags)
    subtitle_preview = escape(
        snapshot.subtitle_preview or "As legendas aparecem depois do preparo de assets."
    )
    youtube_thumbnail_status = (
        "Thumbnail selecionada ja enviada ao YouTube"
        if snapshot.youtube_thumbnail_uploaded
        else "Thumbnail ainda nao enviada ao YouTube"
    )
    youtube_caption_status = (
        f"Legenda enviada ao YouTube ({escape(snapshot.uploaded_caption_language or 'pt-BR')})"
        if snapshot.youtube_captions_uploaded
        else "Legenda ainda nao enviada ao YouTube"
    )
    latest_view_count = str(snapshot.latest_view_count or 0)
    latest_like_count = str(snapshot.latest_like_count or 0)
    latest_comment_count = str(snapshot.latest_comment_count or 0)
    upload_button_disabled = "disabled" if not snapshot.rendered_video_path else ""
    prepare_button_disabled = ""
    publish_button_disabled = (
        "disabled"
        if snapshot.review_status != "approved" or snapshot.youtube_video_id is None
        else ""
    )
    rendered_video_preview = (
        f"""
        <video
          controls
          preload="metadata"
          style="width:100%;border-radius:16px;border:1px solid var(--border);background:#140f0c;"
          src="/api/v1/projects/{escape(snapshot.project_id)}/artifacts/rendered-video"
        ></video>
        <p class="hint">Arquivo local: {rendered_video_label}</p>
        """
        if snapshot.rendered_video_path
        else "<p class=\"hint\">O preview em video aparece assim que o render terminar.</p>"
    )
    thumbnail_preview = (
        f"""
        <img
          src="/api/v1/projects/{escape(snapshot.project_id)}/artifacts/thumbnail"
          alt="Thumbnail gerada"
          style="width:100%;border-radius:16px;border:1px solid var(--border);background:#fff;"
        >
        <p class="hint">Thumbnail local pronta para revisao.</p>
        """
        if snapshot.thumbnail_asset_path
        else "<p class=\"hint\">A thumbnail aparece depois do preparo de assets.</p>"
    )
    thumbnail_gallery = "".join(
        (
            "<article class=\"thumbnail-card\">"
            f"<img src=\"/api/v1/projects/{escape(snapshot.project_id)}/artifacts/thumbnail/"
            f"{escape(variant.asset_id)}\" "
            f"alt=\"{escape(variant.label)}\" class=\"thumbnail-variant-image\">"
            f"<p><strong>{escape(variant.label)}</strong></p>"
            f"<p class=\"hint\">"
            f"{'Selecionada para upload' if variant.is_selected else 'Disponivel para selecao'}"
            "</p>"
            f"<p class=\"hint\">"
            f"{'Ja enviada ao YouTube' if variant.uploaded_to_youtube else 'Ainda nao enviada'}"
            "</p>"
            f"<button type=\"button\" {'disabled' if variant.is_selected else ''} "
            f"onclick=\"selectThumbnail('{escape(variant.asset_id)}')\">"
            f"{'Selecionada' if variant.is_selected else 'Usar esta thumbnail'}"
            "</button>"
            "</article>"
        )
        for variant in snapshot.thumbnail_variants
    ) or "<p class=\"hint\">As variacoes de thumbnail aparecem depois do preparo de assets.</p>"
    events_html = "".join(
        (
            "<li>"
            f"<strong>{escape(event.message)}</strong><br>"
            f"<span class=\"hint\">{escape(event.created_at)} | {escape(event.event_type)}</span>"
            "</li>"
        )
        for event in snapshot.events
    ) or "<li>Nenhum evento operacional registrado ainda.</li>"

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Review | {escape(snapshot.idea_title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4efe6;
      --panel: #fffaf2;
      --ink: #1f2328;
      --accent: #1d6f5f;
      --accent-strong: #13473d;
      --danger: #aa3a2a;
      --border: #dfd3c3;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", sans-serif;
      background: radial-gradient(circle at top, #fffdf9 0%, var(--bg) 60%);
      color: var(--ink);
    }}
    main {{
      max-width: 1080px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    .hero, .panel {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 22px;
      box-shadow: 0 18px 40px rgba(48, 42, 33, 0.08);
      margin-bottom: 18px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 18px;
    }}
    .badge {{
      display: inline-block;
      padding: 6px 10px;
      border-radius: 999px;
      background: #e8f3ef;
      color: var(--accent-strong);
      font-size: 14px;
      margin-right: 8px;
      margin-bottom: 8px;
    }}
    h1, h2, h3 {{ margin-top: 0; }}
    p, li {{ line-height: 1.5; }}
    textarea, input {{
      width: 100%;
      border-radius: 12px;
      border: 1px solid var(--border);
      padding: 10px 12px;
      font: inherit;
      margin-bottom: 10px;
      background: #fff;
    }}
    button {{
      border: 0;
      border-radius: 12px;
      padding: 10px 14px;
      font: inherit;
      cursor: pointer;
      background: var(--accent);
      color: #fff;
      margin-right: 8px;
      margin-bottom: 8px;
    }}
    button.secondary {{ background: #7d6852; }}
    button.danger {{ background: var(--danger); }}
    button:disabled {{
      opacity: 0.5;
      cursor: not-allowed;
    }}
    pre {{
      white-space: pre-wrap;
      word-break: break-word;
      background: #fff;
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 12px;
    }}
    .hint {{
      color: #665d52;
      font-size: 14px;
    }}
    .stack {{
      display: grid;
      gap: 14px;
    }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 12px;
    }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 18px;
    }}
    .meta-grid article {{
      background: #fff;
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 14px;
    }}
    .thumbnail-gallery {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
    }}
    .thumbnail-card {{
      background: #fff;
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 14px;
    }}
    .thumbnail-variant-image {{
      width: 100%;
      border-radius: 14px;
      border: 1px solid var(--border);
      background: #fff;
      margin-bottom: 10px;
    }}
    .timeline-list {{
      list-style: none;
      padding: 0;
      margin: 0;
      display: grid;
      gap: 12px;
    }}
    .timeline-list li {{
      background: #fff;
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 12px;
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>Painel de revisao humana</h1>
      <p>{escape(snapshot.idea_title)}</p>
      <div>
        <span class="badge">Ideia: {escape(snapshot.idea_status)}</span>
        <span class="badge">Review: {escape(snapshot.review_status)}</span>
        <span class="badge">YouTube: {escape(snapshot.visibility)}</span>
        <span class="badge">Agendado: {scheduled_publish_label}</span>
      </div>
      <p><strong>Project ID:</strong> {escape(snapshot.project_id)}</p>
      <p><strong>YouTube Video ID:</strong> {youtube_video_label}</p>
      <p><strong>Task agendada:</strong> {scheduled_task_label}</p>
      <p><strong>Ideia original:</strong> {escape(snapshot.raw_idea)}</p>
      <div class="actions">
        <button
          type="button"
          {prepare_button_disabled}
          onclick="prepareVideo()"
        >Preparar video automaticamente</button>
        <button
          type="button"
          class="secondary"
          onclick="scrollToMetadata()"
        >Editar metadados antes de publicar</button>
      </div>
    </section>

    <section class="grid">
      <article class="panel">
        <h2>Conteudo gerado</h2>
        <p><strong>Titulo:</strong> {generated_title}</p>
        <p><strong>Descricao:</strong> {generated_description}</p>
        <p><strong>Tags:</strong> {generated_tags_label}</p>
        <p><strong>Thumbnail prompt:</strong> {thumbnail_prompt}</p>
        <p><strong>Plano de producao:</strong></p>
        <pre>{production_plan}</pre>
        <p><strong>Roteiro:</strong></p>
        <pre>{generated_script}</pre>
      </article>

      <article class="panel">
        <h2>Assets e jobs</h2>
        <p><strong>Video renderizado:</strong> {rendered_video_label}</p>
        <p>
          <strong>Analytics atuais:</strong>
          views {latest_view_count} | likes {latest_like_count} | comentarios {latest_comment_count}
        </p>
        <h3>Assets</h3>
        <ul>{assets_html}</ul>
        <h3>Jobs</h3>
        <ul>{jobs_html}</ul>
      </article>
    </section>

    <section class="panel stack">
      <div class="meta-grid">
        <article>
          <h3>Pacote YouTube</h3>
          <p><strong>Thumbnail:</strong> {escape(youtube_thumbnail_status)}</p>
          <p><strong>Legenda:</strong> {youtube_caption_status}</p>
          <p class="hint">
            Esse bloco mostra o que ja foi anexado ao upload privado atual.
          </p>
        </article>
        <article>
          <h3>Thumbnail ativa</h3>
          {thumbnail_preview}
        </article>
      </div>
    </section>

    <section class="panel stack">
      <div>
        <h2>Linha do tempo operacional</h2>
        <p class="hint">
          Historico mais recente do projeto para auditoria rapida de upload, review e publicacao.
        </p>
      </div>
      <ul class="timeline-list">{events_html}</ul>
    </section>

    <section class="panel stack">
      <div>
        <h2>Preview de material</h2>
        <p class="hint">
          Tudo que for ajustado aqui permanece no projeto antes do upload e da publicacao.
        </p>
      </div>
      <div class="meta-grid">
        <article>
          <h3>Video renderizado</h3>
          {rendered_video_preview}
        </article>
      </div>
    </section>

    <section class="panel stack">
      <div>
        <h2>Legenda e thumbnails</h2>
        <p class="hint">
          Escolha a melhor thumbnail e confira as legendas antes do upload privado.
        </p>
      </div>
      <div class="meta-grid">
        <article>
          <h3>Preview de legenda</h3>
          <pre>{subtitle_preview}</pre>
        </article>
        <article>
          <h3>Variacoes de thumbnail</h3>
          <div class="thumbnail-gallery">{thumbnail_gallery}</div>
        </article>
      </div>
    </section>

    <section class="panel" id="metadata-editor">
      <h2>Editar metadados</h2>
      <p class="hint">Use esta secao para ajustar o pacote final sem voltar para o Studio.</p>
      <input
        id="metadata-title"
        name="generated_title"
        value="{escape(snapshot.generated_title or '')}"
        placeholder="Titulo final do video"
      >
      <textarea
        id="metadata-description"
        name="generated_description"
        rows="4"
        placeholder="Descricao final do video"
      >{escape(snapshot.generated_description or '')}</textarea>
      <input
        id="metadata-tags"
        name="generated_tags"
        value="{escape(', '.join(snapshot.generated_tags))}"
        placeholder="tags, separadas, por, virgula"
      >
      <textarea
        id="metadata-thumbnail-prompt"
        name="thumbnail_prompt"
        rows="3"
        placeholder="Prompt final de thumbnail"
      >{escape(snapshot.thumbnail_prompt or '')}</textarea>
      <button type="button" onclick="saveMetadata()">Salvar metadados</button>
    </section>

    <section class="grid">
      <article class="panel">
        <h2>Upload privado</h2>
        <p class="hint">O upload continua saindo como <code>private</code> por padrao.</p>
        <input
          id="file-path"
          name="file_path"
          value="{rendered_video_path}"
          placeholder="Caminho do video renderizado"
        >
        <button
          type="button"
          {upload_button_disabled}
          onclick="uploadVideo()"
        >Enviar para YouTube</button>
      </article>

      <article class="panel">
        <h2>Revisao humana</h2>
        <input id="reviewer-name" name="reviewer_name" placeholder="Nome do revisor">
        <textarea
          id="review-notes"
          name="notes"
          rows="4"
          placeholder="Notas de aprovacao ou ajustes"
        ></textarea>
        <button type="button" onclick="approveProject()">Aprovar publicacao</button>
        <button type="button" class="danger" onclick="rejectProject()">Rejeitar publicacao</button>
      </article>

      <article class="panel">
        <h2>Publicacao final</h2>
        <p class="hint">
          A publicacao em <code>public</code> so e liberada apos aprovacao humana
          e upload previo.
        </p>
        <input
          id="schedule-publish-at"
          name="publish_at"
          type="datetime-local"
          value=""
        >
        <button
          type="button"
          class="secondary"
          onclick="schedulePublication()"
        >Agendar ou reagendar</button>
        <button
          type="button"
          class="danger"
          onclick="cancelScheduledPublication()"
        >Cancelar agendamento</button>
        <button
          type="button"
          class="secondary"
          {publish_button_disabled}
          onclick="publishProject()"
        >Publicar agora</button>
        <button type="button" onclick="collectAnalytics()">Atualizar analytics</button>
      </article>
    </section>
  </main>
  <script>
    async function postJson(url, payload) {{
      const response = await fetch(url, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload)
      }});
      if (!response.ok) {{
        const error = await response.json().catch(() => ({{ detail: "Erro inesperado" }}));
        throw new Error(error.detail || "Erro inesperado");
      }}
      return response.json();
    }}

    async function patchJson(url, payload) {{
      const response = await fetch(url, {{
        method: "PATCH",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload)
      }});
      if (!response.ok) {{
        const error = await response.json().catch(() => ({{ detail: "Erro inesperado" }}));
        throw new Error(error.detail || "Erro inesperado");
      }}
      return response.json();
    }}

    function requireReviewer() {{
      const reviewerName = document.getElementById("reviewer-name").value.trim();
      if (!reviewerName) {{
        throw new Error("Informe o nome do revisor.");
      }}
      return reviewerName;
    }}

    function scrollToMetadata() {{
      document
        .getElementById("metadata-editor")
        .scrollIntoView({{ behavior: "smooth", block: "start" }});
    }}

    async function saveMetadata() {{
      try {{
        const tags = document
          .getElementById("metadata-tags")
          .value
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean);
        await patchJson("/api/v1/projects/{escape(snapshot.project_id)}/metadata", {{
          generated_title: document.getElementById("metadata-title").value.trim() || null,
          generated_description:
            document.getElementById("metadata-description").value.trim() || null,
          generated_tags: tags,
          thumbnail_prompt:
            document.getElementById("metadata-thumbnail-prompt").value.trim() || null
        }});
        window.location.reload();
      }} catch (error) {{
        alert(error.message);
      }}
    }}

    async function selectThumbnail(assetId) {{
      try {{
        await patchJson("/api/v1/projects/{escape(snapshot.project_id)}/thumbnail-selection", {{
          asset_id: assetId
        }});
        window.location.reload();
      }} catch (error) {{
        alert(error.message);
      }}
    }}

    async function uploadVideo() {{
      try {{
        const filePath = document.getElementById("file-path").value.trim();
        if (!filePath) {{
          throw new Error("Informe o caminho do video renderizado.");
        }}
        await postJson(
          "/api/v1/projects/{escape(snapshot.project_id)}/youtube/upload",
          {{ file_path: filePath }}
        );
        window.location.reload();
      }} catch (error) {{
        alert(error.message);
      }}
    }}

    async function approveProject() {{
      try {{
        await postJson("/api/v1/projects/{escape(snapshot.project_id)}/review/approve", {{
          reviewer_name: requireReviewer(),
          notes: document.getElementById("review-notes").value.trim() || null
        }});
        window.location.reload();
      }} catch (error) {{
        alert(error.message);
      }}
    }}

    async function rejectProject() {{
      try {{
        await postJson("/api/v1/projects/{escape(snapshot.project_id)}/review/reject", {{
          reviewer_name: requireReviewer(),
          notes: document.getElementById("review-notes").value.trim() || null
        }});
        window.location.reload();
      }} catch (error) {{
        alert(error.message);
      }}
    }}

    async function publishProject() {{
      try {{
        await postJson("/api/v1/projects/{escape(snapshot.project_id)}/youtube/publish", {{}});
        window.location.reload();
      }} catch (error) {{
        alert(error.message);
      }}
    }}

    async function schedulePublication() {{
      try {{
        const publishAtValue = document.getElementById("schedule-publish-at").value;
        if (!publishAtValue) {{
          throw new Error("Escolha uma data e hora para o agendamento.");
        }}
        await postJson("/api/v1/projects/{escape(snapshot.project_id)}/youtube/schedule", {{
          publish_at: new Date(publishAtValue).toISOString()
        }});
        window.location.reload();
      }} catch (error) {{
        alert(error.message);
      }}
    }}

    async function cancelScheduledPublication() {{
      try {{
        await postJson(
          "/api/v1/projects/{escape(snapshot.project_id)}/youtube/schedule/cancel",
          {{}}
        );
        window.location.reload();
      }} catch (error) {{
        alert(error.message);
      }}
    }}

    async function collectAnalytics() {{
      try {{
        await postJson("/api/v1/projects/{escape(snapshot.project_id)}/analytics/collect", {{}});
        window.location.reload();
      }} catch (error) {{
        alert(error.message);
      }}
    }}

    async function prepareVideo() {{
      try {{
        await postJson("/api/v1/projects/{escape(snapshot.project_id)}/prepare-video", {{}});
        window.location.reload();
      }} catch (error) {{
        alert(error.message);
      }}
    }}
  </script>
</body>
</html>"""


def _format_optional_job_id(celery_task_id: str | None) -> str:
    if celery_task_id is None:
        return ""
    return f" - task {escape(celery_task_id)}"
