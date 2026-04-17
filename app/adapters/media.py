from __future__ import annotations

import math
import re
import struct
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from app.adapters.narration import NarrationProvider, NarrationRequest


@dataclass(slots=True)
class MediaPreparationInput:
    project_id: str
    generated_title: str
    generated_script: str
    thumbnail_prompt: str
    production_plan: str


@dataclass(slots=True)
class PreparedMediaAsset:
    asset_type: str
    source_adapter: str
    source_reference: str
    storage_path: str
    metadata_json: dict[str, object] = field(default_factory=dict)


class MediaAssetAdapter(Protocol):
    def prepare_assets(self, payload: MediaPreparationInput) -> list[PreparedMediaAsset]:
        """Prepare media assets for a project."""


class ThumbnailGenerator(Protocol):
    def generate_variants(
        self,
        *,
        base_path: Path,
        slug: str,
        title: str,
        prompt: str,
    ) -> list[PreparedMediaAsset]:
        """Generate thumbnail variants."""


class DeterministicMediaAssetAdapter(MediaAssetAdapter):
    def __init__(
        self,
        *,
        output_root: str,
        narration_provider: NarrationProvider,
        thumbnail_generator: ThumbnailGenerator | None = None,
    ) -> None:
        self._output_root = Path(output_root)
        self._narration_provider = narration_provider
        self._thumbnail_generator = thumbnail_generator

    def prepare_assets(self, payload: MediaPreparationInput) -> list[PreparedMediaAsset]:
        slug = _slugify_filename(payload.generated_title)
        base_path = self._output_root / payload.project_id
        base_path.mkdir(parents=True, exist_ok=True)

        thumbnail_assets = (
            self._thumbnail_generator.generate_variants(
                base_path=base_path,
                slug=slug,
                title=payload.generated_title,
                prompt=payload.thumbnail_prompt,
            )
            if self._thumbnail_generator is not None
            else self._write_thumbnail_variants(
                base_path=base_path,
                slug=slug,
                title=payload.generated_title,
                prompt=payload.thumbnail_prompt,
            )
        )

        voiceover_script_path = base_path / f"{slug}-voiceover.txt"
        voiceover_script_path.write_text(payload.generated_script, encoding="utf-8")

        production_manifest_path = base_path / f"{slug}-production-plan.md"
        production_manifest_path.write_text(payload.production_plan, encoding="utf-8")

        narration_result = self._narration_provider.synthesize(
            NarrationRequest(
                project_id=payload.project_id,
                title=payload.generated_title,
                script=payload.generated_script,
                output_path=str(base_path / f"{slug}-voiceover.wav"),
            )
        )
        subtitle_cues = self._build_subtitle_cues(
            script=payload.generated_script,
            total_duration_seconds=narration_result.duration_seconds,
        )
        subtitle_srt_path = base_path / f"{slug}-captions.srt"
        subtitle_vtt_path = base_path / f"{slug}-captions.vtt"
        subtitle_srt_path.write_text(self._render_srt(subtitle_cues), encoding="utf-8")
        subtitle_vtt_path.write_text(self._render_vtt(subtitle_cues), encoding="utf-8")
        background_music_path = base_path / f"{slug}-background-music.wav"
        self._write_background_music(
            output_path=background_music_path,
            duration_seconds=narration_result.duration_seconds,
        )

        return [
            *thumbnail_assets,
            PreparedMediaAsset(
                asset_type="voiceover_script",
                source_adapter="deterministic-media-adapter",
                source_reference=payload.generated_script,
                storage_path=str(voiceover_script_path),
                metadata_json={
                    "language": "pt-BR",
                    "script_excerpt": payload.generated_script[:120],
                },
            ),
            PreparedMediaAsset(
                asset_type="voiceover_audio",
                source_adapter=narration_result.provider,
                source_reference=payload.generated_script,
                storage_path=narration_result.output_path,
                metadata_json={
                    "language": "pt-BR",
                    "duration_seconds": narration_result.duration_seconds,
                    **narration_result.metadata_json,
                },
            ),
            PreparedMediaAsset(
                asset_type="subtitles_srt",
                source_adapter="deterministic-media-adapter",
                source_reference=payload.generated_script,
                storage_path=str(subtitle_srt_path),
                metadata_json={
                    "language": "pt-BR",
                    "cue_count": len(subtitle_cues),
                    "format": "srt",
                },
            ),
            PreparedMediaAsset(
                asset_type="subtitles_vtt",
                source_adapter="deterministic-media-adapter",
                source_reference=payload.generated_script,
                storage_path=str(subtitle_vtt_path),
                metadata_json={
                    "language": "pt-BR",
                    "cue_count": len(subtitle_cues),
                    "format": "vtt",
                },
            ),
            PreparedMediaAsset(
                asset_type="background_music",
                source_adapter="deterministic-media-adapter",
                source_reference=payload.production_plan,
                storage_path=str(background_music_path),
                metadata_json={
                    "duration_seconds": narration_result.duration_seconds,
                    "format": "wav",
                    "mix_role": "bed",
                },
            ),
            PreparedMediaAsset(
                asset_type="production_manifest",
                source_adapter="deterministic-media-adapter",
                source_reference=payload.production_plan,
                storage_path=str(production_manifest_path),
                metadata_json={
                    "title": payload.generated_title,
                    "steps": 4,
                },
            ),
        ]

    def _write_thumbnail_variants(
        self,
        *,
        base_path: Path,
        slug: str,
        title: str,
        prompt: str,
    ) -> list[PreparedMediaAsset]:
        variants = [
            ("hero", "#172235", "#0f766e", "#bf5a36", True, "Hero forte com CTA"),
            ("contrast", "#2d132c", "#801336", "#ee4540", False, "Contraste alto e energia"),
            ("minimal", "#12343b", "#2d545e", "#e1b382", False, "Minimalista e editorial"),
        ]
        assets: list[PreparedMediaAsset] = []
        for variant_name, start_color, end_color, accent_color, selected, label in variants:
            thumbnail_path = base_path / f"{slug}-thumbnail-{variant_name}.svg"
            thumbnail_path.write_text(
                self._build_thumbnail_svg(
                    title=title,
                    prompt=prompt,
                    start_color=start_color,
                    end_color=end_color,
                    accent_color=accent_color,
                    variant_label=label,
                ),
                encoding="utf-8",
            )
            assets.append(
                PreparedMediaAsset(
                    asset_type="thumbnail",
                    source_adapter="deterministic-media-adapter",
                    source_reference=prompt,
                    storage_path=str(thumbnail_path),
                    metadata_json={
                        "prompt": prompt,
                        "format": "svg",
                        "variant": variant_name,
                        "label": label,
                        "selected": selected,
                    },
                )
            )
        return assets

    @staticmethod
    def _build_thumbnail_svg(
        *,
        title: str,
        prompt: str,
        start_color: str,
        end_color: str,
        accent_color: str,
        variant_label: str,
    ) -> str:
        safe_title = _escape_xml(title[:70] or "YouTube Agent OS")
        safe_prompt = _escape_xml(prompt[:110] or "Thumbnail visual gerada localmente")
        safe_variant_label = _escape_xml(variant_label[:48])
        return f"""
<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720"
     viewBox="0 0 1280 720">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{start_color}" />
      <stop offset="100%" stop-color="{end_color}" />
    </linearGradient>
  </defs>
  <rect width="1280" height="720" fill="url(#bg)" rx="36" />
  <rect x="54" y="54" width="1172" height="612" rx="32" fill="#f6efe6" opacity="0.96" />
  <rect x="54" y="54" width="1172" height="138" rx="32" fill="{accent_color}" />
  <text x="92" y="120" fill="#fff8f1" font-size="34"
        font-family="Segoe UI, Arial, sans-serif" font-weight="700">YOUTUBE AGENT OS</text>
  <text x="92" y="280" fill="#1f2937" font-size="68"
        font-family="Segoe UI, Arial, sans-serif" font-weight="800">{safe_title}</text>
  <text x="92" y="390" fill="#334155" font-size="28"
        font-family="Segoe UI, Arial, sans-serif">{safe_prompt}</text>
  <rect x="92" y="470" width="1096" height="132" rx="24" fill="#ffffff" />
  <text x="128" y="548" fill="#0f766e" font-size="48"
        font-family="Segoe UI, Arial, sans-serif" font-weight="800">VIDEO ASSISTIDO</text>
  <text x="860" y="548" fill="#475569" font-size="24"
        font-family="Segoe UI, Arial, sans-serif" font-weight="700">{safe_variant_label}</text>
  <text x="92" y="650" fill="#fff8f1" font-size="28"
        font-family="Segoe UI, Arial, sans-serif">MVP visual local para revisao humana</text>
</svg>
"""

    @staticmethod
    def _build_subtitle_cues(
        *,
        script: str,
        total_duration_seconds: float,
    ) -> list[SubtitleCue]:
        lines = [
            line.strip()
            for line in re.split(r"[\n\.!?]+", script)
            if line.strip()
        ]
        if not lines:
            lines = ["Conteudo gerado para revisao humana."]
        max_cues = min(8, len(lines))
        selected_lines = lines[:max_cues]
        cue_duration = max(1.5, total_duration_seconds / max(1, len(selected_lines)))
        cues: list[SubtitleCue] = []
        current_start = 0.0
        for line in selected_lines:
            end_time = current_start + cue_duration
            cues.append(
                SubtitleCue(
                    start_seconds=round(current_start, 2),
                    end_seconds=round(end_time, 2),
                    text=line,
                )
            )
            current_start = end_time
        return cues

    @staticmethod
    def _render_srt(cues: list[SubtitleCue]) -> str:
        blocks: list[str] = []
        for index, cue in enumerate(cues, start=1):
            blocks.append(
                "\n".join(
                    [
                        str(index),
                        f"{_format_timestamp(cue.start_seconds, srt_style=True)} --> "
                        f"{_format_timestamp(cue.end_seconds, srt_style=True)}",
                        cue.text,
                    ]
                )
            )
        return "\n\n".join(blocks) + "\n"

    @staticmethod
    def _render_vtt(cues: list[SubtitleCue]) -> str:
        blocks = ["WEBVTT\n"]
        for cue in cues:
            blocks.append(
                "\n".join(
                    [
                        f"{_format_timestamp(cue.start_seconds, srt_style=False)} --> "
                        f"{_format_timestamp(cue.end_seconds, srt_style=False)}",
                        cue.text,
                    ]
                )
            )
        return "\n\n".join(blocks) + "\n"

    @staticmethod
    def _write_background_music(*, output_path: Path, duration_seconds: float) -> None:
        sample_rate = 22050
        amplitude = 700
        frequencies = (130.81, 164.81, 196.0, 261.63)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        total_samples = max(sample_rate * 2, int(sample_rate * max(2.0, duration_seconds)))

        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)

            frames = bytearray()
            for sample_index in range(total_samples):
                progress = sample_index / sample_rate
                frequency = frequencies[int(progress // 2) % len(frequencies)]
                envelope = 0.45 + 0.15 * math.sin(2 * math.pi * 0.25 * progress)
                sample = amplitude * envelope * math.sin(
                    2 * math.pi * frequency * (sample_index / sample_rate)
                )
                frames.extend(struct.pack("<h", int(sample)))
            wav_file.writeframes(frames)


@dataclass(slots=True)
class SubtitleCue:
    start_seconds: float
    end_seconds: float
    text: str


def _escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _format_timestamp(seconds: float, *, srt_style: bool) -> str:
    total_milliseconds = int(seconds * 1000)
    hours = total_milliseconds // 3_600_000
    minutes = (total_milliseconds % 3_600_000) // 60_000
    secs = (total_milliseconds % 60_000) // 1000
    milliseconds = total_milliseconds % 1000
    separator = "," if srt_style else "."
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{milliseconds:03d}"


def _slugify_filename(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^\w\s-]", "", normalized, flags=re.UNICODE)
    normalized = re.sub(r"[-\s]+", "-", normalized).strip("-")
    return normalized or "youtube-agent-os"
