from __future__ import annotations

from html import escape
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_studio_dashboard_service
from app.services.studio import StudioDashboardService, StudioDashboardSnapshot

router = APIRouter(prefix="/studio", include_in_schema=False)


@router.get("", response_class=HTMLResponse, name="get_studio_dashboard")
def get_studio_dashboard(
    studio_service: Annotated[StudioDashboardService, Depends(get_studio_dashboard_service)],
    session: Annotated[Session, Depends(get_db_session)],
) -> HTMLResponse:
    snapshot = studio_service.get_snapshot(session)
    return HTMLResponse(content=_render_studio_dashboard(snapshot))


def _render_studio_dashboard(snapshot: StudioDashboardSnapshot) -> str:
    return (
        """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>YouTube Agent OS Studio</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6efe5;
      --surface: rgba(255, 250, 244, 0.88);
      --surface-strong: rgba(255, 255, 255, 0.9);
      --ink: #1d2430;
      --muted: #665f57;
      --line: rgba(90, 67, 45, 0.16);
      --accent: #bf5a36;
      --accent-strong: #8f3417;
      --green: #0d7f63;
      --shadow: 0 22px 44px rgba(62, 40, 21, 0.12);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
      background:
        radial-gradient(circle at top left, rgba(255, 211, 182, 0.65), transparent 34%),
        radial-gradient(circle at top right, rgba(207, 236, 227, 0.9), transparent 28%),
        linear-gradient(180deg, #fcf7f2 0%, var(--bg) 55%, #efe2d3 100%);
      min-height: 100vh;
    }
    .shell {
      max-width: 1180px;
      margin: 0 auto;
      padding: 28px 18px 42px;
    }
    .hero {
      position: relative;
      overflow: hidden;
      background: linear-gradient(135deg, rgba(30, 36, 48, 0.96), rgba(72, 42, 26, 0.94));
      color: #fff8f1;
      border-radius: 28px;
      padding: 30px;
      box-shadow: var(--shadow);
      margin-bottom: 22px;
    }
    .hero-grid {
      position: relative;
      z-index: 1;
      display: grid;
      grid-template-columns: 1.3fr 0.8fr;
      gap: 18px;
      align-items: start;
    }
    .eyebrow {
      text-transform: uppercase;
      letter-spacing: 0.18em;
      font-size: 12px;
      color: #ffd8bd;
      margin-bottom: 10px;
    }
    h1 {
      font-size: clamp(34px, 5vw, 62px);
      line-height: 0.95;
      margin: 0 0 14px;
      max-width: 680px;
    }
    .hero p {
      margin: 0;
      font-size: 17px;
      line-height: 1.55;
      color: rgba(255, 248, 241, 0.86);
      max-width: 720px;
    }
    .stats {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }
    .stat {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 18px;
      padding: 16px;
      backdrop-filter: blur(10px);
    }
    .stat strong {
      display: block;
      font-size: 28px;
      margin-bottom: 6px;
    }
    .layout {
      display: grid;
      grid-template-columns: 400px minmax(0, 1fr);
      gap: 20px;
    }
    .panel {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 22px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(16px);
    }
    .panel h2 {
      margin: 0 0 12px;
      font-size: 26px;
    }
    .subtle {
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
    }
    label {
      display: block;
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--muted);
      margin: 16px 0 6px;
    }
    input, textarea, select {
      width: 100%;
      border-radius: 16px;
      border: 1px solid rgba(84, 66, 51, 0.16);
      background: rgba(255, 255, 255, 0.82);
      padding: 13px 14px;
      font: inherit;
      color: var(--ink);
    }
    textarea {
      resize: vertical;
      min-height: 110px;
    }
    .button-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 18px;
    }
    button, .button-link {
      appearance: none;
      border: 0;
      border-radius: 999px;
      padding: 12px 18px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      text-decoration: none;
      text-align: center;
    }
    .primary {
      background: linear-gradient(135deg, var(--accent), var(--accent-strong));
      color: #fff9f5;
    }
    .secondary {
      background: #f0e0d4;
      color: #513a2b;
    }
    .success {
      background: linear-gradient(135deg, var(--green), #14694c);
      color: #f7fffc;
    }
    .status-bar {
      border-radius: 18px;
      padding: 14px 16px;
      margin-bottom: 16px;
      font-size: 14px;
      display: none;
    }
    .status-bar.visible { display: block; }
    .status-ok {
      background: #def5ee;
      color: #14694c;
      border: 1px solid rgba(20, 105, 76, 0.16);
    }
    .status-error {
      background: #fde8e4;
      color: #8e2c20;
      border: 1px solid rgba(142, 44, 32, 0.16);
    }
    .connections {
      display: grid;
      gap: 12px;
    }
    .connection-card, .flow-card {
      border-radius: 20px;
      background: linear-gradient(180deg, rgba(255,255,255,0.94), rgba(255,246,237,0.96));
      border: 1px solid rgba(84, 66, 51, 0.12);
      padding: 16px;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border-radius: 999px;
      padding: 7px 11px;
      background: rgba(217, 243, 235, 1);
      color: var(--green);
      font-size: 13px;
      font-weight: 700;
      margin-bottom: 10px;
    }
    .quick-links {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
    }
    .quick-links a {
      text-decoration: none;
      color: #ffd8bd;
      font-weight: 700;
      font-size: 14px;
    }
    .stack {
      display: grid;
      gap: 16px;
    }
    .flow-card h3 {
      margin: 0 0 8px;
      font-size: 24px;
    }
    .flow-card ol {
      margin: 10px 0 0 18px;
      padding: 0;
      color: var(--muted);
      line-height: 1.6;
    }
    .empty {
      border-radius: 22px;
      border: 1px dashed rgba(84, 66, 51, 0.26);
      padding: 34px;
      text-align: center;
      color: var(--muted);
      background: rgba(255,255,255,0.55);
    }
    @media (max-width: 960px) {
      .hero-grid, .layout { grid-template-columns: 1fr; }
    }
    @media (max-width: 720px) {
      .stats { grid-template-columns: 1fr; }
      .shell { padding-inline: 14px; }
      .hero, .panel { padding: 20px; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="hero-grid">
        <div>
          <div class="eyebrow">YouTube Agent OS</div>
          <h1>Um studio mais limpo para criar, configurar e publicar sem ruído.</h1>
          <p>
            O Studio agora virou o ponto de entrada do fluxo: configurar o sistema,
            conectar canal, descrever a ideia e abrir a revisao pronta no fim do preparo.
          </p>
          <div class="quick-links">
            <a href="/api/v1/system/settings">Configuracoes do sistema</a>
            <a href="/api/v1/oauth/youtube/authorize" target="_blank" rel="noreferrer">
              Conectar novo canal
            </a>
            <a href="/api/v1/health" target="_blank" rel="noreferrer">Health da API</a>
          </div>
        </div>
        <div class="stats">
          <div class="stat">
            <strong>__INITIAL_CONNECTIONS__</strong><span>Canais ativos</span>
          </div>
          <div class="stat">
            <strong>.env guiado</strong><span>Configuracao pela interface</span>
          </div>
          <div class="stat">
            <strong>private</strong><span>Upload inicial seguro</span>
          </div>
          <div class="stat">
            <strong>human review</strong><span>Publicacao so apos aprovacao</span>
          </div>
        </div>
      </div>
    </section>

    <section class="layout">
      <article class="panel">
        <h2>Criar projeto</h2>
        <p class="subtle">
          Escolha um canal, descreva a ideia base e deixe o sistema criar e preparar o
          video automaticamente antes de abrir a tela de revisao.
        </p>
        <div id="studio-status" class="status-bar"></div>
        <label for="connection-id">Canal conectado</label>
        <select id="connection-id">__CONNECTION_OPTIONS__</select>
        <label for="project-title">Titulo da ideia</label>
        <input id="project-title" placeholder="Ex: Primeiro video publicado por um agente de IA">
        <label for="project-idea">Ideia base</label>
        <textarea
          id="project-idea"
          placeholder="Descreva a mensagem, o tom e o que o video precisa provar."></textarea>
        <label for="target-audience">Publico-alvo</label>
        <input id="target-audience" placeholder="Ex: criadores, devs, time de marketing">
        <label for="business-goal">Objetivo</label>
        <input
          id="business-goal"
          placeholder="Ex: validar MVP, apresentar tecnologia, gerar curiosidade">
        <div class="button-row">
          <button class="primary" type="button" onclick="createProject()">Criar e preparar</button>
          <a class="button-link secondary" href="/api/v1/system/settings">Abrir configuracoes</a>
        </div>
      </article>

      <section class="stack">
        <article class="panel">
          <h2>Canais conectados</h2>
          <p class="subtle">Use um canal ativo para rodar o fluxo completo do YouTube.</p>
          <div class="connections">__CONNECTIONS_HTML__</div>
        </article>
        <article class="panel flow-card">
          <h3>Fluxo atual</h3>
          <p class="subtle">
            Depois do clique em criar, o sistema gera conteudo, prepara assets, renderiza e
            te leva direto para a revisao humana.
          </p>
          <ol>
            <li>Conectar o canal do YouTube</li>
            <li>Preencher a configuracao local no sistema</li>
            <li>Criar e preparar o projeto</li>
            <li>Revisar, subir como private e publicar</li>
          </ol>
        </article>
      </section>
    </section>
  </main>
  <script>
    function setStatus(message, kind = "ok") {
      const node = document.getElementById("studio-status");
      node.textContent = message;
      node.className = "status-bar visible " + (kind === "error" ? "status-error" : "status-ok");
    }

    async function postJson(url, payload) {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json().catch(() => ({ detail: "Erro inesperado" }));
      if (!response.ok) {
        throw new Error(data.detail || "Erro inesperado");
      }
      return data;
    }

    async function createProject() {
      try {
        const connectionId = document.getElementById("connection-id").value.trim();
        const title = document.getElementById("project-title").value.trim();
        const rawIdea = document.getElementById("project-idea").value.trim();
        if (!connectionId || !title || !rawIdea) {
          throw new Error("Preencha canal, titulo e ideia antes de criar o projeto.");
        }
        const payload = {
          connection_id: connectionId,
          title,
          raw_idea: rawIdea,
          target_audience: document.getElementById("target-audience").value.trim() || null,
          business_goal: document.getElementById("business-goal").value.trim() || null
        };
        const result = await postJson("/api/v1/projects", payload);
        setStatus("Projeto criado. Preparando video automaticamente...");
        await postJson("/api/v1/projects/" + result.project_id + "/prepare-video", {});
        setStatus("Video preparado com sucesso. Abrindo revisao.");
        window.location.href = result.review_url;
      } catch (error) {
        setStatus(error.message, "error");
      }
    }
  </script>
</body>
</html>"""
        .replace("__INITIAL_CONNECTIONS__", str(len(snapshot.connections)))
        .replace("__CONNECTION_OPTIONS__", _render_connection_options(snapshot))
        .replace("__CONNECTIONS_HTML__", _render_connections_html(snapshot))
    )


def _render_connection_options(snapshot: StudioDashboardSnapshot) -> str:
    if not snapshot.connections:
        return '<option value="">Nenhum canal ativo</option>'
    return "".join(
        f'<option value="{escape(connection.connection_id)}">'
        f"{escape(connection.channel_title)} ({escape(connection.youtube_channel_id)})"
        "</option>"
        for connection in snapshot.connections
    )


def _render_connections_html(snapshot: StudioDashboardSnapshot) -> str:
    if not snapshot.connections:
        return (
            '<div class="empty">Nenhum canal conectado ainda. Use "Conectar novo canal" '
            "para autenticar um canal do YouTube.</div>"
        )
    return "".join(
        (
            '<div class="connection-card">'
            f'<div class="badge">{escape(connection.connection_status)}</div>'
            f"<strong>{escape(connection.channel_title)}</strong>"
            f'<p class="subtle">Connection ID: {escape(connection.connection_id)}</p>'
            f'<p class="subtle">YouTube Channel ID: {escape(connection.youtube_channel_id)}</p>'
            "</div>"
        )
        for connection in snapshot.connections
    )
