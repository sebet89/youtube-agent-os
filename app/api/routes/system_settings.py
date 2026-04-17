from __future__ import annotations

from html import escape
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import HTMLResponse

from app.api.dependencies import get_system_settings_service
from app.services.system_settings import (
    SystemSettingFieldSnapshot,
    SystemSettingSectionSnapshot,
    SystemSettingsService,
)

router = APIRouter(prefix="/system/settings", include_in_schema=False)


@router.get("", response_class=HTMLResponse, name="get_system_settings")
def get_system_settings_page(
    settings_service: Annotated[SystemSettingsService, Depends(get_system_settings_service)],
) -> HTMLResponse:
    snapshot = settings_service.get_snapshot()
    return HTMLResponse(content=_render_system_settings(snapshot.env_path, snapshot.sections))


@router.post("")
def save_system_settings(
    payload: Annotated[dict[str, Any], Body()],
    settings_service: Annotated[SystemSettingsService, Depends(get_system_settings_service)],
) -> dict[str, object]:
    raw_values = payload.get("values", {})
    if not isinstance(raw_values, dict):
        raise HTTPException(
            status_code=400,
            detail="O payload de configuracoes precisa conter um objeto 'values'.",
        )
    saved = settings_service.save(
        {
            str(key): "" if value is None else str(value)
            for key, value in raw_values.items()
        }
    )
    return {
        "message": "Configuracoes salvas com sucesso.",
        "env_path": saved.env_path,
        "updated_keys": list(saved.updated_keys),
    }


def _render_system_settings(
    env_path: str,
    sections: tuple[SystemSettingSectionSnapshot, ...],
) -> str:
    sections_html = "".join(_render_section(section) for section in sections)
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Configuracoes do sistema</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5efe7;
      --surface: rgba(255, 250, 245, 0.9);
      --surface-strong: #fffaf6;
      --ink: #18202a;
      --muted: #6a625c;
      --line: rgba(80, 63, 48, 0.14);
      --accent: #0a7f64;
      --accent-strong: #075743;
      --secondary: #ebded0;
      --shadow: 0 22px 46px rgba(62, 43, 26, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
      background:
        radial-gradient(circle at top left, rgba(255, 217, 186, 0.65), transparent 32%),
        linear-gradient(180deg, #fbf7f3 0%, #f2e8dc 100%);
    }}
    .shell {{
      max-width: 1160px;
      margin: 0 auto;
      padding: 28px 18px 42px;
    }}
    .hero {{
      background: linear-gradient(135deg, rgba(24, 32, 42, 0.96), rgba(11, 78, 61, 0.96));
      color: #f5fbf8;
      border-radius: 28px;
      padding: 28px;
      box-shadow: var(--shadow);
      margin-bottom: 20px;
    }}
    .hero h1 {{
      margin: 0 0 10px;
      font-size: clamp(30px, 4vw, 54px);
      line-height: 0.96;
    }}
    .hero p {{
      margin: 0;
      max-width: 760px;
      color: rgba(245, 251, 248, 0.84);
      line-height: 1.55;
    }}
    .hero-links {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
    }}
    .hero-links a {{
      color: #dff9f0;
      text-decoration: none;
      font-weight: 700;
    }}
    .status {{
      display: none;
      border-radius: 18px;
      padding: 14px 16px;
      margin: 0 0 18px;
      font-size: 14px;
    }}
    .status.visible {{ display: block; }}
    .status.ok {{
      background: #def4ec;
      color: #0a6c53;
      border: 1px solid rgba(10, 108, 83, 0.16);
    }}
    .status.error {{
      background: #fde7e2;
      color: #8e3222;
      border: 1px solid rgba(142, 50, 34, 0.16);
    }}
    .stack {{
      display: grid;
      gap: 18px;
    }}
    .panel {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 22px;
      box-shadow: var(--shadow);
    }}
    .panel h2 {{
      margin: 0 0 8px;
      font-size: 26px;
    }}
    .subtle {{
      color: var(--muted);
      line-height: 1.55;
      font-size: 14px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 14px;
      margin-top: 18px;
    }}
    .field {{
      background: var(--surface-strong);
      border: 1px solid rgba(80, 63, 48, 0.08);
      border-radius: 18px;
      padding: 16px;
    }}
    label {{
      display: block;
      margin: 0 0 8px;
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    input, textarea, select {{
      width: 100%;
      border-radius: 14px;
      border: 1px solid rgba(80, 63, 48, 0.16);
      background: rgba(255, 255, 255, 0.92);
      padding: 12px 13px;
      font: inherit;
      color: var(--ink);
    }}
    textarea {{
      min-height: 110px;
      resize: vertical;
    }}
    .field p {{
      margin: 8px 0 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }}
    .footer-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 18px;
    }}
    button {{
      appearance: none;
      border: 0;
      border-radius: 999px;
      padding: 12px 18px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }}
    .primary {{
      background: linear-gradient(135deg, var(--accent), var(--accent-strong));
      color: #f8fffc;
    }}
    .secondary {{
      background: var(--secondary);
      color: #4d3b2d;
    }}
    code {{
      background: rgba(255,255,255,0.6);
      border-radius: 8px;
      padding: 2px 6px;
      font-size: 13px;
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <h1>Configuracoes do sistema</h1>
      <p>
        Preencha credenciais, providers, caminhos locais e detalhes de infraestrutura sem
        editar o arquivo manualmente. As alteracoes sao salvas no <code>{escape(env_path)}</code>.
      </p>
      <div class="hero-links">
        <a href="/api/v1/studio">Voltar ao studio</a>
        <a href="/api/v1/health" target="_blank" rel="noreferrer">Health da API</a>
      </div>
    </section>

    <div id="settings-status" class="status"></div>
    <section class="stack">
      {sections_html}
      <article class="panel">
        <h2>Salvar</h2>
        <p class="subtle">
          Alteracoes em credenciais, providers de IA, Celery e FFmpeg costumam pedir restart
          da API e do worker para refletirem em todo o fluxo.
        </p>
        <div class="footer-actions">
          <button class="primary" type="button" onclick="saveSettings()">
            Salvar configuracoes
          </button>
          <button class="secondary" type="button" onclick="window.location.reload()">
            Recarregar tela
          </button>
        </div>
      </article>
    </section>
  </main>
  <script>
    function setStatus(message, kind) {{
      const node = document.getElementById("settings-status");
      node.textContent = message;
      node.className = "status visible " + (kind === "error" ? "error" : "ok");
    }}

    async function saveSettings() {{
      const values = {{}};
      document.querySelectorAll("[data-env-key]").forEach((node) => {{
        values[node.dataset.envKey] = node.value;
      }});
      try {{
        const response = await fetch("/api/v1/system/settings", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ values }})
        }});
        const payload = await response.json().catch(() => ({{ detail: "Erro inesperado" }}));
        if (!response.ok) {{
          throw new Error(payload.detail || "Erro inesperado ao salvar configuracoes.");
        }}
        setStatus(payload.message + " Se mexeu em providers, reinicie a API e o worker.", "ok");
      }} catch (error) {{
        setStatus(error.message, "error");
      }}
    }}
  </script>
