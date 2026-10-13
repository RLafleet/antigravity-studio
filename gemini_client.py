import json
import httpx
from typing import Optional, Dict, Any, List

ANTIGRAVITY_LINEUP = [
    {
        "id": "gemini-3.8-flash",
        "name": "Gemini 3.8 Flash",
        "default_thinking": "high",
        "tag": "Recommended",
        "category": "Antigravity Models"
    },
    {
        "id": "gemini-3.1-pro",
        "name": "Gemini 3.1 Pro",
        "default_thinking": "low",
        "tag": "Deep Reasoning",
        "category": "Antigravity Models"
    },
    {
        "id": "gemini-2.5-flash",
        "name": "Gemini 2.5 Flash",
        "default_thinking": "medium",
        "tag": "Fast",
        "category": "Gemini Production"
    },
    {
        "id": "gemini-2.5-pro",
        "name": "Gemini 2.5 Pro",
        "default_thinking": "high",
        "tag": "Advanced",
        "category": "Gemini Production"
    }
]


class GeminiClient:
    def __init__(self, api_key: str, model_name: str = "gemini-3.8-flash", thinking_level: str = "high"):
        self.api_key = api_key
        self.model_name = model_name
        self.thinking_level = thinking_level
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def get_models_catalog(self) -> Dict[str, Any]:
        """Fetches available models and constructs full lineup."""
        catalog: List[Dict[str, Any]] = list(ANTIGRAVITY_LINEUP)
        existing_ids = {m["id"] for m in catalog}

        if not self.api_key:
            return {
                "ok": True,
                "models": catalog,
                "thinking_levels": ["high", "medium", "low", "off"],
                "warning": "API ключ не настроен. Показан стандартный набор моделей."
            }

        url = f"{self.base_url}/models?key={self.api_key}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    raw_models = data.get("models", [])
                    discovered_models = []
                    for m in raw_models:
                        model_id = m.get("name", "").replace("models/", "")
                        if any(term in model_id for term in ["flash", "pro", "antigravity"]):
                            if model_id not in existing_ids:
                                display_name = m.get("displayName") or model_id.replace("-", " ").title()
                                is_pro = "pro" in model_id.lower()
                                discovered_models.append({
                                    "id": model_id,
                                    "name": display_name,
                                    "default_thinking": "high" if is_pro else "medium",
                                    "tag": "API",
                                    "category": "Discovered Models"
                                })
                                existing_ids.add(model_id)

                    return {
                        "ok": True,
                        "models": catalog + discovered_models,
                        "thinking_levels": ["high", "medium", "low", "off"]
                    }
                else:
                    return {
                        "ok": True,
                        "models": catalog,
                        "thinking_levels": ["high", "medium", "low", "off"],
                        "api_error": f"HTTP {res.status_code}: {res.text}"
                    }
        except Exception as e:
            return {
                "ok": True,
                "models": catalog,
                "thinking_levels": ["high", "medium", "low", "off"],
                "api_error": str(e)
            }

    async def test_connection(self) -> Dict[str, Any]:
        """Validates API Key connectivity."""
        return await self.get_models_catalog()

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        json_output: bool = False,
        temperature: float = 0.2,
        thinking_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calls Gemini API with fallback handling and thinking budget."""
        if not self.api_key:
            return {"ok": False, "error": "Gemini API key is not configured"}

        level = (thinking_level or self.thinking_level or "high").lower()

        models_to_try = [self.model_name]
        for fallback in ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash"]:
            if fallback not in models_to_try:
                models_to_try.append(fallback)

        last_error = ""
        for model in models_to_try:
            url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"

            payload: Dict[str, Any] = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt}]
                    }
                ],
                "generationConfig": {
                    "temperature": temperature,
                }
            }

            if system_instruction:
                payload["systemInstruction"] = {
                    "parts": [{"text": system_instruction}]
                }

            if json_output:
                payload["generationConfig"]["responseMimeType"] = "application/json"

            if level and level != "off":
                budget_map = {"high": 8192, "medium": 2048, "low": 512}
                payload["generationConfig"]["thinkingConfig"] = {
                    "thinkingBudget": budget_map.get(level, 2048)
                }

            try:
                async with httpx.AsyncClient(timeout=45.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if not candidates:
                            return {"ok": False, "error": "No generation candidates returned"}

                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        usage = data.get("usageMetadata", {})

                        result = {
                            "ok": True,
                            "text": text,
                            "model_used": model,
                            "usage": usage
                        }

                        if json_output:
                            try:
                                clean_text = text.strip()
                                if clean_text.startswith("```json"):
                                    clean_text = clean_text[7:]
                                if clean_text.endswith("```"):
                                    clean_text = clean_text[:-3]
                                result["json"] = json.loads(clean_text.strip())
                            except Exception as je:
                                result["json_error"] = str(je)

                        return result
                    else:
                        last_error = f"Model {model} returned HTTP {resp.status_code}: {resp.text}"
            except Exception as ex:
                last_error = f"Model {model} connection error: {str(ex)}"

        # Resilient Fallback 1: Local Antigravity CLI (agy.exe)
        try:
            agy_bin = r"C:\Users\decoriko\AppData\Local\agy\bin\agy.exe"
            import os
            import subprocess
            if os.path.exists(agy_bin):
                agy_model = f"gemini-3.8-flash-{level}" if level in ["high", "medium", "low"] else "gemini-3.8-flash-high"
                full_prompt = prompt
                if system_instruction:
                    full_prompt = f"System instructions:\n{system_instruction}\n\nUser request:\n{full_prompt}"
                if json_output:
                    full_prompt = f"{full_prompt}\n\nIMPORTANT: Output MUST be strictly valid JSON without markdown fences."

                p = subprocess.run([agy_bin, "--model", agy_model, "-p", full_prompt], capture_output=True, text=True, encoding="utf-8")
                if p.returncode == 0 and p.stdout.strip():
                    text = p.stdout.strip()
                    result = {
                        "ok": True,
                        "text": text,
                        "model_used": agy_model,
                        "engine": "agy_cli",
                        "usage": {"totalTokenCount": 0}
                    }
                    if json_output:
                        try:
                            clean_text = text.strip()
                            if clean_text.startswith("```json"):
                                clean_text = clean_text[7:]
                            if clean_text.startswith("```"):
                                clean_text = clean_text[3:]
                            if clean_text.endswith("```"):
                                clean_text = clean_text[:-3]
                            result["json"] = json.loads(clean_text.strip())
                        except Exception as je:
                            result["json_error"] = str(je)
                    return result
        except Exception as cli_err:
            last_error += f" | CLI fallback error: {str(cli_err)}"

        return {"ok": False, "error": last_error}

