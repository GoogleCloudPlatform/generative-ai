#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Google Cloud Text-to-Speech Narration & Subtitle Timecode Synthesizer.

Generates professional studio-quality voice audio tracks and synchronized subtitle
timecodes matching the demo's detected language (Japanese, English, German, French, etc.)
using Google Cloud Text-to-Speech API (Neural2 / Journey / Chirp voices).
Outputs a narration_manifest.json containing audio durations and subtitle segment slices.
"""

import argparse
import json
import os
import subprocess
import sys

try:
    from google.cloud import texttospeech
except ImportError:
    texttospeech = None

# Language code to recommended neural voices (Google Cloud Chirp 3 HD foundation voices)
VOICE_MAPPING = {
    "en-US": {"voice": "en-US-Chirp3-HD-Achernar", "language_code": "en-US", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "en": {"voice": "en-US-Chirp3-HD-Achernar", "language_code": "en-US", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "en-GB": {"voice": "en-GB-Chirp3-HD-Achernar", "language_code": "en-GB", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "en-AU": {"voice": "en-AU-Chirp3-HD-Achernar", "language_code": "en-AU", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "en-IN": {"voice": "en-IN-Chirp3-HD-Achernar", "language_code": "en-IN", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "ja-JP": {"voice": "ja-JP-Chirp3-HD-Aoede", "language_code": "ja-JP", "ssml_gender": "FEMALE", "speaking_rate": 1.05},
    "ja": {"voice": "ja-JP-Chirp3-HD-Aoede", "language_code": "ja-JP", "ssml_gender": "FEMALE", "speaking_rate": 1.05},
    "de-DE": {"voice": "de-DE-Chirp3-HD-Achernar", "language_code": "de-DE", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "de": {"voice": "de-DE-Chirp3-HD-Achernar", "language_code": "de-DE", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "fr-FR": {"voice": "fr-FR-Chirp3-HD-Achernar", "language_code": "fr-FR", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "fr": {"voice": "fr-FR-Chirp3-HD-Achernar", "language_code": "fr-FR", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "fr-CA": {"voice": "fr-CA-Chirp3-HD-Achernar", "language_code": "fr-CA", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "es-ES": {"voice": "es-ES-Chirp3-HD-Achernar", "language_code": "es-ES", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "es": {"voice": "es-ES-Chirp3-HD-Achernar", "language_code": "es-ES", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "es-US": {"voice": "es-US-Chirp3-HD-Achernar", "language_code": "es-US", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "it-IT": {"voice": "it-IT-Chirp3-HD-Achernar", "language_code": "it-IT", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "it": {"voice": "it-IT-Chirp3-HD-Achernar", "language_code": "it-IT", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "ko-KR": {"voice": "ko-KR-Chirp3-HD-Achernar", "language_code": "ko-KR", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "ko": {"voice": "ko-KR-Chirp3-HD-Achernar", "language_code": "ko-KR", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "cmn-CN": {"voice": "cmn-CN-Chirp3-HD-Achernar", "language_code": "cmn-CN", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "zh-CN": {"voice": "cmn-CN-Chirp3-HD-Achernar", "language_code": "cmn-CN", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "zh": {"voice": "cmn-CN-Chirp3-HD-Achernar", "language_code": "cmn-CN", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "cmn-TW": {"voice": "cmn-TW-Wavenet-A", "language_code": "cmn-TW", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "zh-TW": {"voice": "cmn-TW-Wavenet-A", "language_code": "cmn-TW", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "yue-HK": {"voice": "yue-HK-Chirp3-HD-Achernar", "language_code": "yue-HK", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "zh-HK": {"voice": "yue-HK-Chirp3-HD-Achernar", "language_code": "yue-HK", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "pt-BR": {"voice": "pt-BR-Chirp3-HD-Achernar", "language_code": "pt-BR", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "pt": {"voice": "pt-BR-Chirp3-HD-Achernar", "language_code": "pt-BR", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "pt-PT": {"voice": "pt-PT-Wavenet-E", "language_code": "pt-PT", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "nl-NL": {"voice": "nl-NL-Chirp3-HD-Achernar", "language_code": "nl-NL", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "nl": {"voice": "nl-NL-Chirp3-HD-Achernar", "language_code": "nl-NL", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "nl-BE": {"voice": "nl-BE-Chirp3-HD-Achernar", "language_code": "nl-BE", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "hi-IN": {"voice": "hi-IN-Chirp3-HD-Achernar", "language_code": "hi-IN", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "hi": {"voice": "hi-IN-Chirp3-HD-Achernar", "language_code": "hi-IN", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "ar-XA": {"voice": "ar-XA-Chirp3-HD-Achernar", "language_code": "ar-XA", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
        "ar": {"voice": "ar-XA-Chirp3-HD-Achernar", "language_code": "ar-XA", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "th-TH": {"voice": "th-TH-Chirp3-HD-Orion", "language_code": "th-TH", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
    "th": {"voice": "th-TH-Chirp3-HD-Orion", "language_code": "th-TH", "ssml_gender": "FEMALE", "speaking_rate": 1.0},
}


def resolve_voice_for_language(lang: str) -> dict:
    """Dynamically resolves neural voice parameters for any language code without Japanese leakage."""
    if not lang:
        return dict(VOICE_MAPPING["en-US"])

    normalized = lang.strip().replace("_", "-")
    # 1. Exact match (case-insensitive)
    for k, v in VOICE_MAPPING.items():
        if k.lower() == normalized.lower():
            info = dict(v)
            info.setdefault("language_code", k if "-" in k else f"{k}-{k.upper()}")
            return info

    # 2. Language prefix match
    norm_lower = normalized.lower()
    prefix = norm_lower.split("-")[0]

    prefix_map = {
        "ja": "ja-JP",
        "en": "en-US",
        "de": "de-DE",
        "fr": "fr-FR",
        "es": "es-ES",
        "it": "it-IT",
        "ko": "ko-KR",
        "zh": "cmn-CN",
        "cmn": "cmn-CN",
        "pt": "pt-BR",
        "nl": "nl-NL",
        "hi": "hi-IN",
                "ar": "ar-XA",
        "th": "th-TH",
    }
    if prefix in prefix_map:
        target_key = prefix_map[prefix]
        info = dict(VOICE_MAPPING[target_key])
        return info

    # 3. Dynamic BCP-47 candidate or neutral fallback.
    # Non-Japanese languages NEVER fall back to Japanese! Neutral fallback is strictly en-US.
    return dict(VOICE_MAPPING["en-US"])


resolve_voice_for_locale = resolve_voice_for_language


def format_tts_diagnostic_banner(error_msg: str = "", project_id: str = "") -> str:
    """Formats a loud, actionable diagnostic banner for Cloud TTS failures."""
    # Detect if arguments were passed as (project_id, error_msg)
    if error_msg and " " not in error_msg.strip() and project_id and (" " in project_id.strip() or len(project_id.strip()) > 30):
        proj = error_msg.strip()
        err = project_id.strip()
    else:
        proj = project_id.strip() if project_id else "<PROJECT_ID>"
        err = error_msg.strip() if error_msg else "Cloud Text-to-Speech API inaccessible"

    banner = [
        "",
        "=" * 80,
        "❌ [Cloud TTS Error] Text-to-Speech API is disabled or inaccessible!",
        f"   Project ID : {proj}",
        f"   Error      : {err}",
        "",
        "👉 To enable the Cloud Text-to-Speech API, run:",
        f"   gcloud services enable texttospeech.googleapis.com --project {proj}",
        "",
        "👉 If credentials or quota project need configuration, run:",
        f"   gcloud auth application-default set-quota-project {proj}",
        "   gcloud auth application-default login",
        "",
        f"👉 Or visit: https://console.developers.google.com/apis/api/texttospeech.googleapis.com/overview?project={proj}",
        "",
        "👉 For offline testing without Cloud TTS, run with --mock flag.",
        "=" * 80,
        ""
    ]
    return "\n".join(banner)


def validate_tts_readiness(project_id: str = "", lang: str = "en-US", mock: bool = False, no_narration: bool = False) -> tuple:
    """Validates Cloud TTS API enablement, credentials, and quota project before synthesis.

    Returns:
        (is_ready: bool, diagnostic_message: str)
    """
    if mock or no_narration:
        return True, "Cloud TTS bypassed (mock or no-narration mode enabled)."

    quota_project = (
        project_id
        or os.environ.get("GOOGLE_CLOUD_QUOTA_PROJECT")
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("PROJECT_ID")
    )
    if not quota_project:
        try:
            res = subprocess.run(["gcloud", "config", "get-value", "project"], capture_output=True, text=True)
            lines = [l.strip() for l in res.stdout.splitlines() if l.strip() and not l.startswith("Your active configuration")]
            if lines:
                quota_project = lines[0]
        except Exception:
            pass

    try:
        from google.cloud import texttospeech
        from google.api_core.client_options import ClientOptions

        client_options = ClientOptions(quota_project_id=quota_project) if quota_project else None
        client = texttospeech.TextToSpeechClient(client_options=client_options)

        # Lightweight probe
        v_info = resolve_voice_for_language(lang)
        voice = texttospeech.VoiceSelectionParams(
            language_code=v_info.get("language_code", "en-US"),
            name=v_info["voice"],
            ssml_gender=getattr(texttospeech.SsmlVoiceGender, v_info.get("ssml_gender", "FEMALE"))
        )
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
        client.synthesize_speech(
            input=texttospeech.SynthesisInput(text="Test"),
            voice=voice,
            audio_config=audio_config
        )
        return True, "Cloud Text-to-Speech API is ready."
    except Exception as e:
        diag = format_tts_diagnostic_banner(str(e), quota_project)
        return False, diag


def estimate_speech_duration(text: str, lang: str) -> float:
    """Estimates speech duration in seconds for timing alignment and mock fallback."""
    base_lang = lang.split("-")[0].lower()
    if base_lang in ("ja", "zh", "ko", "cmn", "yue", "th"):
        # Average CJK/Thai speech rate: ~5.0 characters per second
        clean_len = len(text.replace(" ", "").replace("\n", ""))
        return max(2.5, round(clean_len / 5.0, 2))
    else:
        # Average English/European speech rate: ~150 words per minute (2.5 words per sec)
        words = len(text.split())
        return max(2.5, round(words / 2.5, 2))


def generate_silent_audio(output_path: str, duration_sec: float):
    """Generates an empty silent MP3 audio track using ffmpeg for mock / fallback mode."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=stereo",
        "-t", str(duration_sec),
        "-q:a", "9",
        "-acodec", "libmp3lame",
        output_path
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except Exception:
        # If ffmpeg is not available, create a minimal silent MP3 audio stub
        # Frame header: 0xFF, 0xFB, 0x90, 0x64 (MPEG1 Layer III, 128 kbps, 44.1 kHz, stereo)
        # Followed by 414 bytes of zero padding = 418 bytes total per frame (~26ms)
        frame = b"\xff\xfb\x90\x64" + b"\x00" * 414
        num_frames = max(1, int(duration_sec * 38.28125))
        with open(output_path, "wb") as f:
            f.write(frame * num_frames)


