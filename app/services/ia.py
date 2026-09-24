"""Integração com a API da Anthropic usada pelo Agente Financeiro.

Isolada das rotas Flask. POST /transacoes chama `categorizar_transacao`
e, quando o projetado fica negativo, `gerar_recomendacao`.
"""

from __future__ import annotations

from typing import Iterable

import anthropic
from flask import current_app


class IAServiceError(RuntimeError):
    """Erro controlado na integração com o provedor de IA."""


def _client() -> anthropic.Anthropic:
    api_key = current_app.config.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise IAServiceError("ANTHROPIC_API_KEY não configurada")

    timeout = float(current_app.config.get("ANTHROPIC_TIMEOUT", 10))
    return anthropic.Anthropic(
        api_key=api_key,
        timeout=timeout,
        max_retries=1,
    )


def _model() -> str:
    return current_app.config.get(
        "ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"
    )


def _text_from_response(response: anthropic.types.Message) -> str:
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            return text.strip()
    raise IAServiceError("A IA retornou uma resposta sem texto")


def categorizar_transacao(
    descricao: str,
    categorias: Iterable[str],
) -> str:
    descricao = (descricao or "").strip()
    categorias = [str(c).strip() for c in categorias if str(c).strip()]

    if not descricao:
        raise IAServiceError("A descrição da transação é obrigatória para a IA")
    if not categorias:
        raise IAServiceError("Nenhuma categoria disponível para classificação")

    opcoes = "\n".join(f"- {categoria}" for categoria in categorias)
    prompt = f"""Classifique a transação abaixo em UMA das categorias permitidas.

Descrição da transação:
{descricao}

Categorias permitidas:
{opcoes}

Responda somente com o nome EXATO de uma das categorias permitidas.
Não explique a resposta e não crie uma categoria nova."""

    try:
        response = _client().messages.create(
            model=_model(),
            max_tokens=50,
            system=(
                "Você é um classificador financeiro. "
                "Siga exatamente as categorias fornecidas."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        resultado = _text_from_response(response).strip().strip("\"'")
    except IAServiceError:
        raise
    except (anthropic.APIError, anthropic.APITimeoutError, anthropic.APIConnectionError) as exc:
        raise IAServiceError(f"Falha na chamada da IA: {exc}") from exc
    except Exception as exc:
        raise IAServiceError(f"Erro inesperado na integração com a IA: {exc}") from exc

    for categoria in categorias:
        if resultado == categoria:
            return categoria
    for categoria in categorias:
        if resultado.casefold() == categoria.casefold():
            return categoria

    raise IAServiceError(f"A IA retornou uma categoria inválida: {resultado!r}")


def gerar_recomendacao(mensagem: str) -> str:
    mensagem = (mensagem or "").strip()
    if not mensagem:
        raise IAServiceError("A mensagem do alerta é obrigatória")

    prompt = f"""Você é um agente financeiro.

Alerta:
{mensagem}

Escreva uma recomendação prática, curta e objetiva para reduzir o risco de
fluxo de caixa negativo. Não invente dados que não estejam no alerta."""

    try:
        response = _client().messages.create(
            model=_model(),
            max_tokens=180,
            system="Você é um assistente financeiro objetivo e conservador.",
            messages=[{"role": "user", "content": prompt}],
        )
        return _text_from_response(response)
    except IAServiceError:
        raise
    except (anthropic.APIError, anthropic.APITimeoutError, anthropic.APIConnectionError) as exc:
        raise IAServiceError(f"Falha na chamada da IA: {exc}") from exc
    except Exception as exc:
        raise IAServiceError(f"Erro inesperado na integração com a IA: {exc}") from exc
