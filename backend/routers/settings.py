"""Settings router — provider/model management."""

from fastapi import APIRouter, Depends
from backend.config import settings
from backend.schemas import ProviderCreate, ProviderOut, ModelOut

router = APIRouter()


def _mask_key(key: str) -> str:
    if len(key) <= 4:
        return "****"
    return "*" * (len(key) - 4) + key[-4:]


@router.get("/providers", response_model=list[ProviderOut])
def list_providers():
    result = []
    for p in settings.llm_providers:
        result.append(
            ProviderOut(
                id=p["id"],
                name=p.get("name", p["id"]),
                api_base=p.get("api_base", ""),
                api_key_masked=_mask_key(p.get("api_key", "")),
                models=p.get("models", []),
                enabled=p.get("enabled", True),
            )
        )
    return result


@router.post("/providers")
def add_provider(data: ProviderCreate):
    provider = data.model_dump()
    settings.add_provider(provider)
    return {"ok": True}


@router.put("/providers/{provider_id}")
def update_provider(provider_id: str, data: ProviderCreate):
    provider = data.model_dump()
    provider["id"] = provider_id
    settings.update_provider(provider_id, provider)
    return {"ok": True}


@router.delete("/providers/{provider_id}")
def delete_provider(provider_id: str):
    settings.remove_provider(provider_id)
    return {"ok": True}


@router.get("/models", response_model=list[ModelOut])
def list_models():
    return settings.get_all_models()


@router.get("/mineru-status")
def check_mineru():
    return {"token_configured": bool(settings.mineru_token)}


@router.post("/test-provider/{provider_id}")
def test_provider(provider_id: str):
    provider = settings.get_provider(provider_id)
    if not provider:
        return {"ok": False, "error": "Provider not found"}

    try:
        import openai

        client = openai.OpenAI(
            api_key=provider["api_key"],
            base_url=provider["api_base"],
        )
        models = provider.get("models", [])
        model_id = models[0]["id"] if models else "gpt-3.5-turbo"

        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=10,
        )
        return {"ok": True, "response": response.choices[0].message.content}
    except Exception as e:
        return {"ok": False, "error": str(e)}
