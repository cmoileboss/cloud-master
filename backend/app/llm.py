import json
import logging
import time

import openai
from openai import OpenAI
from pydantic import ValidationError

from app.config import BACKEND_DIR, Settings
from app.meetings import today_paris
from app.models import ConvocationChoice, Meeting

logger = logging.getLogger("ffk.llm")


class LLMError(Exception):
    """Échec d'un appel LLM, avec un message destiné à l'utilisateur et un code HTTP."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def to_llm_error(exc: openai.APIError) -> LLMError:
    """Traduit les erreurs du SDK en messages qui indiquent quel paramètre vérifier."""
    if isinstance(exc, (openai.AuthenticationError, openai.PermissionDeniedError)):
        return LLMError("Clé refusée par le fournisseur LLM : vérifiez LLM_API_KEY.")
    if isinstance(exc, openai.NotFoundError):
        return LLMError(
            "Modèle ou adresse introuvable chez le fournisseur : vérifiez LLM_MODEL et LLM_BASE_URL."
        )
    if isinstance(exc, openai.RateLimitError):
        return LLMError("Quota du fournisseur LLM atteint. Réessayez plus tard.", 429)
    if isinstance(exc, openai.APITimeoutError):
        return LLMError("Le fournisseur LLM n'a pas répondu à temps.", 504)
    if isinstance(exc, openai.APIConnectionError):
        return LLMError("Fournisseur LLM injoignable : vérifiez LLM_BASE_URL.")
    if isinstance(exc, openai.BadRequestError):
        return LLMError(
            "Requête refusée par le fournisseur LLM (le modèle accepte-t-il le mode JSON ?). "
            "Détail dans les logs du backend."
        )
    return LLMError("Erreur du fournisseur LLM. Détail dans les logs du backend.")


class LLMService:
    """Appels à un fournisseur compatible avec l'API OpenAI « chat/completions »."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def choose_meeting(self, request: str, meetings: list[Meeting]) -> ConvocationChoice:
        data = {
            "request": request,
            "meetings": [meeting.model_dump(mode="json") for meeting in meetings],
            "reference_date": today_paris().isoformat(),
        }
        return self.run("preparer-convocation", data, ConvocationChoice)

    def run(self, prompt_name: str, data: dict, output_type):
        """Envoie le prompt prompts/<prompt_name>.md et les données, puis valide la réponse JSON."""
        settings = self.settings
        api_key = settings.llm_api_key.get_secret_value()
        if not (settings.llm_base_url and settings.llm_model and api_key):
            raise LLMError("LLM non configuré : renseignez LLM_BASE_URL, LLM_MODEL et LLM_API_KEY.", 503)
        if settings.llm_base_url.rstrip("/").endswith("/chat/completions"):
            raise LLMError(
                "LLM_BASE_URL doit s'arrêter avant « /chat/completions » (ex. https://fournisseur/v1) : "
                "le SDK ajoute ce chemin lui-même.",
                503,
            )

        prompt = (BACKEND_DIR / "prompts" / f"{prompt_name}.md").read_text(encoding="utf-8")
        schema = json.dumps(output_type.model_json_schema(), ensure_ascii=False)
        prompt += f"\n\nRéponds uniquement avec un objet JSON conforme à ce schéma :\n{schema}"

        started = time.perf_counter()
        try:
            with OpenAI(base_url=settings.llm_base_url, api_key=api_key, timeout=60, max_retries=0) as client:
                response = client.chat.completions.create(
                    model=settings.llm_model,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": json.dumps(data, ensure_ascii=False)},
                    ],
                    response_format={"type": "json_object"},
                )
        except openai.APIError as exc:
            logger.error(
                "llm_failed prompt=%s model=%s error=%s detail=%s",
                prompt_name,
                settings.llm_model,
                type(exc).__name__,
                exc,
            )
            raise to_llm_error(exc) from exc

        content = response.choices[0].message.content or ""
        try:
            result = output_type.model_validate_json(content)
        except ValidationError as exc:
            logger.error(
                "llm_invalid_output prompt=%s model=%s output=%r",
                prompt_name,
                settings.llm_model,
                content[:300],
            )
            raise LLMError(
                "La réponse IA ne respecte pas le format attendu. Réessayez ou adaptez le prompt."
            ) from exc

        logger.info(
            "llm_ok prompt=%s model=%s duration=%.1fs",
            prompt_name,
            settings.llm_model,
            time.perf_counter() - started,
        )
        return result
