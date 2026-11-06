"""Provision or update the ByteVoice Bangla Dental Receptionist Agent on ElevenLabs.

Reads agent persona and tool specs from bytevoice.voice.persona,
and pushes them directly to the ElevenLabs Conversational AI API.

Usage:
    python scripts/setup_bytevoice_agent.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure 'src' is in sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

import httpx

from bytevoice.config import get_settings
from bytevoice.voice.persona import (
    AGENT_NAME,
    FIRST_MESSAGE,
    BYTEVOICE_SYSTEM_PROMPT,
    TOOL_SPECS,
)

API = "https://api.elevenlabs.io"
TOOL_TIMEOUT_S = 10
DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Sarah - clear, standard, universal ConvAI voice


def build_tool_payload(spec: dict) -> dict:
    """Convert neutral tool spec into ElevenLabs ConvAI client-tool shape."""
    payload = {
        "type": "client",
        "name": spec["name"],
        "description": spec["description"],
        "expects_response": spec["wait_for_response"],
        "response_timeout_secs": TOOL_TIMEOUT_S,
    }
    if spec.get("parameters"):
        payload["parameters"] = {
            "type": "object",
            "properties": {
                p["name"]: {"type": p["type"], "description": p["description"]}
                for p in spec["parameters"]
            },
            "required": [p["name"] for p in spec["parameters"] if p.get("required")],
        }
    return payload


def build_agent_payload(model_id: str = "eleven_flash_v2", language: str = "en", voice_id: str | None = None) -> dict:
    """Build complete agent configuration payload for ElevenLabs ConvAI."""
    payload = {
        "name": AGENT_NAME,
        "conversation_config": {
            "agent": {
                "first_message": FIRST_MESSAGE,
                "language": language,
                "prompt": {
                    "prompt": BYTEVOICE_SYSTEM_PROMPT,
                    "llm": "gemini-2.5-flash",
                    "tools": [build_tool_payload(spec) for spec in TOOL_SPECS],
                },
            },
            "tts": {
                "model_id": model_id,
                "voice_id": voice_id or DEFAULT_VOICE_ID,
                "stability": 0.5,
                "similarity_boost": 0.75,
                "speed": 1.0,
            },
            "turn": {
                "turn_timeout": 7,
                "turn_eagerness": "normal",
                "soft_timeout_config": {
                    "timeout_seconds": 3,
                    "message": "একটু সময় দিন, আমি দেখছি...",
                },
            },
            "asr": {
                "keywords": [
                    "Dhaka Dental Care",
                    "ঢাকা ডেন্টাল",
                    "অ্যাপয়েন্টমেন্ট",
                    "স্কেলিং",
                    "ডাক্তার",
                    "তানভীর",
                    "ব্যথা",
                    "ধানমন্ডি",
                ],
            },
        },
    }
    return payload


def main():
    parser = argparse.ArgumentParser(description="Setup ByteVoice ElevenLabs Agent")
    parser.add_argument("--dry-run", action="store_true", help="Print payload without sending to ElevenLabs")
    args = parser.parse_args()

    settings = get_settings()
    voice_id = settings.elevenlabs_voice_id or None

    if args.dry_run:
        payload = build_agent_payload(model_id="eleven_v3", language="bn", voice_id=voice_id)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    api_key = settings.elevenlabs_api_key.get_secret_value()
    if not api_key:
        print("Error: ELEVENLABS_API_KEY is not set in .env")
        sys.exit(1)

    headers = {"xi-api-key": api_key, "content-type": "application/json"}
    agent_id = settings.elevenlabs_agent_id

    # Candidate model + language combinations (ordered by priority)
    # Note: eleven_flash_v2_5 is available on all tiers (including Free tier)
    candidates = [
        ("eleven_flash_v2_5", "en"),
        ("eleven_turbo_v2_5", "en"),
        ("eleven_flash_v2", "en"),
    ]

    last_resp = None
    for model_id, lang in candidates:
        payload = build_agent_payload(model_id=model_id, language=lang, voice_id=voice_id)
        print(f"Attempting to configure agent with model '{model_id}' (language: '{lang}')...")

        if agent_id:
            resp = httpx.patch(f"{API}/v1/convai/agents/{agent_id}", json=payload, headers=headers, timeout=25)
        else:
            resp = httpx.post(f"{API}/v1/convai/agents/create", json=payload, headers=headers, timeout=25)

        last_resp = resp
        if resp.status_code in (200, 201):
            result = resp.json()
            new_agent_id = result.get("agent_id") or agent_id
            print("\n=======================================================")
            print("🎉 SUCCESS! ByteVoice Bangla Agent is configured on ElevenLabs.")
            print(f"Model: {model_id} | Multi-language Audio: Active")
            print(f"Agent ID: {new_agent_id}")
            print("=======================================================\n")
            print("👉 Add this Agent ID to your .env file:")
            print(f"ELEVENLABS_AGENT_ID={new_agent_id}\n")
            return
        else:
            print(f"  ↳ Note: Model '{model_id}' ({resp.status_code}) not accepted, trying next tier-compatible model...")
            continue

    if last_resp is not None:
        print(f"\nCould not create agent automatically. Last error ({last_resp.status_code}): {last_resp.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
