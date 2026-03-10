"""Video UGC (User-Generated Content) Engine pipeline.

Most complex pipeline. Steps:
  1. generate_script     — OpenAI: UGC script structure (hook, body, CTA) per
                           creative angle.
  2. generate_voiceover  — ElevenLabs TTS from script, multiple voice variations.
  3. generate_video      — HeyGen avatar video OR FAL/Kling background video
                           depending on style config.
  4. composite           — ffmpeg: combine voiceover + video + captions (SRT) +
                           brand elements + CTA cards.

Fan-out by: hooks x avatars/voices x CTAs.
Outputs: MP4 files, script text files, SRT caption files.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from app.integrations.elevenlabs_client import ElevenLabsClient
from app.integrations.fal_client import FalClient
from app.integrations.heygen_client import HeyGenClient
from app.integrations.openai_client import OpenAIClient

# ---------------------------------------------------------------------------
# OpenAI JSON schema for UGC script generation
# ---------------------------------------------------------------------------

SCRIPT_SCHEMA: dict[str, Any] = {
    "name": "ugc_scripts",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "scripts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "angle": {
                            "type": "string",
                            "description": "Creative angle this script targets",
                        },
                        "hook": {
                            "type": "string",
                            "description": (
                                "Opening hook — attention-grabbing first 3 seconds"
                            ),
                        },
                        "body": {
                            "type": "string",
                            "description": (
                                "Main script body — product demo, benefits, story"
                            ),
                        },
                        "cta": {
                            "type": "string",
                            "description": (
                                "Call-to-action closing — clear next step for viewer"
                            ),
                        },
                        "full_text": {
                            "type": "string",
                            "description": (
                                "Complete script as continuous narration "
                                "(hook + body + cta combined)"
                            ),
                        },
                        "estimated_duration_seconds": {
                            "type": "integer",
                            "description": "Estimated read time in seconds",
                        },
                    },
                    "required": [
                        "angle",
                        "hook",
                        "body",
                        "cta",
                        "full_text",
                        "estimated_duration_seconds",
                    ],
                    "additionalProperties": False,
                },
                "description": "One script per creative angle",
            },
        },
        "required": ["scripts"],
        "additionalProperties": False,
    },
}

DEFAULT_ANGLES = [
    "problem_solution",
    "unboxing_reaction",
    "day_in_my_life",
    "before_after",
    "testimonial_story",
]

DEFAULT_VOICES = [
    {"voice_id": "21m00Tcm4TlvDq8ikWAM", "label": "rachel"},
    {"voice_id": "EXAVITQu4vr4xnSDxMaL", "label": "bella"},
]

DEFAULT_AVATARS = [
    {"avatar_id": "josh_lite3_20230714", "label": "josh"},
]


# ---------------------------------------------------------------------------
# Step 1: generate_script
# ---------------------------------------------------------------------------

async def generate_script(prev_output: dict, config: dict) -> dict[str, Any]:
    """Generate UGC script structures (hook, body, CTA) per creative angle.

    Fan-out: produces one script per angle.
    """
    brand = config.get("brand", {})
    product = config.get("product", {})
    angles = config.get("angles", DEFAULT_ANGLES)
    tone = config.get("tone", "authentic, conversational, relatable")
    platform = config.get("platform", "TikTok / Instagram Reels")
    job_id = config.get("job_id", "unknown")

    client = OpenAIClient()

    system_prompt = (
        "You are an expert UGC (User-Generated Content) scriptwriter for social "
        "media ads. You write scripts that feel organic, personal, and native to "
        f"the platform ({platform}). Each script has three parts:\n"
        "- hook: attention-grabbing opening (first 3 seconds)\n"
        "- body: product showcase, benefits, personal story\n"
        "- cta: clear call-to-action\n\n"
        f"Brand voice: {brand.get('voice', 'Professional and engaging')}.\n"
        f"Tone: {tone}."
    )

    angles_text = "\n".join(f"- {a}" for a in angles)
    user_prompt = (
        f"Generate one UGC video script for EACH of these creative angles:\n"
        f"{angles_text}\n\n"
        f"Product: {product.get('name', 'Unknown Product')}\n"
        f"Description: {product.get('description', '')}\n"
        f"Price: ${product.get('price', 'N/A')}\n"
        f"Key benefits: {product.get('benefits', 'N/A')}\n\n"
        f"Target platform: {platform}\n"
        f"Each script should be 15-45 seconds when read aloud.\n"
        f"Make them feel like real people talking, not ads."
    )

    result = await client.structured_output(
        system=system_prompt,
        user=user_prompt,
        json_schema=SCRIPT_SCHEMA,
        temperature=0.7,
        max_tokens=4096,
    )

    scripts = result["scripts"]

    # Write script text files
    output_dir = Path("outputs") / str(job_id) / "video_ugc" / "scripts"
    output_dir.mkdir(parents=True, exist_ok=True)

    script_files: list[str] = []
    for script in scripts:
        slug = script["angle"].replace(" ", "_").lower()
        path = output_dir / f"script_{slug}.txt"
        path.write_text(
            f"[HOOK]\n{script['hook']}\n\n"
            f"[BODY]\n{script['body']}\n\n"
            f"[CTA]\n{script['cta']}\n\n"
            f"---\n{script['full_text']}"
        )
        script_files.append(str(path))

    scripts_json = output_dir / "all_scripts.json"
    scripts_json.write_text(json.dumps(scripts, indent=2))

    return {
        "scripts": scripts,
        "script_files": script_files,
        "scripts_json_path": str(scripts_json),
        "angle_count": len(scripts),
    }


# ---------------------------------------------------------------------------
# Step 2: generate_voiceover
# ---------------------------------------------------------------------------

async def generate_voiceover(prev_output: dict, config: dict) -> dict[str, Any]:
    """Generate ElevenLabs TTS voiceovers from scripts.

    Fan-out: scripts x voice variations.
    """
    scripts = prev_output["scripts"]
    voices = config.get("voices", DEFAULT_VOICES)
    job_id = config.get("job_id", "unknown")

    client = ElevenLabsClient()

    output_dir = Path("outputs") / str(job_id) / "video_ugc" / "voiceovers"
    output_dir.mkdir(parents=True, exist_ok=True)

    voiceovers: list[dict[str, Any]] = []

    for script in scripts:
        angle_slug = script["angle"].replace(" ", "_").lower()

        for voice in voices:
            voice_id = voice["voice_id"]
            voice_label = voice.get("label", voice_id[:8])

            audio_bytes = await client.text_to_speech(
                script["full_text"],
                voice_id=voice_id,
            )

            filename = f"vo_{angle_slug}_{voice_label}.mp3"
            dest = output_dir / filename
            dest.write_bytes(audio_bytes)

            voiceovers.append({
                "angle": script["angle"],
                "voice_id": voice_id,
                "voice_label": voice_label,
                "file_path": str(dest),
                "script_text": script["full_text"],
                "hook": script["hook"],
                "body": script["body"],
                "cta": script["cta"],
                "estimated_duration_seconds": script["estimated_duration_seconds"],
            })

    return {
        "voiceovers": voiceovers,
        "total_voiceovers": len(voiceovers),
        "output_dir": str(output_dir),
    }


# ---------------------------------------------------------------------------
# Step 3: generate_video
# ---------------------------------------------------------------------------

async def generate_video(prev_output: dict, config: dict) -> dict[str, Any]:
    """Generate video assets — HeyGen avatar OR FAL/Kling background video.

    Style is determined by config['video_style']:
      - "avatar"     → HeyGen talking-head avatar video
      - "background" → FAL/Kling AI-generated background video clip

    Fan-out: voiceovers x avatars (avatar mode) or voiceovers x 1 (background).
    """
    voiceovers = prev_output["voiceovers"]
    video_style = config.get("video_style", "avatar")
    avatars = config.get("avatars", DEFAULT_AVATARS)
    job_id = config.get("job_id", "unknown")
    product = config.get("product", {})

    output_dir = Path("outputs") / str(job_id) / "video_ugc" / "videos"
    output_dir.mkdir(parents=True, exist_ok=True)

    videos: list[dict[str, Any]] = []

    if video_style == "avatar":
        heygen = HeyGenClient()

        for vo in voiceovers:
            angle_slug = vo["angle"].replace(" ", "_").lower()

            for avatar in avatars:
                avatar_id = avatar["avatar_id"]
                avatar_label = avatar.get("label", avatar_id[:8])

                video_id = await heygen.create_video(
                    script=vo["script_text"],
                    avatar_id=avatar_id,
                    voice_id=vo.get("voice_id"),
                )

                result = await heygen.poll_video(video_id)
                video_url = result.get("video_url", "")

                filename = (
                    f"vid_{angle_slug}_{vo['voice_label']}"
                    f"_{avatar_label}.mp4"
                )
                video_path = await heygen.download_video(video_url, filename)
                # Move to our output dir
                final_path = output_dir / filename
                if video_path != final_path:
                    final_path.write_bytes(video_path.read_bytes())

                videos.append({
                    "angle": vo["angle"],
                    "voice_label": vo["voice_label"],
                    "avatar_label": avatar_label,
                    "video_style": "avatar",
                    "file_path": str(final_path),
                    "voiceover_path": vo["file_path"],
                    "script_text": vo["script_text"],
                    "hook": vo["hook"],
                    "body": vo["body"],
                    "cta": vo["cta"],
                    "estimated_duration_seconds": vo["estimated_duration_seconds"],
                })
    else:
        # Background video mode — generate AI video clips via FAL/Kling
        fal = FalClient()

        for vo in voiceovers:
            angle_slug = vo["angle"].replace(" ", "_").lower()
            product_name = product.get("name", "product")

            video_prompt = (
                f"Cinematic product shot of {product_name}. "
                f"Style: UGC social media ad. "
                f"Context: {vo['angle'].replace('_', ' ')}. "
                f"Clean background, soft lighting, lifestyle aesthetic."
            )

            result = await fal.generate_video(
                video_prompt,
                duration=str(min(vo["estimated_duration_seconds"], 10)),
                aspect_ratio="9:16",
            )

            video_url = result.get("video", {}).get("url", "")
            if not video_url and result.get("data"):
                video_url = result["data"].get("url", "")

            filename = f"vid_{angle_slug}_{vo['voice_label']}_bg.mp4"
            video_path = await fal.download_file(video_url, filename)
            final_path = output_dir / filename
            if video_path != final_path:
                final_path.write_bytes(video_path.read_bytes())

            videos.append({
                "angle": vo["angle"],
                "voice_label": vo["voice_label"],
                "avatar_label": None,
                "video_style": "background",
                "file_path": str(final_path),
                "voiceover_path": vo["file_path"],
                "script_text": vo["script_text"],
                "hook": vo["hook"],
                "body": vo["body"],
                "cta": vo["cta"],
                "estimated_duration_seconds": vo["estimated_duration_seconds"],
            })

    return {
        "videos": videos,
        "total_videos": len(videos),
        "video_style": video_style,
        "output_dir": str(output_dir),
    }


# ---------------------------------------------------------------------------
# Step 4: composite
# ---------------------------------------------------------------------------

def _generate_srt(script: dict[str, Any]) -> str:
    """Generate an SRT caption file from a script's hook/body/cta structure.

    Estimates timing based on word count (~150 words per minute).
    """
    segments = [
        ("hook", script["hook"]),
        ("body", script["body"]),
        ("cta", script["cta"]),
    ]

    srt_lines: list[str] = []
    current_time = 0.0
    idx = 1

    for _label, text in segments:
        # Split into subtitle chunks of ~10 words each
        words = text.split()
        chunk_size = 10
        for i in range(0, len(words), chunk_size):
            chunk_words = words[i : i + chunk_size]
            chunk_text = " ".join(chunk_words)
            # ~150 WPM = 2.5 words/sec
            duration = len(chunk_words) / 2.5

            start = current_time
            end = current_time + duration

            start_ts = _format_srt_time(start)
            end_ts = _format_srt_time(end)

            srt_lines.append(str(idx))
            srt_lines.append(f"{start_ts} --> {end_ts}")
            srt_lines.append(chunk_text)
            srt_lines.append("")

            current_time = end
            idx += 1

    return "\n".join(srt_lines)


def _format_srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp: HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _build_ffmpeg_command(
    video_path: str,
    audio_path: str,
    srt_path: str,
    output_path: str,
    cta_text: str,
    brand_name: str,
) -> list[str]:
    """Build ffmpeg command for compositing video + audio + captions + CTA card.

    Overlays:
      - Audio track from voiceover
      - Burned-in SRT captions (white text, dark outline)
      - Brand watermark (top-left text)
      - CTA card (bottom overlay in last 3 seconds)
    """
    # Escape special characters for ffmpeg drawtext
    cta_escaped = cta_text.replace("'", "'\\''").replace(":", "\\:")
    brand_escaped = brand_name.replace("'", "'\\''").replace(":", "\\:")

    filter_parts = [
        # Burn in subtitles from SRT file
        f"subtitles='{srt_path}':force_style="
        "'FontName=Arial,FontSize=22,PrimaryColour=&HFFFFFF&,"
        "OutlineColour=&H000000&,Outline=2,Shadow=1,MarginV=40'",
        # Brand watermark — top-left
        f"drawtext=text='{brand_escaped}':"
        "fontcolor=white:fontsize=18:x=20:y=20:"
        "shadowcolor=black:shadowx=1:shadowy=1",
        # CTA card — bottom banner in last 3 seconds
        f"drawtext=text='{cta_escaped}':"
        "fontcolor=white:fontsize=28:x=(w-text_w)/2:y=h-80:"
        "shadowcolor=black:shadowx=2:shadowy=2:"
        "enable='gte(t,duration-3)'",
    ]

    vf = ",".join(filter_parts)

    return [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-filter_complex",
        f"[0:v]{vf}[vout]",
        "-map", "[vout]",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "fast",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        output_path,
    ]


async def composite(prev_output: dict, config: dict) -> dict[str, Any]:
    """Combine voiceover + video + captions (SRT) + brand elements + CTA cards.

    Uses ffmpeg for video composition. Generates SRT caption files from scripts.
    Produces final MP4 files ready for ad platform upload.
    """
    videos = prev_output["videos"]
    brand = config.get("brand", {})
    brand_name = brand.get("name", "Brand")
    job_id = config.get("job_id", "unknown")

    output_dir = Path("outputs") / str(job_id) / "video_ugc" / "final"
    srt_dir = Path("outputs") / str(job_id) / "video_ugc" / "captions"
    output_dir.mkdir(parents=True, exist_ok=True)
    srt_dir.mkdir(parents=True, exist_ok=True)

    composited: list[dict[str, Any]] = []

    for video in videos:
        angle_slug = video["angle"].replace(" ", "_").lower()
        voice_label = video["voice_label"]
        avatar_label = video.get("avatar_label") or "bg"
        variant_slug = f"{angle_slug}_{voice_label}_{avatar_label}"

        # Generate SRT caption file
        srt_content = _generate_srt(video)
        srt_path = srt_dir / f"captions_{variant_slug}.srt"
        srt_path.write_text(srt_content)

        # Build output path
        final_filename = f"ugc_final_{variant_slug}.mp4"
        final_path = output_dir / final_filename

        # Compose with ffmpeg
        cmd = _build_ffmpeg_command(
            video_path=video["file_path"],
            audio_path=video["voiceover_path"],
            srt_path=str(srt_path),
            output_path=str(final_path),
            cta_text=video["cta"],
            brand_name=brand_name,
        )

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(
                f"ffmpeg failed for {variant_slug}: "
                f"{stderr.decode(errors='replace')[:500]}"
            )

        composited.append({
            "angle": video["angle"],
            "voice_label": voice_label,
            "avatar_label": video.get("avatar_label"),
            "video_style": video["video_style"],
            "final_mp4_path": str(final_path),
            "srt_path": str(srt_path),
            "script_text": video["script_text"],
            "hook": video["hook"],
            "cta": video["cta"],
        })

    # Write manifest
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(composited, indent=2))

    # Create Output records for gallery and file serving
    session = config.get("_session")
    if session is not None:
        from uuid import UUID
        from app.models.output import Output

        _job_id = UUID(str(job_id))

        for video_entry in composited:
            video_output = Output(
                job_id=_job_id,
                pipeline_name="video_ugc",
                output_type="video",
                file_path=video_entry["final_mp4_path"],
                metadata_={
                    "angle": video_entry["angle"],
                    "voice_label": video_entry["voice_label"],
                    "avatar_label": video_entry.get("avatar_label"),
                    "video_style": video_entry["video_style"],
                    "hook": video_entry["hook"],
                    "cta": video_entry["cta"],
                },
            )
            session.add(video_output)

        manifest_output = Output(
            job_id=_job_id,
            pipeline_name="video_ugc",
            output_type="json",
            file_path=str(manifest_path),
            metadata_={
                "format": "manifest",
                "total_videos": len(composited),
            },
        )
        session.add(manifest_output)
        await session.flush()

    return {
        "composited_videos": composited,
        "total_final_videos": len(composited),
        "manifest_path": str(manifest_path),
        "output_dir": str(output_dir),
        "srt_dir": str(srt_dir),
    }


# ---------------------------------------------------------------------------
# Pipeline registration
# ---------------------------------------------------------------------------

from app.engine.pipeline_engine import register_pipeline  # noqa: E402

register_pipeline(
    "video_ugc",
    [
        ("generate_script", generate_script),
        ("generate_voiceover", generate_voiceover),
        ("generate_video", generate_video),
        ("composite", composite),
    ],
)