</body>
</html>"""


def _render_section(section: SystemSettingSectionSnapshot) -> str:
    fields_html = "".join(_render_field(field) for field in section.fields)
    return (
        '<article class="panel">'
        f"<h2>{escape(section.title)}</h2>"
        f'<p class="subtle">{escape(section.description)}</p>'
        f'<div class="grid">{fields_html}</div>'
        "</article>"
    )


def _render_field(field: SystemSettingFieldSnapshot) -> str:
    if field.options:
        control = _render_select(field)
    elif field.multiline:
        control = (
            f'<textarea id="{escape(field.env_key)}" data-env-key="{escape(field.env_key)}" '
            f'placeholder="{escape(field.placeholder)}">{escape(field.value)}</textarea>'
        )
    else:
        control = (
            f'<input id="{escape(field.env_key)}" '
            f'type="{escape(field.input_type)}" '
            f'data-env-key="{escape(field.env_key)}" '
            f'value="{escape(field.value)}" '
            f'placeholder="{escape(field.placeholder)}">'
        )
    return (
        '<div class="field">'
        f'<label for="{escape(field.env_key)}">{escape(field.label)}</label>'
        f"{control}"
        f"<p>{escape(field.help_text)}</p>"
        "</div>"
    )


def _render_select(field: SystemSettingFieldSnapshot) -> str:
    options_html = "".join(
        (
            f'<option value="{escape(option.value)}"'
            + (' selected' if option.value == field.value else "")
            + f">{escape(option.label)}</option>"
        )
        for option in field.options
    )
    return (
        f'<select id="{escape(field.env_key)}" data-env-key="{escape(field.env_key)}">'
        f"{options_html}"
        "</select>"
    )
