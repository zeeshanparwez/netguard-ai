"""
AI router — handles the GPT-4o-mini chat endpoint.
Keeps all HTTP/FastAPI concerns here; actual LLM logic lives in ai_service.
"""

from fastapi import APIRouter, HTTPException

from backend.schemas.requests import ChatRequest
from backend.services import ai_service

router = APIRouter()


@router.post("/api/ai/chat")
async def ai_chat(body: ChatRequest):
    """
    LLM-powered Q&A grounded in live network data.

    Builds a system prompt that includes the current network snapshot (risk
    distribution, top at-risk devices, KPI correlations) then forwards the
    full conversation history to Azure OpenAI GPT-4o-mini.

    Multi-turn: pass the full conversation history in `messages` each call.
    """
    context = ai_service.build_network_context()
    system_prompt = ai_service.SYSTEM_PROMPT_TEMPLATE.format(network_context=context)

    messages = [{"role": "system", "content": system_prompt}]
    messages += [{"role": m.role, "content": m.content} for m in body.messages]

    try:
        reply = ai_service.chat(messages)
        return {"reply": reply}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI service unavailable: {exc}")
