"""
src/logger.py
=============
Persiste XMLs enviados, respostas do portal e logs de texto.

Estrutura de saída:
    output/
        xmls/
            YYYYMMDD_HHMMSS_rps<N>_enviado.xml
            YYYYMMDD_HHMMSS_rps<N>_resposta.xml
        logs/
            nfse_homologacao.log
"""

import json
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path

try:
    import colorlog  # opcional — só para terminal colorido
    _HAS_COLORLOG = True
except ImportError:
    _HAS_COLORLOG = False


def configurar_logging(dir_logs: str = "output/logs") -> None:
    """Configura logging em arquivo + console."""
    Path(dir_logs).mkdir(parents=True, exist_ok=True)
    log_file = Path(dir_logs) / "nfse_homologacao.log"

    fmt_arquivo = "%(asctime)s [%(levelname)-8s] %(name)s — %(message)s"
    fmt_console = "%(asctime)s [%(levelname)-8s] %(message)s"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Handler arquivo (rotativo, 5 MB, 5 backups)
    fh = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    fh.setFormatter(logging.Formatter(fmt_arquivo))
    fh.setLevel(logging.DEBUG)
    root.addHandler(fh)

    # Handler console
    if _HAS_COLORLOG:
        ch = colorlog.StreamHandler()
        ch.setFormatter(
            colorlog.ColoredFormatter(
                "%(log_color)s" + fmt_console,
                log_colors={
                    "DEBUG":    "cyan",
                    "INFO":     "green",
                    "WARNING":  "yellow",
                    "ERROR":    "red",
                    "CRITICAL": "bold_red",
                },
            )
        )
    else:
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter(fmt_console))

    ch.setLevel(logging.INFO)
    root.addHandler(ch)


def salvar_xml_enviado(
    xml_bytes: bytes,
    numero_rps: int,
    dir_xmls: str = "output/xmls",
) -> Path:
    """Salva o XML montado/enviado em disco."""
    Path(dir_xmls).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = Path(dir_xmls) / f"{ts}_rps{numero_rps}_enviado.xml"
    destino.write_bytes(xml_bytes)
    logging.getLogger("nfse.io").info("XML enviado salvo: %s", destino)
    return destino


def salvar_resposta(
    xml_resposta: str,
    numero_rps: int,
    dir_xmls: str = "output/xmls",
) -> Path:
    """Salva o XML de resposta do portal em disco."""
    Path(dir_xmls).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = Path(dir_xmls) / f"{ts}_rps{numero_rps}_resposta.xml"
    destino.write_text(xml_resposta, encoding="utf-8")
    logging.getLogger("nfse.io").info("XML de resposta salvo: %s", destino)
    return destino


def salvar_sumario(
    dados: dict,
    numero_rps: int,
    dir_logs: str = "output/logs",
) -> Path:
    """Salva um resumo JSON do processamento (útil para pipelines)."""
    Path(dir_logs).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = Path(dir_logs) / f"{ts}_rps{numero_rps}_sumario.json"
    destino.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")
    logging.getLogger("nfse.io").info("Sumário JSON salvo: %s", destino)
    return destino
