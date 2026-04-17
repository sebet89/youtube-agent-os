from __future__ import annotations

import hashlib
import re
import subprocess
import unicodedata
from dataclasses import dataclass, field
from math import ceil
from pathlib import Path
from typing import Protocol


@dataclass(slots=True)
class RenderInput:
    project_id: str
    title: str
    script: str
    asset_paths: list[str]
    output_dir: str
    audio_path: str | None = None
    audio_duration_seconds: float | None = None
    background_music_path: str | None = None


@dataclass(slots=True)
class RenderResult:
    output_path: str
    command: list[str] = field(default_factory=list)
    metadata_json: dict[str, object] = field(default_factory=dict)


class VideoRenderer(Protocol):
    def render(self, payload: RenderInput) -> RenderResult:
        """Render a final video artifact for a project."""


class FFmpegVideoRenderer(VideoRenderer):
    def __init__(self, ffmpeg_binary: str = "ffmpeg") -> None:
        self._ffmpeg_binary = ffmpeg_binary

    def render(self, payload: RenderInput) -> RenderResult:
        output_dir = Path(payload.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{payload.project_id}-final.mp4"
        theme = self._select_theme(payload)
        slides = self._build_storyboard_slides(payload, theme=theme)
        slide_paths = self._write_storyboard_slides(slides, output_dir, theme=theme)
        slide_duration = self._resolve_slide_duration(payload, slide_count=len(slide_paths))
        total_duration = len(slide_paths) * slide_duration

        command = [
            self._ffmpeg_binary,
            "-y",
        ]
        for slide_path in slide_paths:
            command.extend(
                [
                    "-loop",
                    "1",
                    "-t",
                    str(slide_duration),
                    "-i",
                    str(slide_path),
                ]
            )
        audio_input_index = len(slide_paths)
        filter_complex = self._build_concat_filter(len(slide_paths))
        if payload.audio_path:
            command.extend(["-i", payload.audio_path])
            if payload.background_music_path:
                command.extend(["-i", payload.background_music_path])
                music_input_index = audio_input_index + 1
                filter_complex = self._build_concat_filter(
                    len(slide_paths),
                    voice_input_index=audio_input_index,
                    music_input_index=music_input_index,
                )
        else:
            command.extend(
                [
                    "-f",
                    "lavfi",
                    "-t",
                    str(total_duration),
                    "-i",
                    "anullsrc=r=44100:cl=stereo",
                ]
            )
        command.extend(
            [
                "-filter_complex",
                filter_complex,
                "-map",
                "[v]",
                "-map",
                (
                    "[aout]"
                    if payload.background_music_path and payload.audio_path
                    else f"{audio_input_index}:a"
                ),
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                "-shortest",
            ]
        )
        command.extend(
            [
            "-pix_fmt",
            "yuv420p",
            str(output_path),
            ]
        )
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise ValueError(
                "FFmpeg was not found. Install FFmpeg or set FFMPEG_BINARY in the environment."
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            message = "FFmpeg render failed."
            if stderr:
                message = f"{message} {stderr}"
            raise ValueError(message) from exc
        return RenderResult(
            output_path=str(output_path),
            command=command,
            metadata_json={
                "renderer": "ffmpeg",
                "asset_count": len(payload.asset_paths),
                "title": payload.title,
                "slide_count": len(slide_paths),
                "audio_embedded": bool(payload.audio_path),
                "background_music_embedded": bool(payload.background_music_path),
                "timeline_sections": [slide.headline for slide in slides],
                "theme_name": theme.name,
            },
        )

    @staticmethod
    def _resolve_slide_duration(payload: RenderInput, *, slide_count: int) -> int:
        if payload.audio_duration_seconds and payload.audio_duration_seconds > 0:
            return max(4, ceil(payload.audio_duration_seconds / slide_count))
        return 4

    @staticmethod
    def _build_concat_filter(
        slide_count: int,
        *,
        voice_input_index: int | None = None,
        music_input_index: int | None = None,
    ) -> str:
        scale_steps = [
            f"[{index}:v]scale=1280:720,setsar=1[v{index}]"
            for index in range(slide_count)
        ]
        concat_inputs = "".join(f"[v{index}]" for index in range(slide_count))
        filter_steps = scale_steps + [f"{concat_inputs}concat=n={slide_count}:v=1:a=0[v]"]
        if voice_input_index is not None and music_input_index is not None:
            filter_steps.extend(
                [
                    f"[{voice_input_index}:a]volume=1.0[voice]",
                    f"[{music_input_index}:a]volume=0.18[music]",
                    "[voice][music]amix=inputs=2:duration=first:dropout_transition=2[aout]",
                ]
            )
        return ";".join(filter_steps)

    def _build_storyboard_slides(
        self,
        payload: RenderInput,
        *,
        theme: RenderTheme,
    ) -> list[SlideSpec]:
        script_lines = self._extract_script_lines(payload.script)
        asset_lines = [Path(asset_path).name for asset_path in payload.asset_paths[:4]]
        scene_slides = self._build_scene_slides(script_lines, theme=theme)
        slides = [
            SlideSpec(
                headline=self._normalize_text(payload.title),
                eyebrow="YOUTUBE AGENT OS",
                body_lines=[
                    "Fluxo assistido para YouTube",
                    "Roteiro, voz, assets e render em uma trilha unica",
                ],
                accent=theme.hero_accent,
                panel=theme.hero_panel,
                layout=theme.hero_layout,
                caption="Apresentando o fluxo assistido de video para YouTube.",
            ),
            *scene_slides,
            SlideSpec(
                headline="ASSETS E ENTREGA",
                eyebrow="PRODUCAO",
                body_lines=asset_lines
                or [
                    "Thumbnail preparada",
                    "Voiceover audio disponivel",
                    "Manifesto de producao pronto",
                ],
                accent=theme.assets_accent,
                panel=theme.assets_panel,
                layout=theme.assets_layout,
                caption="Assets prontos para revisar, renderizar e publicar.",
            ),
            SlideSpec(
                headline="REVISAO HUMANA",
                eyebrow="PROXIMO PASSO",
                body_lines=[
                    "Ajuste titulo, descricao e thumbnail",
                    "Render pronto para upload privado",
                    "Libere publicacao somente apos revisar",
                ],
                accent=theme.closing_accent,
                panel=theme.closing_panel,
                layout=theme.closing_layout,
                caption="Revise o resultado antes de liberar a publicacao.",
            ),
        ]
        return slides

    def _write_storyboard_slides(
        self,
        slides: list[SlideSpec],
        output_dir: Path,
        *,
        theme: RenderTheme,
    ) -> list[Path]:
        slide_paths: list[Path] = []
        for index, slide in enumerate(slides, start=1):
            slide_path = output_dir / f"slide-{index}.ppm"
            self._write_slide(
                slide_path,
                slide,
                theme=theme,
                slide_index=index,
                total_slides=len(slides),
            )
            slide_paths.append(slide_path)
        return slide_paths

    def _build_scene_slides(
        self,
        script_lines: list[str],
        *,
        theme: RenderTheme,
    ) -> list[SlideSpec]:
        if not script_lines:
            script_lines = ["Conteudo gerado e pronto para refinamento"]
        grouped_lines = [
            script_lines[index : index + 2]
            for index in range(0, len(script_lines), 2)
        ]
        slides: list[SlideSpec] = []
        total_groups = min(4, len(grouped_lines))
        for index, lines in enumerate(grouped_lines[:total_groups], start=1):
            accent, panel = theme.scene_palettes[(index - 1) % len(theme.scene_palettes)]
            slides.append(
                SlideSpec(
                    headline=f"CENA {index}",
                    eyebrow="NARRATIVA",
                    body_lines=lines,
                    accent=accent,
                    panel=panel,
                    layout=theme.scene_layouts[(index - 1) % len(theme.scene_layouts)],
                    caption=" ".join(lines),
                )
            )
        return slides

    def _write_slide(
        self,
        output_path: Path,
        slide: SlideSpec,
        *,
        theme: RenderTheme,
        slide_index: int,
        total_slides: int,
    ) -> None:
        width = 1280
        height = 720
        pixels = bytearray(width * height * 3)
        self._fill_rect(pixels, width, 0, 0, width, height, theme.background)
        self._fill_rect(pixels, width, 40, 40, width - 80, height - 80, slide.panel)
        self._draw_theme_decorations(pixels, width, theme=theme, slide_index=slide_index)
        self._draw_progress_bar(
            pixels,
            width,
            slide_index=slide_index,
            total_slides=total_slides,
            accent=slide.accent,
        )
        if slide.layout == "hero":
            self._draw_hero_layout(pixels, width, slide)
        elif slide.layout == "magazine":
            self._draw_magazine_layout(pixels, width, slide)
        elif slide.layout == "split-left":
            self._draw_split_layout(pixels, width, slide, reverse=False)
        elif slide.layout == "split-right":
            self._draw_split_layout(pixels, width, slide, reverse=True)
        elif slide.layout == "focus":
            self._draw_focus_layout(pixels, width, slide)
        elif slide.layout == "spotlight":
            self._draw_spotlight_layout(pixels, width, slide)
        elif slide.layout == "checklist":
            self._draw_checklist_layout(pixels, width, slide)
        elif slide.layout == "closing":
            self._draw_closing_layout(pixels, width, slide)
        else:
            self._draw_focus_layout(pixels, width, slide)
        self._draw_caption_strip(pixels, width, slide)

        with output_path.open("wb") as file_obj:
            file_obj.write(f"P6\n{width} {height}\n255\n".encode("ascii"))
            file_obj.write(pixels)

    def _draw_progress_bar(
        self,
        pixels: bytearray,
        image_width: int,
        *,
        slide_index: int,
        total_slides: int,
        accent: tuple[int, int, int],
    ) -> None:
        self._fill_rect(pixels, image_width, 88, 650, 1104, 18, (214, 219, 226))
        filled_width = int(1104 * (slide_index / total_slides))
        self._fill_rect(pixels, image_width, 88, 650, filled_width, 18, accent)

    def _draw_caption_strip(
        self,
        pixels: bytearray,
        image_width: int,
        slide: SlideSpec,
    ) -> None:
        if not slide.caption:
            return
        self._fill_rect(pixels, image_width, 110, 570, 1060, 58, (29, 36, 48))
        self._draw_wrapped_text(
            pixels,
            image_width,
            136,
            584,
            slide.caption,
            max_width=1004,
            scale=2,
            color=(255, 248, 241),
            line_spacing=4,
            max_lines=2,
        )

    def _draw_theme_decorations(
        self,
        pixels: bytearray,
        image_width: int,
        *,
        theme: RenderTheme,
        slide_index: int,
    ) -> None:
        if theme.motif == "rings":
            self._fill_rect(pixels, image_width, 1000, 54, 180, 18, theme.hero_accent)
            self._fill_rect(pixels, image_width, 1040, 82, 120, 18, theme.assets_accent)
            self._fill_rect(pixels, image_width, 1080, 110, 60, 18, theme.closing_accent)
        elif theme.motif == "bars":
            for index in range(4):
                top = 84 + index * 30
                self._fill_rect(
                    pixels,
                    image_width,
                    82,
                    top,
                    14 + (index * 16) + (slide_index * 6),
                    10,
                    theme.scene_palettes[index % len(theme.scene_palettes)][0],
                )
        elif theme.motif == "blocks":
            self._fill_rect(pixels, image_width, 1040, 92, 88, 88, theme.hero_accent)
            self._fill_rect(pixels, image_width, 1142, 92, 42, 42, theme.assets_accent)
            self._fill_rect(pixels, image_width, 1142, 142, 42, 42, theme.closing_accent)
        else:
            self._fill_rect(pixels, image_width, 72, 74, 96, 8, theme.hero_accent)
            self._fill_rect(pixels, image_width, 72, 88, 64, 8, theme.assets_accent)

    def _draw_hero_layout(
        self,
        pixels: bytearray,
        image_width: int,
        slide: SlideSpec,
    ) -> None:
        self._fill_rect(pixels, image_width, 40, 40, 1200, 120, slide.accent)
        self._fill_rect(pixels, image_width, 90, 188, 884, 356, (255, 255, 255))
        self._fill_rect(pixels, image_width, 1004, 188, 148, 148, slide.accent)
        self._fill_rect(pixels, image_width, 1004, 366, 148, 148, (29, 36, 48))
        self._draw_header(pixels, image_width, slide, x=92, y=72, text_color=(255, 248, 241))
        self._draw_wrapped_text(
            pixels,
            image_width,
            118,
            236,
            slide.headline,
            max_width=804,
            scale=6,
            color=(29, 36, 48),
            line_spacing=18,
        )
        self._draw_body_lines(
            pixels,
            image_width,
            slide.body_lines,
            x=128,
            y=420,
            max_width=780,
            color=(70, 76, 82),
            max_lines_per_item=2,
        )
        self._draw_text(pixels, image_width, 1028, 228, "YT", scale=7, color=(255, 255, 255))
        self._draw_text(pixels, image_width, 1030, 412, "OS", scale=7, color=(255, 248, 241))

    def _draw_magazine_layout(
        self,
        pixels: bytearray,
        image_width: int,
        slide: SlideSpec,
    ) -> None:
        self._fill_rect(pixels, image_width, 76, 98, 1128, 74, slide.accent)
        self._fill_rect(pixels, image_width, 94, 214, 1090, 336, (255, 255, 255))
        self._fill_rect(pixels, image_width, 94, 566, 520, 56, slide.accent)
        self._draw_header(pixels, image_width, slide, x=94, y=70, text_color=(29, 36, 48))
        self._draw_wrapped_text(
            pixels,
            image_width,
            118,
            248,
            slide.headline,
            max_width=1000,
            scale=5,
            color=(29, 36, 48),
            line_spacing=14,
            max_lines=2,
        )
        self._draw_body_lines(
            pixels,
            image_width,
            slide.body_lines,
            x=122,
            y=378,
            max_width=980,
            color=(70, 76, 82),
            max_lines_per_item=2,
        )
        self._draw_text(
            pixels,
            image_width,
            120,
            582,
            "EDITORIAL CUT",
            scale=3,
            color=(255, 248, 241),
        )

    def _draw_split_layout(
        self,
        pixels: bytearray,
        image_width: int,
        slide: SlideSpec,
        *,
        reverse: bool,
    ) -> None:
        panel_x = 90 if not reverse else 690
        accent_x = 690 if not reverse else 90
        self._fill_rect(pixels, image_width, panel_x, 170, 500, 410, (255, 255, 255))
        self._fill_rect(pixels, image_width, accent_x, 170, 500, 410, slide.accent)
        self._fill_rect(pixels, image_width, accent_x + 44, 214, 412, 322, slide.panel)
        self._draw_header(pixels, image_width, slide, x=96, y=82, text_color=(29, 36, 48))
        self._draw_wrapped_text(
            pixels,
            image_width,
            panel_x + 36,
            230,
            slide.headline,
            max_width=420,
            scale=5,
            color=(29, 36, 48),
            line_spacing=14,
        )
        self._draw_body_lines(
            pixels,
            image_width,
            slide.body_lines,
            x=panel_x + 42,
            y=350,
            max_width=398,
            color=(70, 76, 82),
            max_lines_per_item=3,
        )
        self._draw_text(
            pixels,
            image_width,
            accent_x + 82,
            258,
            "CENA",
            scale=4,
            color=(29, 36, 48),
        )
        self._draw_text(
            pixels,
            image_width,
            accent_x + 106,
            344,
            slide.headline.replace("CENA ", ""),
            scale=10,
            color=(29, 36, 48),
        )

    def _draw_focus_layout(
        self,
        pixels: bytearray,
        image_width: int,
        slide: SlideSpec,
    ) -> None:
        self._fill_rect(pixels, image_width, 76, 108, 1128, 86, slide.accent)
        self._fill_rect(pixels, image_width, 120, 218, 1040, 352, (255, 255, 255))
        self._draw_header(pixels, image_width, slide, x=94, y=74, text_color=(29, 36, 48))
        self._draw_wrapped_text(
            pixels,
            image_width,
            134,
            262,
            slide.headline,
            max_width=980,
            scale=5,
            color=(29, 36, 48),
            line_spacing=16,
        )
        self._draw_body_lines(
            pixels,
            image_width,
            slide.body_lines,
            x=150,
            y=382,
            max_width=940,
            color=(70, 76, 82),
            max_lines_per_item=2,
        )

    def _draw_spotlight_layout(
        self,
        pixels: bytearray,
        image_width: int,
        slide: SlideSpec,
    ) -> None:
        self._fill_rect(pixels, image_width, 92, 164, 1098, 392, (255, 255, 255))
        self._fill_rect(pixels, image_width, 92, 164, 280, 392, slide.accent)
        self._draw_header(pixels, image_width, slide, x=406, y=94, text_color=(29, 36, 48))
        self._draw_text(
            pixels,
            image_width,
            126,
            240,
            slide.eyebrow,
            scale=4,
            color=(255, 248, 241),
        )
        self._draw_wrapped_text(
            pixels,
            image_width,
            406,
            224,
            slide.headline,
            max_width=720,
            scale=5,
            color=(29, 36, 48),
            line_spacing=14,
            max_lines=2,
        )
        self._draw_body_lines(
            pixels,
            image_width,
            slide.body_lines,
            x=410,
            y=350,
            max_width=700,
            color=(70, 76, 82),
            max_lines_per_item=2,
        )

    def _draw_checklist_layout(
        self,
        pixels: bytearray,
        image_width: int,
        slide: SlideSpec,
    ) -> None:
        self._fill_rect(pixels, image_width, 40, 40, 1200, 120, slide.accent)
        self._fill_rect(pixels, image_width, 92, 192, 520, 390, (255, 255, 255))
        self._fill_rect(pixels, image_width, 668, 192, 484, 390, (255, 255, 255))
        self._draw_header(pixels, image_width, slide, x=92, y=72, text_color=(255, 248, 241))
        self._draw_wrapped_text(
            pixels,
            image_width,
            122,
            244,
            slide.headline,
            max_width=438,
            scale=5,
            color=(29, 36, 48),
            line_spacing=14,
        )
        self._draw_body_lines(
            pixels,
            image_width,
            slide.body_lines,
            x=134,
            y=360,
            max_width=430,
            color=(70, 76, 82),
            max_lines_per_item=2,
        )
        for index in range(3):
            top = 256 + index * 94
            self._fill_rect(pixels, image_width, 706, top, 42, 42, slide.accent)
            self._fill_rect(pixels, image_width, 768, top, 316, 42, slide.panel)
        self._draw_text(pixels, image_width, 720, 268, "1", scale=3, color=(255, 255, 255))
        self._draw_text(pixels, image_width, 720, 362, "2", scale=3, color=(255, 255, 255))
        self._draw_text(pixels, image_width, 720, 456, "3", scale=3, color=(255, 255, 255))
        self._draw_text(
            pixels,
            image_width,
            790,
            270,
            "THUMBNAIL",
            scale=3,
            color=(29, 36, 48),
        )
        self._draw_text(
            pixels,
            image_width,
            790,
            364,
            "VOICEOVER",
            scale=3,
            color=(29, 36, 48),
        )
        self._draw_text(
            pixels,
            image_width,
            790,
            458,
            "DELIVERY",
            scale=3,
            color=(29, 36, 48),
        )

    def _draw_closing_layout(
        self,
        pixels: bytearray,
        image_width: int,
        slide: SlideSpec,
    ) -> None:
        self._fill_rect(pixels, image_width, 40, 40, 1200, 640, slide.accent)
        self._fill_rect(pixels, image_width, 86, 86, 1108, 548, slide.panel)
        self._draw_header(pixels, image_width, slide, x=98, y=112, text_color=(29, 36, 48))
        self._draw_wrapped_text(
            pixels,
            image_width,
            132,
            214,
            slide.headline,
            max_width=936,
            scale=6,
            color=(29, 36, 48),
            line_spacing=18,
        )
        self._draw_body_lines(
            pixels,
            image_width,
            slide.body_lines,
            x=146,
            y=384,
            max_width=900,
            color=(70, 76, 82),
            max_lines_per_item=2,
        )
        self._fill_rect(pixels, image_width, 944, 222, 162, 162, slide.accent)
        self._draw_text(
            pixels,
            image_width,
            986,
            284,
            "OK",
            scale=8,
            color=(255, 248, 241),
        )

    def _draw_header(
        self,
        pixels: bytearray,
        image_width: int,
        slide: SlideSpec,
        *,
        x: int,
        y: int,
        text_color: tuple[int, int, int],
    ) -> None:
        self._draw_text(
            pixels,
            image_width,
            x,
            y,
            slide.eyebrow,
            scale=2,
            color=text_color,
            letter_spacing=3,
        )

    def _draw_body_lines(
        self,
        pixels: bytearray,
        image_width: int,
        body_lines: list[str],
        *,
        x: int,
        y: int,
        max_width: int,
        color: tuple[int, int, int],
        max_lines_per_item: int,
    ) -> None:
        body_y = y
        for body_line in body_lines:
            next_y = self._draw_wrapped_text(
                pixels,
                image_width,
                x,
                body_y,
                f"- {self._normalize_text(body_line)}",
                max_width=max_width,
                scale=3,
                color=color,
                line_spacing=10,
                max_lines=max_lines_per_item,
            )
            body_y = next_y + 12

    @staticmethod
    def _fill_rect(
        pixels: bytearray,
        image_width: int,
        x: int,
        y: int,
        rect_width: int,
        rect_height: int,
        color: tuple[int, int, int],
    ) -> None:
        for row in range(y, y + rect_height):
            row_start = (row * image_width + x) * 3
            for col in range(rect_width):
                offset = row_start + col * 3
                pixels[offset : offset + 3] = bytes(color)

    def _draw_wrapped_text(
        self,
        pixels: bytearray,
        image_width: int,
        x: int,
        y: int,
        text: str,
        *,
        max_width: int,
        scale: int,
        color: tuple[int, int, int],
        line_spacing: int,
        max_lines: int | None = None,
    ) -> int:
        lines = self._wrap_text(text, max_width=max_width, scale=scale)
        if max_lines is not None:
            lines = lines[:max_lines]
            if lines:
                last_line = lines[-1]
                if len(self._wrap_text(text, max_width=max_width, scale=scale)) > max_lines:
                    lines[-1] = self._truncate_visual_line(
                        last_line,
                        max_width=max_width,
                        scale=scale,
                    )
        cursor_y = y
        for line in lines:
            self._draw_text(
                pixels,
                image_width,
                x,
                cursor_y,
                line,
                scale=scale,
                color=color,
            )
            cursor_y += (7 * scale) + line_spacing
        return cursor_y

    def _draw_text(
        self,
        pixels: bytearray,
        image_width: int,
        x: int,
        y: int,
        text: str,
        *,
        scale: int,
        color: tuple[int, int, int],
        letter_spacing: int = 2,
    ) -> None:
        cursor_x = x
        for character in self._normalize_text(text):
            glyph = FONT_5X7.get(character, FONT_5X7[" "])
            for row_index, row in enumerate(glyph):
                for column_index, bit in enumerate(row):
                    if bit == "1":
                        self._fill_rect(
                            pixels,
                            image_width,
                            cursor_x + column_index * scale,
                            y + row_index * scale,
                            scale,
                            scale,
                            color,
                        )
            cursor_x += (5 * scale) + letter_spacing

    def _wrap_text(self, text: str, *, max_width: int, scale: int) -> list[str]:
        normalized = self._normalize_text(text)
        if not normalized:
            return [""]
        max_chars = max(10, max_width // ((5 * scale) + 2))
        words = normalized.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def _truncate_visual_line(self, text: str, *, max_width: int, scale: int) -> str:
        max_chars = max(10, max_width // ((5 * scale) + 2))
        if len(text) <= max_chars:
            return text
        return text[: max(0, max_chars - 3)].rstrip() + "..."

    @staticmethod
    def _extract_script_lines(script: str) -> list[str]:
        cleaned = [
            FFmpegVideoRenderer._normalize_text(line.strip(" -*"))
            for line in re.split(r"[\n\.]+", script)
            if line.strip()
        ]
        return cleaned[:8]

    @staticmethod
    def _normalize_text(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
        cleaned = re.sub(r"[^A-Za-z0-9 .:/-]", " ", ascii_only)
        collapsed = re.sub(r"\s+", " ", cleaned).strip()
        return collapsed.upper()

    def _select_theme(self, payload: RenderInput) -> RenderTheme:
        digest = hashlib.md5(
            f"{payload.project_id}:{payload.title}:{payload.script[:80]}".encode()
        ).digest()
        theme_index = digest[0] % len(RENDER_THEMES)
        return RENDER_THEMES[theme_index]


@dataclass(slots=True)
class SlideSpec:
    headline: str
    eyebrow: str
    body_lines: list[str]
    accent: tuple[int, int, int]
    panel: tuple[int, int, int]
    layout: str = "focus"
    caption: str | None = None


@dataclass(frozen=True, slots=True)
class RenderTheme:
    name: str
    background: tuple[int, int, int]
    hero_accent: tuple[int, int, int]
    hero_panel: tuple[int, int, int]
    hero_layout: str
    scene_palettes: list[tuple[tuple[int, int, int], tuple[int, int, int]]]
    scene_layouts: list[str]
    assets_accent: tuple[int, int, int]
    assets_panel: tuple[int, int, int]
    assets_layout: str
    closing_accent: tuple[int, int, int]
    closing_panel: tuple[int, int, int]
    closing_layout: str
    motif: str


RENDER_THEMES = [
    RenderTheme(
        name="cinematic-editorial",
        background=(18, 22, 31),
        hero_accent=(191, 90, 54),
        hero_panel=(248, 239, 228),
        hero_layout="hero",
        scene_palettes=[
            ((13, 127, 99), (235, 247, 243)),
            ((29, 78, 216), (239, 246, 255)),
            ((202, 138, 4), (254, 252, 232)),
        ],
        scene_layouts=["split-left", "split-right", "focus"],
        assets_accent=(71, 89, 173),
        assets_panel=(238, 241, 255),
        assets_layout="checklist",
        closing_accent=(135, 78, 163),
        closing_panel=(247, 240, 252),
        closing_layout="closing",
        motif="rings",
    ),
    RenderTheme(
        name="neon-briefing",
        background=(9, 12, 21),
        hero_accent=(0, 173, 181),
        hero_panel=(232, 250, 252),
        hero_layout="magazine",
        scene_palettes=[
            ((0, 173, 181), (230, 249, 250)),
            ((255, 87, 34), (255, 240, 234)),
            ((156, 39, 176), (247, 235, 251)),
        ],
        scene_layouts=["spotlight", "split-right", "magazine"],
        assets_accent=(33, 150, 243),
        assets_panel=(232, 245, 255),
        assets_layout="focus",
        closing_accent=(255, 111, 0),
        closing_panel=(255, 245, 230),
        closing_layout="spotlight",
        motif="bars",
    ),
    RenderTheme(
        name="warm-launch",
        background=(35, 24, 21),
        hero_accent=(205, 127, 50),
        hero_panel=(250, 242, 232),
        hero_layout="focus",
        scene_palettes=[
            ((174, 92, 62), (250, 236, 230)),
            ((103, 58, 183), (244, 239, 251)),
            ((46, 125, 50), (237, 247, 237)),
        ],
        scene_layouts=["magazine", "focus", "split-left"],
        assets_accent=(121, 85, 72),
        assets_panel=(245, 238, 235),
        assets_layout="split-left",
        closing_accent=(63, 81, 181),
        closing_panel=(236, 239, 253),
        closing_layout="closing",
        motif="blocks",
    ),
]


FONT_5X7 = {
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    ":": ["00000", "01100", "01100", "00000", "01100", "01100", "00000"],
    "/": ["00001", "00010", "00100", "01000", "10000", "00000", "00000"],
    "?": ["01110", "10001", "00010", "00100", "00100", "00000", "00100"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "11100"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11100", "10010", "10001", "10001", "10001", "10010", "11100"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "J": ["00001", "00001", "00001", "00001", "10001", "10001", "01110"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
}
