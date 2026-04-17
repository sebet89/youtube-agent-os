from __future__ import annotations

import asyncio
import importlib
import math
import re
import struct
import subprocess
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(slots=True)
class NarrationRequest:
    project_id: str
    title: str
    script: str
    output_path: str
    language: str = "pt-BR"


@dataclass(slots=True)
class NarrationResult:
    output_path: str
    provider: str
    duration_seconds: float
    metadata_json: dict[str, object] = field(default_factory=dict)


class NarrationProvider(Protocol):
    def synthesize(self, payload: NarrationRequest) -> NarrationResult:
        """Generate narration audio for a project."""


class EdgeTTSNarrationProvider(NarrationProvider):
    def __init__(self, *, voice_name: str | None = None, rate: int = 0) -> None:
        self._voice_name = voice_name or "pt-BR-AntonioNeural"
        self._rate = max(-50, min(50, rate))

    def synthesize(self, payload: NarrationRequest) -> NarrationResult:
        output_path = Path(payload.output_path).with_suffix(".mp3")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        edge_tts = self._load_edge_tts_module()
        rate = _format_edge_rate(self._rate)
        script = _normalize_narration_script(payload.script)
        try:
            asyncio.run(
                self._synthesize_with_edge_tts(
                    edge_tts=edge_tts,
                    text=script,
                    output_path=output_path,
                    rate=rate,
                )
            )
        except Exception as exc:  # pragma: no cover - runtime provider fallback path
            raise ValueError(f"Edge TTS synthesis failed. {exc}") from exc
        return NarrationResult(
            output_path=str(output_path),
            provider="edge-tts",
            duration_seconds=_estimate_narration_duration_seconds(script),
            metadata_json={
                "voice_name": self._voice_name,
                "rate": rate,
                "language": payload.language,
                "format": "mp3",
            },
        )

    async def _synthesize_with_edge_tts(
        self,
        *,
        edge_tts: Any,
        text: str,
        output_path: Path,
        rate: str,
    ) -> None:
        communicate = edge_tts.Communicate(
            text=text,
            voice=self._voice_name,
            rate=rate,
        )
        await communicate.save(str(output_path))

    @staticmethod
    def _load_edge_tts_module() -> Any:
        try:
            return importlib.import_module("edge_tts")
        except ModuleNotFoundError as exc:
            raise ValueError(
                "edge-tts is not installed. Install it with `python -m pip install edge-tts`."
            ) from exc


