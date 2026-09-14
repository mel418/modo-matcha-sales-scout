from strands import Agent
from strands.models import BedrockModel

for model_id in ["us.anthropic.claude-sonnet-5", "us.anthropic.claude-opus-5"]:
    print(f"\n--- {model_id} ---")
    try:
        agent = Agent(
            model=BedrockModel(model_id=model_id, region_name="us-east-1"),
            system_prompt="Reply in exactly five words.",
        )
        print(agent("Say hello to Modo Matcha."))
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")