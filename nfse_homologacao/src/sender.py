"""
src/sender.py
=============
Envia o XML de NFS-e ao endpoint de homologação do Portal Nacional.

O Portal Nacional usa REST com Content-Type application/xml (ou JSON para
consultas). Este módulo encapsula o envio e trata os retornos.

Endpoint base (homologação): https://notanacional.speedgov.com.br
"""

import logging
from dataclasses import dataclass
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("nfse.sender")


@dataclass
class RespostaEnvio:
    """Resultado de um envio ao webservice."""
    sucesso: bool
    status_http: int
    protocolo: str | None
    mensagem: str
    xml_resposta: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


def _build_session(timeout: int = 30) -> requests.Session:
    """Cria sessão com retry automático e timeout."""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.timeout = timeout
    return session


def enviar_lote_rps(
    xml_bytes: bytes,
    base_url: str,
    rota: str = "/nfse-service/v1/nfse/recepcionar-lote-rps",
    timeout: int = 30,
    cnpj_emitente: str = "",
    token: str = "",
) -> RespostaEnvio:
    """
    Envia o lote de RPS ao Portal Nacional.

    Args:
        xml_bytes       : XML assinado (ou sem assinatura em homologação)
        base_url        : URL base do ambiente (ex.: https://notanacional.speedgov.com.br)
        rota            : Rota REST do endpoint
        timeout         : Timeout em segundos
        cnpj_emitente   : CNPJ do emitente (usado em headers, se necessário)
        token           : Token de autenticação (se exigido pelo portal)

    Returns:
        RespostaEnvio com todos os campos preenchidos
    """
    url = f"{base_url.rstrip('/')}{rota}"
    headers = {
        "Content-Type": "application/xml; charset=UTF-8",
        "Accept": "application/xml",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"
    if cnpj_emitente:
        headers["X-CNPJ-Emitente"] = cnpj_emitente

    logger.info("Enviando NFS-e para: %s", url)
    logger.debug("Payload (%d bytes):\n%s", len(xml_bytes), xml_bytes.decode("utf-8"))

    session = _build_session(timeout)

    try:
        resp = session.post(url, data=xml_bytes, headers=headers)
    except requests.exceptions.ConnectionError as exc:
        logger.error("Falha de conexão com o endpoint: %s", exc)
        return RespostaEnvio(
            sucesso=False,
            status_http=0,
            protocolo=None,
            mensagem=f"Falha de conexão: {exc}",
            xml_resposta="",
        )
    except requests.exceptions.Timeout:
        logger.error("Timeout ao conectar em %s", url)
        return RespostaEnvio(
            sucesso=False,
            status_http=0,
            protocolo=None,
            mensagem="Timeout ao conectar ao endpoint.",
            xml_resposta="",
        )

    logger.info("HTTP %d — %s", resp.status_code, url)

    xml_resposta = resp.text
    protocolo = _extrair_protocolo(xml_resposta)
    sucesso = resp.status_code in (200, 201, 202)
    mensagem = _extrair_mensagem(xml_resposta, resp.status_code)

    if sucesso:
        logger.info("✅ NFS-e aceita pelo portal. Protocolo: %s", protocolo or "(sem protocolo)")
    else:
        logger.warning("❌ Portal retornou erro. Mensagem: %s", mensagem)

    return RespostaEnvio(
        sucesso=sucesso,
        status_http=resp.status_code,
        protocolo=protocolo,
        mensagem=mensagem,
        xml_resposta=xml_resposta,
    )


# ------------------------------------------------------------------
# Helpers de parsing da resposta
# ------------------------------------------------------------------

def _extrair_protocolo(xml_texto: str) -> str | None:
    """Tenta extrair o número de protocolo do XML de resposta."""
    try:
        from lxml import etree
        root = etree.fromstring(xml_texto.encode("utf-8"))
        # Tenta vários nomes comuns no retorno do Portal Nacional
        for tag in ("Protocolo", "NumeroProtocolo", "NumeroLote"):
            els = root.xpath(f"//*[local-name()='{tag}']")
            if els:
                return els[0].text
    except Exception:
        pass
    return None


def _extrair_mensagem(xml_texto: str, status_http: int) -> str:
    """Tenta extrair mensagem de erro/sucesso do XML de resposta."""
    try:
        from lxml import etree
        root = etree.fromstring(xml_texto.encode("utf-8"))
        for tag in ("Mensagem", "MensagemRetorno", "Descricao", "Codigo"):
            els = root.xpath(f"//*[local-name()='{tag}']")
            if els:
                return els[0].text or ""
    except Exception:
        pass
    if status_http == 200:
        return "Processado com sucesso."
    return f"HTTP {status_http} — verifique o XML de resposta."