class WindowsSpeechNarrationProvider(NarrationProvider):
    def __init__(self, *, voice_name: str | None = None, rate: int = 0) -> None:
        self._voice_name = voice_name
        self._rate = max(-10, min(10, rate))

    def synthesize(self, payload: NarrationRequest) -> NarrationResult:
        output_path = Path(payload.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        script = self._build_powershell_script(payload, output_path)
        try:
            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    script,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise ValueError("PowerShell was not found for Windows speech synthesis.") from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            message = "Windows speech synthesis failed."
            if stderr:
                message = f"{message} {stderr}"
            raise ValueError(message) from exc
        return NarrationResult(
            output_path=str(output_path),
            provider="windows-speech",
            duration_seconds=_get_wave_duration_seconds(output_path),
            metadata_json={
                "voice_name": self._voice_name or "default",
                "rate": self._rate,
                "language": payload.language,
            },
        )

    def _build_powershell_script(self, payload: NarrationRequest, output_path: Path) -> str:
        ssml = _build_ssml_document(payload)
        escaped_ssml = _escape_powershell_literal(ssml)
        escaped_path = _escape_powershell_literal(str(output_path))
        commands = [
            "Add-Type -AssemblyName System.Speech",
            "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer",
            f"$synth.Rate = {self._rate}",
        ]
        if self._voice_name:
            commands.append(
                f"$synth.SelectVoice('{_escape_powershell_literal(self._voice_name)}')"
            )
        else:
            commands.extend(
                [
                    "$preferred = $synth.GetInstalledVoices() | "
                    "Where-Object { $_.VoiceInfo.Culture.Name -eq 'pt-BR' } | "
                    "Select-Object -First 1",
                    "if ($preferred) { $synth.SelectVoice($preferred.VoiceInfo.Name) }",
                ]
            )
        commands.extend(
            [
                f"$synth.SetOutputToWaveFile('{escaped_path}')",
                f"$synth.SpeakSsml('{escaped_ssml}')",
                "$synth.Dispose()",
            ]
        )
        return "; ".join(commands)


class SyntheticNarrationProvider(NarrationProvider):
    def __init__(self, *, sample_rate: int = 22050) -> None:
        self._sample_rate = sample_rate

    def synthesize(self, payload: NarrationRequest) -> NarrationResult:
        output_path = Path(payload.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        segments = _split_narration_segments(payload.script) or [payload.title]
        amplitude = 2600
        duration_seconds = 0.0

        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self._sample_rate)

            frames = bytearray()
            for index, segment in enumerate(segments):
                segment_duration = max(0.75, min(2.8, 0.085 * len(segment)))
                pause_duration = 0.16 if index < len(segments) - 1 else 0.0
                duration_seconds += segment_duration + pause_duration
                base_frequency = 185.0 + (index % 4) * 22.0
                segment_samples = int(self._sample_rate * segment_duration)
                pause_samples = int(self._sample_rate * pause_duration)
                for sample_index in range(segment_samples):
                    progress = sample_index / max(1, segment_samples)
                    envelope = _speech_envelope(progress)
                    vibrato = math.sin(2 * math.pi * 4.2 * (sample_index / self._sample_rate))
                    frequency = base_frequency + (12.0 * vibrato)
                    overtone = 0.35 * math.sin(
                        2 * math.pi * (frequency * 2.0) * (sample_index / self._sample_rate)
                    )
                    sample = amplitude * envelope * (
                        math.sin(2 * math.pi * frequency * (sample_index / self._sample_rate))
                        + overtone
                    )
                    frames.extend(struct.pack("<h", int(max(-32767, min(32767, sample)))))
                for _ in range(pause_samples):
                    frames.extend(struct.pack("<h", 0))
            wav_file.writeframes(frames)

        return NarrationResult(
            output_path=str(output_path),
            provider="synthetic-tone",
            duration_seconds=max(2.0, round(duration_seconds, 2)),
            metadata_json={
                "language": payload.language,
                "sample_rate": self._sample_rate,
                "style": "prosody-fallback",
            },
        )


class AutoNarrationProvider(NarrationProvider):
    def __init__(
        self,
        primary: NarrationProvider,
        fallback: NarrationProvider,
    ) -> None:
        self._primary = primary
        self._fallback = fallback

    def synthesize(self, payload: NarrationRequest) -> NarrationResult:
        try:
            return self._primary.synthesize(payload)
        except ValueError:
            return self._fallback.synthesize(payload)


def _escape_powershell_literal(value: str) -> str:
    return value.replace("'", "''")


def _get_wave_duration_seconds(output_path: Path) -> float:
    with wave.open(str(output_path), "rb") as wav_file:
        frame_count = wav_file.getnframes()
        frame_rate = wav_file.getframerate()
        if frame_rate == 0:
            return 0.0
        return round(frame_count / frame_rate, 2)


def _build_ssml_document(payload: NarrationRequest) -> str:
    segments = _split_narration_segments(payload.script) or [payload.title]
    body = "".join(
        f"<s>{_escape_xml(segment)}</s><break time='450ms'/>"
        for segment in segments
    )
    return (
        "<speak version='1.0' xml:lang='pt-BR'>"
        "<prosody rate='-8%' pitch='+2%'>"
        f"{body}"
        "</prosody>"
        "</speak>"
    )


def _split_narration_segments(script: str) -> list[str]:
    return [
        re.sub(r"\s+", " ", segment).strip()
        for segment in re.split(r"[\n.!?]+", script)
        if segment.strip()
    ]


def _escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _speech_envelope(progress: float) -> float:
    if progress < 0.1:
        return 0.25 + (progress / 0.1) * 0.75
    if progress > 0.88:
        return max(0.0, 1.0 - ((progress - 0.88) / 0.12))
    return 1.0


def _format_edge_rate(rate: int) -> str:
    if rate == 0:
        return "+0%"
    return f"{rate:+d}%"


def _normalize_narration_script(script: str) -> str:
    segments = _split_narration_segments(script)
    if not segments:
        return "Conteudo gerado para revisao humana."
    return ". ".join(segments)


def _estimate_narration_duration_seconds(script: str) -> float:
    words = [word for word in script.split() if word.strip()]
    return max(2.0, round(len(words) * 0.42, 2))
