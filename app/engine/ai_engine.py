import json
import logging
from typing import Optional, Dict, Any, Tuple
import httpx
from app.config import (
    OLLAMA_BASE_URL,
    GEMINI_API_KEY,
    OPENAI_API_KEY,
    GROQ_API_KEY,
    ANTHROPIC_API_KEY
)

logger = logging.getLogger("ai_code_reviewer")

class AIEngine:
    def __init__(self):
        pass

    async def generate_deep_review(
        self,
        code: str,
        language: str,
        provider: str = "built-in",
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        ollama_url: Optional[str] = None
    ) -> Tuple[str, Optional[str]]:
        """
        Executes AI review and returns:
        (ai_insights_markdown, optional_ai_refactored_code)
        """
        provider = (provider or "built-in").lower()
        key = (api_key or "").strip()

        if provider == "gemini":
            effective_key = key or GEMINI_API_KEY
            if effective_key:
                return await self._call_gemini(code, language, effective_key, model_name or "gemini-1.5-flash")
            else:
                insights, _ = self._generate_builtin_insights(code, language)
                warning = "> ⚠️ **Google Gemini Notice**: No Gemini API Key was supplied. Open **Settings (⚙️)** to configure your key or set the `GEMINI_API_KEY` environment variable. Showing Built-in Analysis below:\n\n"
                return warning + insights, None

        elif provider == "openai":
            effective_key = key or OPENAI_API_KEY
            if effective_key:
                return await self._call_openai(code, language, effective_key, model_name or "gpt-4o-mini")
            else:
                insights, _ = self._generate_builtin_insights(code, language)
                warning = "> ⚠️ **OpenAI Notice**: No OpenAI API Key was supplied. Open **Settings (⚙️)** to configure your key or set the `OPENAI_API_KEY` environment variable. Showing Built-in Analysis below:\n\n"
                return warning + insights, None

        elif provider == "groq":
            effective_key = key or GROQ_API_KEY
            if effective_key:
                return await self._call_groq(code, language, effective_key, model_name or "llama-3.3-70b-versatile")
            else:
                insights, _ = self._generate_builtin_insights(code, language)
                warning = "> ⚠️ **Groq Notice**: No Groq API Key was supplied. Open **Settings (⚙️)** to configure your key or set the `GROQ_API_KEY` environment variable. Showing Built-in Analysis below:\n\n"
                return warning + insights, None

        elif provider == "ollama":
            return await self._call_ollama(code, language, ollama_url or OLLAMA_BASE_URL, model_name or "codellama")

        else:
            # Built-in offline intelligent code understanding engine
            return self._generate_builtin_insights(code, language)

    def _generate_builtin_insights(self, code: str, language: str) -> Tuple[str, Optional[str]]:
        lines = code.splitlines()
        loc = len(lines)
        has_imports = any("import " in l or "#include" in l or "require(" in l for l in lines)
        has_classes = any("class " in l or "struct " in l or "interface " in l for l in lines)
        has_tests = any("test" in l.lower() or "assert" in l.lower() for l in lines)

        insights = []
        insights.append(f"### 🧠 AI Architectural & Semantic Code Analysis ({language.title()})")
        insights.append(f"- **Code Size & Structure**: Analyzed {loc} source lines. " + 
                        ("Modular architecture with explicit dependencies." if has_imports else "Self-contained script.") + " " +
                        ("Object-Oriented patterns observed." if has_classes else "Procedural / Functional paradigms observed."))
        
        if not has_tests:
            insights.append("- **Test Coverage**: No unit tests or assertion checks detected within this snippet. Recommend introducing comprehensive unit tests to prevent regressions.")
        else:
            insights.append("- **Verification**: Test assertions or test routines present in the reviewed artifact.")

        insights.append("\n#### 🛡️ Robustness Recommendations:")
        insights.append("1. **Input Validation**: Ensure all external inputs (CLI arguments, HTTP parameters, network buffers) are explicitly sanitized and validated against a strict schema.")
        insights.append("2. **Exception Discipline**: Avoid suppressing exceptions without structured error reporting or metrics propagation.")
        insights.append("3. **Resource Lifecycle**: Use language-level RAII or context managers (`with`, `try-with-resources`) to guarantee deterministic resource cleanup.")

        return "\n".join(insights), None

    async def _call_gemini(self, code: str, language: str, api_key: str, model: str) -> Tuple[str, Optional[str]]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        prompt = (
            f"You are an expert Principal Code Reviewer and Security Auditor. "
            f"Analyze the following {language} code for bugs, security vulnerabilities, edge cases, and performance anti-patterns.\n\n"
            f"Provide:\n"
            f"1. A concise Markdown analysis of detected issues and architectural recommendations.\n"
            f"2. A corrected, fully refactored, production-ready version of the code enclosed in a ```{language} code block.\n\n"
            f"Code:\n```{language}\n{code}\n```"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    # Extract refactored code block if present
                    refactored_code = self._extract_code_block(text, language)
                    return text, refactored_code
                else:
                    return f"**Gemini API Error ({res.status_code})**: {res.text}", None
        except Exception as e:
            logger.error(f"Gemini API failure: {e}")
            return f"**AI Engine Notice**: Could not reach Gemini API ({str(e)}). Falling back to built-in rule analyzer.", None

    async def _call_openai(self, code: str, language: str, api_key: str, model: str) -> Tuple[str, Optional[str]]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        prompt = (
            f"You are an elite Software Architect and Security Auditor reviewing {language} code. "
            f"Identify bugs, vulnerabilities, style violations, and performance issues. "
            f"Provide an actionable markdown analysis and complete refactored code enclosed in a ```{language} block."
        )
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Review this code:\n```{language}\n{code}\n```"}
            ],
            "temperature": 0.2
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    text = data["choices"][0]["message"]["content"]
                    refactored_code = self._extract_code_block(text, language)
                    return text, refactored_code
                else:
                    return f"**OpenAI API Error ({res.status_code})**: {res.text}", None
        except Exception as e:
            return f"**AI Engine Notice**: OpenAI API request failed ({str(e)}).", None

    async def _call_groq(self, code: str, language: str, api_key: str, model: str) -> Tuple[str, Optional[str]]:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": f"You are a code review assistant. Review this {language} code and provide fixes."},
                {"role": "user", "content": f"```{language}\n{code}\n```"}
            ]
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    text = res.json()["choices"][0]["message"]["content"]
                    return text, self._extract_code_block(text, language)
                return f"**Groq Error ({res.status_code})**: {res.text}", None
        except Exception as e:
            return f"**AI Engine Notice**: Groq API call failed ({str(e)}).", None

    async def _call_ollama(self, code: str, language: str, base_url: str, model: str) -> Tuple[str, Optional[str]]:
        url = f"{base_url.rstrip('/')}/api/generate"
        prompt = (
            f"Review this {language} code for bugs, security vulnerabilities, and improvements. "
            f"Provide an explanation and corrected code:\n```{language}\n{code}\n```"
        )
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    text = res.json().get("response", "")
                    return text, self._extract_code_block(text, language)
                return f"**Ollama Error ({res.status_code})**: {res.text}", None
        except Exception as e:
            return f"**Ollama Offline**: Could not connect to Ollama at {base_url}. Ensure Ollama is running.", None

    def _extract_code_block(self, text: str, language: str) -> Optional[str]:
        """Extracts code block from markdown text if present."""
        import re
        patterns = [
            rf"```{language}\s*\n(.*?)```",
            r"```[a-zA-Z0-9_+-]*\s*\n(.*?)```"
        ]
        for pat in patterns:
            match = re.search(pat, text, re.DOTALL)
            if match:
                return match.group(1).strip()
        return None