def synthesize_scene_audio(text: str, output_path: str, lang: str = "en-US", mock: bool = False, project: str = "") -> float:
    """Synthesizes speech for a single scene via Google Cloud TTS or fallback."""
    if mock:
        duration = estimate_speech_duration(text, lang)
        generate_silent_audio(output_path, duration)
        return duration

    quota_project = (
        project
        or os.environ.get("GOOGLE_CLOUD_QUOTA_PROJECT")
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("PROJECT_ID")
    )
    if not quota_project:
        try:
            res = subprocess.run(["gcloud", "config", "get-value", "project"], capture_output=True, text=True)
            lines = [l.strip() for l in res.stdout.splitlines() if l.strip() and not l.startswith("Your active configuration")]
            if lines:
                quota_project = lines[0]
        except Exception:
            pass

    try:
        from google.cloud import texttospeech
        from google.api_core.client_options import ClientOptions

        client_options = ClientOptions(quota_project_id=quota_project) if quota_project else None
        client = texttospeech.TextToSpeechClient(client_options=client_options)
        v_info = resolve_voice_for_language(lang)
        language_code = v_info.get("language_code") or "en-US"

        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=v_info["voice"],
            ssml_gender=getattr(texttospeech.SsmlVoiceGender, v_info.get("ssml_gender", "FEMALE"))
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=v_info.get("speaking_rate", 1.0)
        )

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        with open(output_path, "wb") as out:
            out.write(response.audio_content)

        # Get exact duration via ffprobe if available
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", output_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            return round(float(res.stdout.strip()), 2)
        return estimate_speech_duration(text, lang)

    except Exception as e:
        diag = format_tts_diagnostic_banner(str(e), quota_project)
        print(diag, file=sys.stderr)
        raise RuntimeError(f"Cloud TTS synthesis failed: {e}\n{diag}")


