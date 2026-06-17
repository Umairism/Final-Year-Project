"""AI engine gateway routes (OpenAI / Gemini)."""

from typing import Literal, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.config import get_settings

router = APIRouter()
settings = get_settings()


class ChatRequest(BaseModel):
    provider: Literal["openai", "gemini"] = Field(..., description="AI provider name")
    prompt: str = Field(..., min_length=1, description="User prompt")
    system_prompt: Optional[str] = Field(default="You are a helpful health assistant.")
    max_tokens: int = Field(default=300, ge=64, le=2048)


class ChatResponse(BaseModel):
    provider: str
    model: str
    content: str


@router.get("/providers")
async def ai_providers_status():
    """Get availability of configured AI providers."""
    return {
        "openai": {
            "configured": bool(settings.OPENAI_API_KEY),
            "model": settings.OPENAI_MODEL,
        },
        "gemini": {
            "configured": bool(settings.GEMINI_API_KEY),
            "model": settings.GEMINI_MODEL,
        },
    }


@router.post("/chat", response_model=ChatResponse)
async def ai_chat(payload: ChatRequest):
    """Unified AI chat endpoint for OpenAI and Gemini."""
    if payload.provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise HTTPException(status_code=400, detail="OPENAI_API_KEY is not configured")

        body = {
            "model": settings.OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": payload.system_prompt or ""},
                {"role": "user", "content": payload.prompt},
            ],
            "max_tokens": payload.max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                json=body,
                headers=headers,
            )

        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"OpenAI error: {response.text}")

        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        return ChatResponse(
            provider="openai",
            model=settings.OPENAI_MODEL,
            content=content,
        )

    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=400, detail="GEMINI_API_KEY is not configured")

    gemini_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
    )

    gemini_body = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"{payload.system_prompt or ''}\n\nUser: {payload.prompt}",
                    }
                ]
            }
        ]
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(gemini_url, json=gemini_body)

    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Gemini error: {response.text}")

    data = response.json()
    content = (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "")
    )

    return ChatResponse(
        provider="gemini",
        model=settings.GEMINI_MODEL,
        content=content,
    )
