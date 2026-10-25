"""AI engine gateway routes (OpenAI / Gemini)."""

from typing import Literal, Optional
from datetime import datetime

import httpx
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from api.models.database import get_db, Patient
from api.services.patient_assistant import ASSISTANT_SYSTEM_PROMPT, build_patient_context, build_user_prompt
import api.services.gemini_service as gemini_service
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

class ConversationTurn(BaseModel):
    role: Literal['user', 'assistant']
    content: str = Field(..., min_length=1, max_length=4000)


class PatientAssistantRequest(BaseModel):
    patient_id: str
    message: str = Field(..., min_length=1, max_length=2000)
    conversation: list[ConversationTurn] = Field(default_factory=list, max_length=12)


class PatientAssistantResponse(BaseModel):
    answer: str
    patient_id: str
    data_as_of: datetime
    data_freshness_seconds: int
    latest_status: str
    is_simulated_data: bool
    model: str
    disclaimer: str


@router.get("/providers")
async def ai_providers_status():
    """Get availability of configured AI providers."""
    settings = get_settings()
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

    try:
        content = await gemini_service.generate_text(
            payload.system_prompt or '', payload.prompt,
            max_output_tokens=payload.max_tokens,
        )
    except gemini_service.GeminiNotConfiguredError:
        raise HTTPException(status_code=400, detail="GEMINI_API_KEY is not configured")
    except gemini_service.GeminiUpstreamError:
        raise HTTPException(status_code=502, detail="Gemini upstream request failed.")

    return ChatResponse(
        provider="gemini",
        model=get_settings().GEMINI_MODEL,
        content=content,
    )

@router.post('/patient-assistant', response_model=PatientAssistantResponse)
async def patient_assistant(payload: PatientAssistantRequest, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if patient is None:
        raise HTTPException(404, detail={'error': 'patient_not_found', 'message': 'Patient not found'})
    context = build_patient_context(db, patient)
    if context is None:
        raise HTTPException(409, detail={'error': 'no_vitals', 'message': 'No vital readings are available.'})
    try:
        answer = await gemini_service.generate_text(
            ASSISTANT_SYSTEM_PROMPT,
            build_user_prompt(context, payload.message, [turn.model_dump() for turn in payload.conversation]),
        )
    except gemini_service.GeminiNotConfiguredError:
        raise HTTPException(503, detail={'error': 'gemini_not_configured', 'message': 'Gemini is not configured on the backend.'})
    except gemini_service.GeminiUpstreamError:
        raise HTTPException(502, detail={'error': 'gemini_upstream_error', 'message': 'Gemini upstream request failed.'})
    return PatientAssistantResponse(
        answer=answer,
        patient_id=payload.patient_id,
        data_as_of=context['data_as_of'],
        data_freshness_seconds=context['data_freshness_seconds'],
        latest_status=context['latest']['status'],
        is_simulated_data=context['is_simulated_data'],
        model=get_settings().GEMINI_MODEL,
        disclaimer='Decision-support information only. This is not a diagnosis or a replacement for clinical judgement or emergency care.',
    )