def split_subtitles(text: str, total_duration: float, lang: str) -> list:
    """Splits a narration text into timed subtitle segments for Remotion lower-thirds."""
    # Split by punctuation
    base_lang = lang.split("-")[0].lower()
    if base_lang in ("ja", "zh", "ko", "cmn", "yue"):
        sentences = [s.strip() for s in text.replace("。", "。\n").replace("！", "！\n").replace("？", "？\n").split("\n") if s.strip()]
    elif base_lang == "th":
        sentences = [s.strip() for s in text.replace(" ", " \n").split("\n") if s.strip()]
    else:
        sentences = [s.strip() for s in text.replace(".", ".\n").replace("!", "!\n").replace("?", "?\n").split("\n") if s.strip()]

    if not sentences:
        return [{"text": text, "start_sec": 0.0, "end_sec": total_duration}]

    total_chars = sum(len(s) for s in sentences)
    slices = []
    curr_time = 0.0

    for idx, s in enumerate(sentences):
        ratio = len(s) / max(1, total_chars)
        dur = round(total_duration * ratio, 2)
        end_time = round(curr_time + dur, 2)
        if idx == len(sentences) - 1:
            end_time = total_duration
        slices.append({
            "text": s,
            "start_sec": curr_time,
            "end_sec": end_time
        })
        curr_time = end_time

    return slices


