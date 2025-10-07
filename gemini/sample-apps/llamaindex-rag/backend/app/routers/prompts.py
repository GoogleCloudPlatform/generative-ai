from backend.app.dependencies import get_prompts
from backend.app.models import PromptUpdate
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()


@router.get("/get_all_prompts")
async def get_all_prompts(prompts=Depends(get_prompts)) -> dict:
    return prompts.to_dict()


@router.post("/update_prompt")
async def update_prompt(
    prompt_update: PromptUpdate, prompts=Depends(get_prompts)
) -> None:
    try:
        prompts.update(prompt_update.prompt_name, prompt_update.new_content)
        return {"message": f"Prompt {prompt_update.prompt_name} updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
