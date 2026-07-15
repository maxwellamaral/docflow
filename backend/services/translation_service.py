"""Tradução de conteúdo HTML via Ollama com modelo translategemma:4b."""
import httpx
from bs4 import BeautifulSoup

from backend.core.config import settings

# Tags cujo conteúdo textual será traduzido
_TRANSLATABLE_TAGS: frozenset[str] = frozenset(
    {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "th", "caption"}
)


class TranslationError(Exception):
    """Erro durante a tradução via Ollama."""


class TranslationService:
    """Cliente para o serviço Ollama de tradução.

    Args:
        base_url: URL base do servidor Ollama.
        model: Modelo de tradução (ex: 'translategemma:4b').
        target_language: Idioma de destino da tradução.
        timeout: Timeout em segundos para cada request.
    """

    def __init__(
        self,
        base_url: str = settings.ollama_base_url,
        model: str = settings.ollama_model,
        target_language: str = settings.target_language,
        timeout: int = settings.ollama_timeout,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.target_language = target_language
        self.timeout = timeout
        self._endpoint = f"{self.base_url}/api/generate"

    async def _process_text(self, text: str, client: httpx.AsyncClient, mode: str = "translate") -> str:
        """Processa um trecho de texto via Ollama (traduzindo ou refinando o OCR).

        Args:
            text: Texto a ser processado.
            client: Instância reutilizável de httpx.AsyncClient.
            mode: Modo de processamento ("translate" ou "refine").

        Returns:
            Texto processado.

        Raises:
            TranslationError: Se Ollama retornar erro ou for inacessível.
        """
        if mode == "refine":
            prompt = (
                "You are an academic OCR post-processing assistant. "
                "Your task is to correct scanning noises, fix missing Portuguese/English accents, "
                "remove spurious/orphan characters (like isolated letters 'a', '1', 'c' inserted by mistake), "
                "and merge incorrect line breaks in the text. "
                "Maintain the original language (Portuguese/English), tone, scientific meaning, "
                "and preserve all author names and citations exactly as they are. "
                "Return ONLY the cleaned and corrected text, with no explanations or extra content.\n\n"
                f"{text}"
            )
        else:
            prompt = (
                f"Translate the following text to {self.target_language}. "
                "Return only the translation, no explanations or extra content.\n\n"
                f"{text}"
            )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }

        try:
            response = await client.post(
                self._endpoint,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise TranslationError(
                f"Ollama retornou status {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            raise TranslationError(f"Erro ao conectar ao Ollama: {exc}") from exc

        data = response.json()
        return data.get("response", text).strip()

    async def translate_html(self, html_content: str, mode: str = "translate") -> str:
        """Processa o conteúdo textual de um HTML via Ollama preservando a estrutura.

        Para cada elemento das tags definidas em _TRANSLATABLE_TAGS, o texto
        é extraído, traduzido ou refinado individualmente via Ollama e reinserido no HTML.
        Elementos vazios são ignorados.

        Args:
            html_content: Conteúdo HTML de entrada.
            mode: Modo de processamento ("translate" ou "refine").

        Returns:
            HTML com o texto processado para o idioma alvo ou refinado.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        elements = soup.find_all(list(_TRANSLATABLE_TAGS))

        async with httpx.AsyncClient() as client:
            for element in elements:
                original_text = element.get_text()
                if not original_text.strip():
                    continue
                processed = await self._process_text(original_text, client, mode=mode)
                element.string = processed

        return str(soup)