NARRATION_STRINGS = {
    "en": {
        "intro_title": "{company} AI Agent Demo",
        "intro_text": "Welcome to this demonstration of {role}, an autonomous AI agent built on Gemini Enterprise for {company}.",
        "agenda_title": "Walkthrough Agenda",
        "agenda_text_full": "Today's demonstration covers {num_prompts} core operational workflows for enterprise operations. We will walk through situational briefing, catalog discovery, anomaly detection, immediate action approval, root cause analysis, simulation, and daily handover.",
        "agenda_text_short": "Today's demonstration covers {num_prompts} core operational workflows. We will walk through situational briefing, catalog discovery, anomaly detection, immediate action approval, and daily handover.",
        "scene_title": "Scene {s_num}: Demonstration Scenario {s_num}",
        "scene_lead": "Now, let's proceed to demonstration scenario {s_num}.",
        "scene_think": "The agent queries underlying enterprise data stores and synthesizes the required workflow actions.",
        "scene_resp": "As the structured results appear, the agent consolidates multi-source metrics into clear recommendations. This accelerates complex operational workflows while maintaining enterprise data governance.",
        "outro_title": "Conclusion",
        "outro_text": "Gemini Enterprise empowers {company} to transform manual reviews into seamless autonomous operations. Thank you."
    },
    "ja": {
        "intro_title": "{company} AI エージェント デモ",
        "intro_text": "本日は、{company}のために開発されたGemini Enterpriseの自律型エージェント「{role}」の実演をご紹介します。",
        "agenda_title": "実演デモシナリオ一覧",
        "agenda_text_full": "本日のデモでは、製造オペレーションを変革する全{num_prompts}つの重要ワークフローをご紹介します。初期対話からデータ分析、即時承認、根本原因究明、生産シミュレーション、日次サマリーまで順を追って実演します。",
        "agenda_text_short": "本日のデモでは、主要な全{num_prompts}つの重要ワークフローをご紹介します。初期対話からデータ分析、即時承認、そして日次サマリーまで順を追って実演します。",
        "scene_title": "Scene {s_num}: デモシナリオ {s_num}",
        "scene_lead": "それでは、続いてのデモシナリオの実演に移ります。",
        "scene_think": "エージェントが基幹データソースを照会し、要求されたワークフローを自律的に推論しています。",
        "scene_resp": "画面に構造化された分析結果が表示され、多角的な知見が整理されます。これにより、高度なエンタープライズ業務を迅速かつ確実に遂行できます。",
        "outro_title": "まとめ",
        "outro_text": "このように、{company}の業務オペレーションをGemini Enterpriseが強力に加速します。ご清聴ありがとうございました。"
    },
    "de": {
        "intro_title": "{company} KI-Agent Demo",
        "intro_text": "Herzlich willkommen zu dieser Demonstration von {role}, einem autonomen KI-Agenten auf Basis von Gemini Enterprise für {company}.",
        "agenda_title": "Walkthrough-Agenda",
        "agenda_text_full": "Die heutige Demonstration umfasst {num_prompts} zentrale operative Workflows für Unternehmensabläufe. Wir demonstrieren Situationsanalyse, Katalogabfragen, Anomalieerkennung, sofortige Handlungsfreigaben, Ursachenanalyse, Simulation und die tägliche Übergabe.",
        "agenda_text_short": "Die heutige Demonstration umfasst {num_prompts} zentrale operative Workflows. Wir demonstrieren Situationsanalyse, Katalogabfragen, Anomalieerkennung, sofortige Handlungsfreigaben und die tägliche Übergabe.",
        "scene_title": "Szene {s_num}: Demonstrationsszenario {s_num}",
        "scene_lead": "Lassen Sie uns nun mit Demonstrationsszenario {s_num} fortfahren.",
        "scene_think": "Der Agent fragt die zugrunde liegenden Unternehmensdaten ab und synthetisiert die erforderlichen Workflow-Aktionen.",
        "scene_resp": "Sobald die strukturierten Ergebnisse erscheinen, konsolidiert der Agent Daten aus mehreren Quellen in klare Empfehlungen. Dies beschleunigt komplexe operative Abläufe unter Wahrung der Daten-Governance.",
        "outro_title": "Fazit",
        "outro_text": "Gemini Enterprise ermöglicht es {company}, manuelle Prüfungen in nahtlose autonome Prozesse zu transformieren. Vielen Dank."
    },
    "fr": {
        "intro_title": "Démo de l'Agent IA {company}",
        "intro_text": "Bienvenue dans cette démonstration de {role}, un agent IA autonome développé sur Gemini Enterprise pour {company}.",
        "agenda_title": "Au programme",
        "agenda_text_full": "La démonstration d'aujourd'hui couvre {num_prompts} processus opérationnels majeurs. Nous allons passer en revue l'analyse de situation, la découverte de catalogue, la détection d'anomalies, l'approbation d'actions immédiates, l'analyse des causes profondes, la simulation et le compte-rendu quotidien.",
        "agenda_text_short": "La démonstration d'aujourd'hui couvre {num_prompts} processus opérationnels majeurs. Nous allons passer en revue l'analyse de situation, la découverte de catalogue, la détection d'anomalies, l'approbation d'actions immédiates et le compte-rendu quotidien.",
        "scene_title": "Scène {s_num} : Scénario de démonstration {s_num}",
        "scene_lead": "Passons maintenant au scénario de démonstration {s_num}.",
        "scene_think": "L'agent interroge les bases de données de l'entreprise et synthétise les actions requises.",
        "scene_resp": "À l'affichage des résultats structurés, l'agent consolide les mesures multi-sources en recommandations claires. Cela accélère les flux de travail complexes tout en maintenant la gouvernance des données.",
        "outro_title": "Conclusion",
        "outro_text": "Gemini Enterprise aide {company} à transformer des processus manuels en opérations autonomes fluides. Merci de votre attention."
    },
    "es": {
        "intro_title": "Demostración del Agente de IA para {company}",
        "intro_text": "Bienvenidos a esta demostración de {role}, un agente de IA autónomo desarrollado con Gemini Enterprise para {company}.",
        "agenda_title": "Agenda de la Demostración",
        "agenda_text_full": "La demostración de hoy abarca {num_prompts} flujos de trabajo operativos clave. Revisaremos el reporte de situación, la exploración del catálogo, la detección de anomalías, las aprobaciones inmediatas, el análisis de causa raíz, la simulación y el informe diario.",
        "agenda_text_short": "La demostración de hoy abarca {num_prompts} flujos de trabajo operativos clave. Revisaremos el reporte de situación, la exploración del catálogo, la detección de anomalías, las aprobaciones inmediatas y el informe diario.",
        "scene_title": "Escena {s_num}: Escenario de Demostración {s_num}",
        "scene_lead": "A continuación, procedamos con el escenario de demostración {s_num}.",
        "scene_think": "El agente consulta las fuentes de datos corporativas pertinentes y sintetiza las acciones necesarias para el flujo de trabajo.",
        "scene_resp": "Al mostrar los resultados estructurados, el agente consolida las métricas de múltiples fuentes en recomendaciones claras. Esto acelera los flujos operativos complejos preservando la gobernanza de datos empresariales.",
        "outro_title": "Conclusión",
        "outro_text": "Gemini Enterprise impulsa a {company} para transformar revisiones manuales en operaciones autónomas y fluidas. Muchas gracias."
    },
    "it": {
        "intro_title": "Demo dell'Agente IA per {company}",
        "intro_text": "Benvenuti a questa dimostrazione di {role}, un agente IA autonomo sviluppato su Gemini Enterprise per {company}.",
        "agenda_title": "Programma della Dimostrazione",
        "agenda_text_full": "La dimostrazione di oggi riguarda {num_prompts} flussi di lavoro operativi fondamentali. Esamineremo il briefing situazionale, l'esplorazione del catalogo, il rilevamento di anomalie, l'approvazione immediata di azioni, l'analisi delle cause profonde, la simulazione e la consegna giornaliera.",
        "agenda_text_short": "La dimostrazione di oggi riguarda {num_prompts} flussi di lavoro operativi fondamentali. Esamineremo il briefing situazionale, l'esplorazione del catalogo, il rilevamento di anomalie, l'approvazione immediata di azioni e la consegna giornaliera.",
        "scene_title": "Scena {s_num}: Scenario Operativo {s_num}",
        "scene_lead": "Procediamo ora con lo scenario operativo {s_num}.",
        "scene_think": "L'agente interroga i database aziendali e sintetizza in autonomia le azioni richieste per il flusso di lavoro.",
        "scene_resp": "Visualizzando i risultati, l'agente consolida le metriche da più fonti offrendo chiare raccomandazioni. Ciò accelera le operazioni complesse preservando la sicurezza dei dati aziendali.",
        "outro_title": "Conclusione",
        "outro_text": "Gemini Enterprise supporta {company} nel trasformare revisioni manuali in processi autonomi ottimizzati. Grazie per l'attenzione."
    },
    "ko": {
        "intro_title": "{company} AI 에이전트 데모",
        "intro_text": "환영합니다. 본 시연에서는 {company}를 위해 Gemini Enterprise를 기반으로 구축된 자율 AI 에이전트인 {role}을(를) 소개합니다.",
        "agenda_title": "데모 시나리오 개요",
        "agenda_text_full": "오늘 데모에서는 기업 운영을 위한 {num_prompts}가지 핵심 워크플로를 다룹니다. 상황 브리핑, 카탈로그 검색, 이상치 탐지, 즉각적인 조치 승인, 근본 원인 분석, 시뮬레이션 및 일일 인수인계 과정을 순서대로 보여드립니다.",
        "agenda_text_short": "오늘 데모에서는 기업 운영을 위한 {num_prompts}가지 핵심 워크플로를 다룹니다. 상황 브리핑, 카탈로그 검색, 이상치 탐지, 즉각적인 조치 승인 및 일일 인수인계 과정을 순서대로 보여드립니다.",
        "scene_title": "장면 {s_num}: 데모 시나리오 {s_num}",
        "scene_lead": "이제 데모 시나리오 {s_num}을(를) 진행하겠습니다.",
        "scene_think": "에이전트가 기반 기업 데이터 스토어를 쿼리하고 필요한 워크플로 조치를 도출합니다.",
        "scene_resp": "구조화된 결과가 나타나면 에이전트는 다양한 출처의 지표를 명확한 권장 사항으로 통합합니다. 이는 엔터프라이즈 데이터 거버넌스를 유지하면서 복잡한 운영 워크플로를 가속화합니다.",
        "outro_title": "결론",
        "outro_text": "Gemini Enterprise는 {company}가 수동 검토 작업을 원활한 자율 운영으로 혁신할 수 있도록 지원합니다. 감사합니다."
    },
    "zh": {
        "intro_title": "{company} AI 智能体演示",
        "intro_text": "欢迎观看本次演示，了解我们为 {company} 打造的基于 Gemini Enterprise 的自主 AI 智能体 {role}。",
        "agenda_title": "演示议程",
        "agenda_text_full": "今天的演示将涵盖企业运营的 {num_prompts} 个核心工作流。我们将依次展示情况简报、目录查询、异常检测、即时操作审批、根本原因分析、模拟预测以及日常交接。",
        "agenda_text_short": "今天的演示将涵盖企业运营的 {num_prompts} 个核心工作流。我们将依次展示情况简报、目录查询、异常检测、即时操作审批以及日常交接。",
        "scene_title": "场景 {s_num}：演示场景 {s_num}",
        "scene_lead": "现在，让我们进入演示场景 {s_num}。",
        "scene_think": "智能体正在查询企业级底层数据存储，并综合出所需的工作流操作。",
        "scene_resp": "随着结构化结果的显示，智能体会将多源指标整合为明确的建议。这在保持企业数据治理的同时，加速了复杂的运营工作流。",
        "outro_title": "总结",
        "outro_text": "Gemini Enterprise 赋能 {company}，帮助将人工审核转化为无缝的自动化运营。感谢您的观看。"
    },
    # Traditional Chinese. Keyed by full locale, not by base language: zh-TW and
    # zh-HK resolve to Traditional-script voices, and pairing those with the
    # Simplified copy above would put the wrong script on screen in the subtitles.
    "zh-TW": {
        "intro_title": "{company} AI 智慧代理程式展示",
        "intro_text": "歡迎觀看本次展示，了解我們為 {company} 打造、以 Gemini Enterprise 為基礎的自主 AI 代理程式 {role}。",
        "agenda_title": "展示議程",
        "agenda_text_full": "今天的展示將涵蓋企業營運的 {num_prompts} 項核心工作流程。我們將依序展示情境簡報、目錄查詢、異常偵測、即時作業核准、根本原因分析、模擬預測以及每日交接。",
        "agenda_text_short": "今天的展示將涵蓋企業營運的 {num_prompts} 項核心工作流程。我們將依序展示情境簡報、目錄查詢、異常偵測、即時作業核准以及每日交接。",
        "scene_title": "場景 {s_num}：展示情境 {s_num}",
        "scene_lead": "現在，讓我們進入展示情境 {s_num}。",
        "scene_think": "代理程式正在查詢企業底層資料儲存區，並彙整出所需的工作流程動作。",
        "scene_resp": "隨著結構化結果顯示，代理程式會將多來源指標整合為明確的建議。這在維持企業資料治理的同時，加速了複雜的營運流程。",
        "outro_title": "總結",
        "outro_text": "Gemini Enterprise 助力 {company}，將人工審查轉化為順暢的自主營運。感謝您的觀看。"
    },
    "pt": {
        "intro_title": "Demonstração do Agente de IA para a {company}",
        "intro_text": "Bem-vindos a esta demonstração do {role}, um agente de IA autônomo desenvolvido na plataforma Gemini Enterprise para a {company}.",
        "agenda_title": "Agenda da Demonstração",
        "agenda_text_full": "A demonstração de hoje aborda {num_prompts} fluxos operacionais centrais. Exploraremos: análise de situação, pesquisa de catálogo, detecção de anomalias, aprovação de ações imediatas, análise de causa raiz, simulação e o repasse diário.",
        "agenda_text_short": "A demonstração de hoje aborda {num_prompts} fluxos operacionais centrais. Exploraremos: análise de situação, pesquisa de catálogo, detecção de anomalias, aprovação de ações imediatas e o repasse diário.",
        "scene_title": "Cena {s_num}: Cenário de Demonstração {s_num}",
        "scene_lead": "A seguir, avançaremos para o cenário de demonstração {s_num}.",
        "scene_think": "O agente consulta os bancos de dados corporativos e organiza as ações requisitadas para o fluxo de trabalho.",
        "scene_resp": "Conforme os resultados aparecem na tela, o agente consolida métricas de múltiplas fontes em recomendações claras. Isso acelera fluxos complexos, preservando a governança dos dados da empresa.",
        "outro_title": "Conclusão",
        "outro_text": "A plataforma Gemini Enterprise capacita a {company} na transformação de processos manuais em operações autônomas contínuas. Agradecemos a atenção."
    },
    "nl": {
        "intro_title": "{company} AI-Agent Demo",
        "intro_text": "Welkom bij deze demonstratie van {role}, een autonome AI-agent gebouwd op Gemini Enterprise voor {company}.",
        "agenda_title": "Agenda van de Demonstratie",
        "agenda_text_full": "Onze demonstratie van vandaag omvat {num_prompts} kernworkflows voor ondernemingsactiviteiten. We zullen kijken naar situatie-briefings, catalogusontdekkingen, anomaliedetecties, directe goedkeuringen van acties, oorzakenanalyses, simulaties en de dagelijkse overdracht.",
        "agenda_text_short": "Onze demonstratie van vandaag omvat {num_prompts} kernworkflows voor ondernemingsactiviteiten. We zullen kijken naar situatie-briefings, catalogusontdekkingen, anomaliedetecties, directe goedkeuringen van acties en de dagelijkse overdracht.",
        "scene_title": "Scène {s_num}: Demonstratiescenario {s_num}",
        "scene_lead": "Laten we nu verdergaan met demonstratiescenario {s_num}.",
        "scene_think": "De agent bevraagt de onderliggende datastores van de onderneming en synthetiseert de vereiste workflowacties.",
        "scene_resp": "Zodra de gestructureerde resultaten verschijnen, consolideert de agent meetgegevens uit meerdere bronnen in heldere aanbevelingen. Dit versnelt complexe operationele workflows met behoud van datagovernance.",
        "outro_title": "Conclusie",
        "outro_text": "Gemini Enterprise stelt {company} in staat om handmatige reviews om te zetten in naadloos autonome operaties. Hartelijk dank."
    },
    "hi": {
        "intro_title": "{company} एआई एजेंट डेमो",
        "intro_text": "जेमिनी एंटरप्राइज़ पर {company} के लिए निर्मित एक स्वायत्त एआई एजेंट, {role}, के इस प्रदर्शन में आपका स्वागत है।",
        "agenda_title": "प्रदर्शन कार्यसूची",
        "agenda_text_full": "आज के प्रदर्शन में उद्यम संचालन के लिए {num_prompts} प्रमुख कार्यप्रवाह शामिल हैं। हम स्थिति ब्रीफिंग, कैटलॉग खोज, विसंगति का पता लगाने, तत्काल कार्रवाई की मंजूरी, मूल कारण विश्लेषण, सिमुलेशन, और दैनिक हैंडओवर (हस्तांतरण) की प्रक्रिया देखेंगे।",
        "agenda_text_short": "आज के प्रदर्शन में उद्यम संचालन के लिए {num_prompts} प्रमुख कार्यप्रवाह शामिल हैं। हम स्थिति ब्रीफिंग, कैटलॉग खोज, विसंगति का पता लगाने, तत्काल कार्रवाई की मंजूरी और दैनिक हैंडओवर (हस्तांतरण) की प्रक्रिया देखेंगे।",
        "scene_title": "दृश्य {s_num}: प्रदर्शन परिदृश्य {s_num}",
        "scene_lead": "अब, हम प्रदर्शन परिदृश्य {s_num} की ओर बढ़ते हैं।",
        "scene_think": "एजेंट उद्यम के डेटा स्रोतों में क्वेरी करता है और आवश्यक कार्यप्रवाह को निष्पादित करता है।",
        "scene_resp": "जैसे ही संरचित परिणाम सामने आते हैं, एजेंट कई स्रोतों से प्राप्त मेट्रिक्स को स्पष्ट सुझावों में समेकित करता है। इससे डेटा गवर्नेंस को बनाए रखते हुए जटिल उद्यम कार्यप्रवाह में तेज़ी आती है।",
        "outro_title": "निष्कर्ष",
        "outro_text": "जेमिनी एंटरप्राइज़ {company} को मैन्युअल प्रक्रियाओं को सहज और स्वायत्त संचालन में बदलने का अधिकार देता है। धन्यवाद।"
    },
    "ar": {
        "intro_title": "عرض وكيل الذكاء الاصطناعي لشركة {company}",
        "intro_text": "مرحباً بكم في هذا العرض التوضيحي لـ {role}، وهو وكيل ذكاء اصطناعي مستقل مبني على جيميناي إنتربرايز لشركة {company}.",
        "agenda_title": "جدول العرض التوضيحي",
        "agenda_text_full": "يغطي العرض التوضيحي اليوم {num_prompts} من مسارات العمل التشغيلية الأساسية. سنتطرق إلى ملخص الحالة، واستكشاف الكتالوج، واكتشاف الحالات الشاذة، والموافقات الفورية على الإجراءات، وتحليل الأسباب الجذرية، والمحاكاة، بالإضافة إلى التسليم اليومي.",
        "agenda_text_short": "يغطي العرض التوضيحي اليوم {num_prompts} من مسارات العمل التشغيلية الأساسية. سنتطرق إلى ملخص الحالة، واستكشاف الكتالوج، واكتشاف الحالات الشاذة، والموافقات الفورية على الإجراءات، بالإضافة إلى التسليم اليومي.",
        "scene_title": "المشهد {s_num}: سيناريو العرض {s_num}",
        "scene_lead": "الآن، دعونا ننتقل إلى سيناريو العرض {s_num}.",
        "scene_think": "يقوم الوكيل بالاستعلام عن قواعد البيانات الخاصة بالمؤسسة ويقوم بتجميع الإجراءات المطلوبة لمسار العمل.",
        "scene_resp": "بمجرد ظهور النتائج المنظمة، يقوم الوكيل بتوحيد المقاييس من مصادر متعددة في توصيات واضحة. مما يسرع العمليات التشغيلية المعقدة مع الحفاظ على حوكمة البيانات.",
        "outro_title": "الخاتمة",
        "outro_text": "تعمل جيميناي إنتربرايز على تمكين {company} من تحويل المراجعات اليدوية إلى عمليات مستقلة وسلسة. شكرًا لكم."
    },
    "th": {
        "intro_title": "การสาธิต AI Agent ของ {company}",
        "intro_text": "ยินดีต้อนรับสู่การสาธิต {role} ซึ่งเป็นตัวแทน AI อัตโนมัติที่พัฒนาบนแพลตฟอร์ม Gemini Enterprise สำหรับ {company}",
        "agenda_title": "หัวข้อการสาธิต",
        "agenda_text_full": "การสาธิตในวันนี้ครอบคลุมกระบวนการทำงานหลัก {num_prompts} ประการสำหรับการดำเนินธุรกิจ เราจะพิจารณาสรุปสถานการณ์, การสำรวจแค็ตตาล็อก, การตรวจจับความผิดปกติ, การอนุมัติการดำเนินการทันที, การวิเคราะห์สาเหตุที่แท้จริง, การจำลองสถานการณ์ และการส่งมอบงานประจำวัน",
        "agenda_text_short": "การสาธิตในวันนี้ครอบคลุมกระบวนการทำงานหลัก {num_prompts} ประการสำหรับการดำเนินธุรกิจ เราจะพิจารณาสรุปสถานการณ์, การสำรวจแค็ตตาล็อก, การตรวจจับความผิดปกติ, การอนุมัติการดำเนินการทันที และการส่งมอบงานประจำวัน",
        "scene_title": "ฉากที่ {s_num}: สถานการณ์จำลองที่ {s_num}",
        "scene_lead": "ตอนนี้ เรามารับชมสถานการณ์จำลองที่ {s_num} กันเลย",
        "scene_think": "ระบบ AI กำลังสืบค้นโครงสร้างข้อมูลพื้นฐานขององค์กรและวิเคราะห์การทำงานที่จำเป็นตามกระบวนการ",
        "scene_resp": "เมื่อผลลัพธ์ที่เป็นโครงสร้างปรากฏขึ้น ระบบ AI จะรวบรวมข้อมูลจากหลายแหล่งให้เป็นข้อเสนอแนะที่ชัดเจน ซึ่งช่วยเร่งกระบวนการทำงานที่ซับซ้อนไปพร้อมกับการรักษาธรรมมาภิบาลของข้อมูลองค์กร",
        "outro_title": "บทสรุป",
        "outro_text": "Gemini Enterprise ช่วยให้ {company} สามารถเปลี่ยนกระบวนการตรวจสอบโดยมนุษย์ไปสู่ระบบการทำงานอัตโนมัติที่ไร้รอยต่อ ขอบคุณที่รับชม"
    }
}

script_templates_ja = {
        1: (
            "Scene 1: 初期対話と状況把握",
            "それでは、プラントの初期対話と状況把握の実演を行います。",
            "エージェントが基幹システムと各ラインのシフトログを横断検索し、優先アラートを抽出しています。",
            "リアルタイムにパーソナライズされた挨拶カードと優先タスクが提示され、各ラインの稼働状態や重要アラートが一目で把握できます。朝のダッシュボード巡回やメール確認の工数をゼロにし、即座に重要課題の意思決定に着手できます。"
        ),
        2: (
            "Scene 2: メタデータと製品カタログ探索",
            "続いて、全自動組み立てセルの設備仕様と稼働ステータスの照会を行います。",
            "エージェントが設備マスタとIoTゲートウェイを照合し、各セルの詳細稼働パラメータを収集しています。",
            "生成された一覧表には、セルごとのサイクルタイム、油圧圧力、メンテナンス予定日が網羅的に整理されています。各工場への個別確認を不要にし、設備の健全性とボトルネックを秒速で可視化します。"
        ),
        3: (
            "Scene 3: 複合データ分析と不整合検知",
            "次に、サプライヤーの納品実績と製造オーダーを突合し、部品欠品や納期の不整合を検知します。",
            "エージェントがBigQuery上の納品履歴とERPの生産スケジュールを自律突合し、納品遅延の影響を分析しています。",
            "分析結果では、Apex社からのタービンブレードに5日間の遅延が発生し、ライン停止の重大リスクがあることが特定されました。複数データソースの高度なクロス分析を自然言語で完了し、サプライチェーンの寸断を未然に防ぎます。"
        ),
        4: (
            "Scene 4: 即時アクションとワークフロー承認",
            "それでは、タービンラインの欠品を解消するための緊急在庫移管プランを策定し、承認指示書を起票します。",
            "エージェントが近隣倉庫の安全在庫と輸送リードタイムを計算し、ERP移管申請データを自動生成しています。",
            "画面にはオースティン倉庫から40個を緊急転送するプランと、ワンクリックで実行できる承認カードが表示されます。承認ボタンを押すだけでERP台帳が即座に更新され、部門間の調整工数を95％削減して即時対応を可能にします。"
        ),
        5: (
            "Scene 5: 根本原因分析と品質検査",
            "続いて、センサーの振動テレメトリと不良ログを解析し、鋳造異常の根本原因を究明します。",
            "エージェントが高周波振動波形と加熱バッチ履歴を統計解析し、異常振動の発生パターンを特定しています。",
            "詳細レポートにより、第3サイクルの高調波振動が油圧ダンパーのキャリブレーション不良に起因していることが判明しました。熟練技術者の勘に頼っていた品質調査をAIが自動化し、不良品の流出と手戻りを確実に根絶します。"
        ),
        6: (
            "Scene 6: 生産計画シミュレーションと予測的配分",
            "次に、現在の供給制約下における翌日のラインスループットをシミュレーションし、最適なスケジュールを再配分します。",
            "エージェントが代替ラインの設備能力と部材納期を考慮し、最適な負荷分散シナリオを計算しています。",
            "シミュレーション結果として、第2セルへの工程シフトによりスループットを12％改善し、納期を順守する最適配分案が提示されました。突発的な供給変動に対しても、納期を厳守する最適な生産体制を即座に再構築できます。"
        ),
        7: (
            "Scene 7: 業務サマリーと推奨事項",
            "最後に、本日の対応実績サマリーと明日に向けた発注推奨事項を作成します。",
            "エージェントが本日の緊急移管実績、設備メンテナンスログ、明日の発注優先度を統括レポートに集約しています。",
            "出力されたエグゼクティブサマリーには、本日の対処結果と明朝発注すべきサプライヤー推奨数量が整然と構造化されています。業務の引き継ぎ漏れを根絶し、属人化を排除した継続的なオペレーションエクセレンスを確立します。"
        ),
    }

script_templates_en = {
        1: (
            "Scene 1: Welcome & Situational Briefing",
            "Now, let's begin with our situational operational briefing by querying current assembly alerts.",
            "While the agent queries active line status and cross-references shift logs across manufacturing plants, it isolates critical equipment warnings.",
            "The agent returns a structured welcome briefing with priority operational alerts, highlighting turbine cell throughput and pending material handovers. This completely eliminates morning dashboard hopping, providing plant leadership with immediate situational clarity."
        ),
        2: (
            "Scene 2: Metadata & Catalog Discovery",
            "Next, let's inspect component specifications and operational status across all automated assembly cells.",
            "The agent scans the enterprise asset registry, correlating cell telemetry, operating parameters, and scheduled maintenance intervals.",
            "A comprehensive equipment specifications table is generated, detailing cycle times, hydraulic pressure thresholds, and active health metrics for cells one through four. Plant managers gain instant visibility into machine health across facilities without manual database queries or engineering escalations."
        ),
        3: (
            "Scene 3: Cross-Source Anomaly Detection",
            "We now proceed to cross-reference recent supplier shipments against active production orders to detect component shortages.",
            "The agent autonomously joins BigQuery supplier dispatch ledgers with ERP production schedules to uncover shipment variances.",
            "The resulting analysis table isolates a critical five-day delay on titanium turbine blades from Apex Aerospace, pinpointing an impending line stoppage. Autonomous cross-source reconciliation surfaces supply chain vulnerabilities before they cascade into plant downtime."
        ),
        4: (
            "Scene 4: Immediate Workflow Execution",
            "Now, let's formulate an emergency component transfer plan to resolve the turbine line shortage and prepare the authorization.",
            "The agent evaluates safety stock across secondary warehouses, calculates transit lead times, and prepares a formal ERP transfer order.",
            "It presents an emergency transfer plan reallocating forty units from the Austin depot, complete with an interactive one-click authorization card. Clicking the approval executes the transfer instantly in ERP, slashing inter-facility logistics coordination from hours to seconds."
        ),
        5: (
            "Scene 5: Root Cause Analysis & Quality Inspection",
            "Next, let's perform root cause analysis on sensor vibration telemetry and defect logs to investigate recent casting anomalies.",
            "The agent performs deep statistical correlation between high-frequency vibration spikes, furnace temperatures, and raw material heat batches.",
            "The diagnostic report pinpoints high vibration harmonics during casting cycle three, isolating an uncalibrated hydraulic dampener. Predictive vibration analytics prevents defective castings from reaching downstream assembly, safeguarding product quality and warranty margins."
        ),
        6: (
            "Scene 6: Predictive Planning & Line Simulation",
            "Moving to predictive planning, let's simulate tomorrow's line throughput under current supply constraints and rebalance the schedule.",
            "The agent models machine capacity across alternative cell routings, factoring in operator availability and component lead times.",
            "The simulation projects a twelve percent throughput uplift by rerouting sub-assemblies to Cell Two, maintaining customer delivery commitments. Dynamic production rebalancing empowers operations teams to absorb supply shocks without compromising schedule integrity."
        ),
        7: (
            "Scene 7: Operational Summary & Recommendations",
            "Finally, let's generate the executive end-of-day operations summary, capturing today's reallocations and tomorrow's procurement priorities.",
            "The agent synthesizes today's emergency transfer records, defect resolutions, and line balancing adjustments into an executive handover.",
            "The resulting executive report summarizes resolved alerts, confirms forty diverted turbine blades, and outlines high-priority supplier purchase orders. This guarantees seamless shift handovers, prevents operational blind spots, and establishes institutional excellence across all manufacturing operations."
        ),
    }

def _narration_pack(lang: str, company: str, role: str, num_prompts: int) -> dict:
    parts = lang.split("-")
    base_lang = parts[0].lower()
    region = parts[1].upper() if len(parts) > 1 else ""

    # 1. Map known fallbacks for regional dialects if they weren't explicitly defined
    if base_lang == "cmn":
        base_lang = "zh"
    elif base_lang == "yue":
        # Cantonese is written in Traditional script.
        base_lang = "zh"
        region = region or "HK"

    # 2. Select language pack. A full locale wins over its base language, because
    #    some regions differ in script rather than only in accent: zh-TW and zh-HK
    #    are read by Traditional-script voices, so Simplified copy would put the
    #    wrong characters in the subtitles.
    full_locale = "%s-%s" % (base_lang, region) if region else ""
    if full_locale and full_locale in NARRATION_STRINGS:
        pack = NARRATION_STRINGS[full_locale]
    elif base_lang == "zh" and region in ("TW", "HK", "MO"):
        pack = NARRATION_STRINGS["zh-TW"]
    elif base_lang in NARRATION_STRINGS:
        pack = NARRATION_STRINGS[base_lang]
    else:
        pack = NARRATION_STRINGS["en"]
        print(f"Note: Narration language '{base_lang}' not fully defined. Falling back to English.", file=sys.stderr)

    # 3. Choose agenda text based on num_prompts
    agenda_key = "agenda_text_full" if num_prompts >= 7 else "agenda_text_short"
    
    # 4. Resolve templates for per-scene narratives
    scene_templates = {}
    if base_lang == "ja":
        scene_templates = script_templates_ja
    elif base_lang == "en":
        scene_templates = script_templates_en
    # Fallback uses empty dictionary, meaning the scene loop will use the default properties in `pack`

    return {
        "intro_title": pack["intro_title"].format(company=company, role=role),
        "intro_text": pack["intro_text"].format(company=company, role=role),
        "agenda_title": pack["agenda_title"],
        "agenda_text": pack[agenda_key].format(num_prompts=num_prompts),
        "scene_fallback": {
            "title": pack["scene_title"],
            "lead_text": pack["scene_lead"],
            "think_text": pack["scene_think"],
            "resp_text": pack["scene_resp"],
        },
        "outro_title": pack["outro_title"],
        "outro_text": pack["outro_text"].format(company=company, role=role),
        "scene_templates": scene_templates
    }


def build_narration_script(company: str, role: str, lang: str, prompts: list = None) -> list:
    """Returns structured narration lines for demo scenes."""
    num_prompts = len(prompts) if prompts else 7
    pack = _narration_pack(lang, company, role, num_prompts)

    scenes = [
        {
            "scene_id": "intro",
            "title": pack["intro_title"],
            "text": pack["intro_text"]
        },
        {
            "scene_id": "agenda",
            "title": pack["agenda_title"],
            "text": pack["agenda_text"]
        }
    ]

    prompts_to_iterate = prompts if prompts else [f"Prompt {i}" for i in range(1, 8)]
    for idx, p in enumerate(prompts_to_iterate):
        s_num = idx + 1
        
        # Use full pre-crafted templates if available for this specific scene, else format the fallbacks
        if s_num in pack["scene_templates"]:
            title, lead_text, think_text, resp_text = pack["scene_templates"][s_num]
        else:
            fb = pack["scene_fallback"]
            title = fb["title"].format(s_num=s_num)
            lead_text = fb["lead_text"].format(s_num=s_num)
            think_text = fb["think_text"].format(s_num=s_num)
            resp_text = fb["resp_text"].format(s_num=s_num)

        scenes.append({
            "scene_id": f"prompt_{s_num}",
            "title": title,
            "lead_text": lead_text,
            "think_text": think_text,
            "resp_text": resp_text,
            "text": f"{lead_text} {think_text} {resp_text}".strip()
        })

    scenes.append({
        "scene_id": "outro",
        "title": pack["outro_title"],
        "text": pack["outro_text"]
    })
    return scenes
def synthesize_all(args) -> dict:
    """Synthesizes audio tracks and subtitle manifests for all scenes."""
    os.makedirs(args.outdir, exist_ok=True)
    lang = args.lang or ("ja-JP" if os.environ.get("CURRENCY_SYMBOL") in ("¥", "円") else "en-US")
    company = args.company or os.environ.get("COMPANY_NAME", "Enterprise Demo")
    role = args.role or os.environ.get("DEMO_DISPLAY_NAME", "Operations Director")
    project_id = getattr(args, "project", "") or os.environ.get("PROJECT_ID", "")

    # Proactive preflight validation
    ready, diag = validate_tts_readiness(project_id=project_id, lang=lang, mock=getattr(args, "mock", False), no_narration=False)
    if not ready and not getattr(args, "mock", False):
        print(diag, file=sys.stderr)
        sys.exit(1)

    script_scenes = build_narration_script(company, role, lang, prompts=getattr(args, "prompts", None))
    manifest_scenes = []
    total_audio_duration = 0.0

    print(f"🎙️ Synthesizing narration audio (Language: {lang}, Company: {company}, Role: {role})...")

    for idx, sc in enumerate(script_scenes):
        scene_id = sc["scene_id"]
        audio_filename = f"audio_{scene_id}.mp3"
        audio_path = os.path.join(args.outdir, audio_filename)

        print(f"  Generating voice track for {scene_id}...")
        dur = synthesize_scene_audio(sc["text"], audio_path, lang=lang, mock=args.mock, project=getattr(args, "project", ""))
        total_audio_duration += dur

        subtitles = split_subtitles(sc["text"], dur, lang=lang)

        scene_entry = {
            "scene_id": scene_id,
            "title": sc["title"],
            "narration_text": sc["text"],
            "audio_file": audio_filename,
            "duration_sec": dur,
            "subtitles": subtitles
        }

        # If scene has structured phases (lead, thinking, response), synthesize per-phase audio
        if "lead_text" in sc and "think_text" in sc and "resp_text" in sc:
            lead_filename = f"audio_{scene_id}_lead.mp3"
            think_filename = f"audio_{scene_id}_think.mp3"
            resp_filename = f"audio_{scene_id}_resp.mp3"

            dur_lead = synthesize_scene_audio(sc["lead_text"], os.path.join(args.outdir, lead_filename), lang=lang, mock=args.mock, project=getattr(args, "project", ""))
            dur_think = synthesize_scene_audio(sc["think_text"], os.path.join(args.outdir, think_filename), lang=lang, mock=args.mock, project=getattr(args, "project", ""))
            dur_resp = synthesize_scene_audio(sc["resp_text"], os.path.join(args.outdir, resp_filename), lang=lang, mock=args.mock, project=getattr(args, "project", ""))

            subs_lead = split_subtitles(sc["lead_text"], dur_lead, lang=lang)
            subs_think = split_subtitles(sc["think_text"], dur_think, lang=lang)
            subs_resp = split_subtitles(sc["resp_text"], dur_resp, lang=lang)

            scene_entry["phases"] = {
                "lead": {
                    "text": sc["lead_text"],
                    "audio_file": lead_filename,
                    "duration_sec": dur_lead,
                    "subtitles": subs_lead
                },
                "thinking": {
                    "text": sc["think_text"],
                    "audio_file": think_filename,
                    "duration_sec": dur_think,
                    "subtitles": subs_think
                },
                "response": {
                    "text": sc["resp_text"],
                    "audio_file": resp_filename,
                    "duration_sec": dur_resp,
                    "subtitles": subs_resp
                }
            }
            print(f"    Phase tracks: lead={dur_lead:.2f}s, think={dur_think:.2f}s, response={dur_resp:.2f}s")

        manifest_scenes.append(scene_entry)
        print(f"    Total Audio duration: {dur:.2f}s ({len(subtitles)} subtitle slices)")

    manifest_data = {
        "company": company,
        "role": role,
        "language": lang,
        "total_audio_duration_sec": round(total_audio_duration, 2),
        "scenes": manifest_scenes
    }

    manifest_path = os.path.join(args.outdir, "narration_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Narration synthesis complete! Saved to {manifest_path}")
    return manifest_data


def main():
    parser = argparse.ArgumentParser(description="Synthesize voice narration and subtitles for demo video.")
    parser.add_argument("--outdir", default="./output/narration", help="Output directory for audio and manifest")
    parser.add_argument("--company", default="", help="Company name")
    parser.add_argument("--role", default="", help="Agent role / display name")
    parser.add_argument("--lang", default="", help="Language code (e.g. ja-JP, en-US)")
    parser.add_argument("--project", default="", help="Google Cloud project ID for quota / billing")
    parser.add_argument("--prompts", nargs="+", help="Custom demo prompt strings")
    parser.add_argument("--mock", action="store_true", help="Simulate speech durations with silent audio (no Google Cloud TTS call)")
    args = parser.parse_args()

    synthesize_all(args)


if __name__ == "__main__":
    main()
