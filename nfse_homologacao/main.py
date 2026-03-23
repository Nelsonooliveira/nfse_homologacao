#!/usr/bin/env python3
"""
main.py — Ponto de entrada da aplicação NFS-e Homologação
==========================================================
Emite NFS-e fictícias no ambiente de homologação do Portal Nacional.

Uso:
    python main.py                          # dados padrão fictícios
    python main.py --valor 250.00 --numero-rps 42

⚠️  Todos os dados são FICTÍCIOS. Não usar em produção.
"""

import argparse
import sys
import logging
from decimal import Decimal
from pathlib import Path

import yaml

# ── Ajusta path para importar src/ ──────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from src.logger import configurar_logging, salvar_xml_enviado, salvar_resposta, salvar_sumario
from src.builder import NFSeBuilder
from src.signer import sign_xml
from src.sender import enviar_lote_rps

# ── Logger do módulo principal ───────────────────────────────────────────────
logger = logging.getLogger("nfse.main")

# ── Dados fictícios padrão ───────────────────────────────────────────────────
DEFAULTS = {
    "cnpj_emitente":   "12345678000195",
    "nome_tomador":    "TOMADOR FICTICIO LTDA",
    "cnpj_tomador":    "00000000000191",
    "codigo_servico":  "1.07",
    "descricao":       "Prestação de serviços de suporte técnico em informática — HOMOLOGAÇÃO",
    "valor":           "100.00",
    "numero_rps":      1,
    "serie_rps":       "A",
}


def carregar_config(caminho: str = "config/config.yaml") -> dict:
    with open(caminho, encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolver_aliquota(cfg: dict, codigo_servico: str) -> float:
    """Busca a alíquota de ISS no config.yaml pelo código do serviço."""
    servicos = cfg.get("servicos", {})
    srv = servicos.get(codigo_servico, {})
    return float(srv.get("aliquota_iss", 2.0))


def emitir_nfse(args: argparse.Namespace, cfg: dict) -> dict:
    """
    Orquestra todo o fluxo:
        1. Monta XML
        2. (Opcional) Assina com A1
        3. Envia ao portal
        4. Salva XMLs e log

    Retorna um dict com o sumário do resultado.
    """

    # ── 1. Preparar emitente ────────────────────────────────────────────────
    emitente = cfg.get("emitente", {})
    if args.cnpj_emitente:
        emitente["cnpj"] = args.cnpj_emitente

    aliquota = resolver_aliquota(cfg, args.codigo_servico)

    logger.info("=" * 60)
    logger.info("Iniciando emissão de NFS-e — HOMOLOGAÇÃO")
    logger.info("Emitente  : %s", emitente.get("razao_social", "—"))
    logger.info("CNPJ      : %s", emitente.get("cnpj"))
    logger.info("Tomador   : %s (%s)", args.nome_tomador, args.cnpj_tomador)
    logger.info("Serviço   : %s — %s", args.codigo_servico, args.descricao[:60])
    logger.info("Valor     : R$ %.2f | ISS %.1f%%", float(args.valor), aliquota)
    logger.info("RPS nº    : %d / Série %s", args.numero_rps, args.serie_rps)
    logger.info("=" * 60)

    # ── 2. Montar XML ───────────────────────────────────────────────────────
    builder = NFSeBuilder(
        emitente=emitente,
        tomador_nome=args.nome_tomador,
        tomador_doc=args.cnpj_tomador,
        codigo_servico=args.codigo_servico,
        descricao=args.descricao,
        valor_servico=Decimal(args.valor),
        aliquota_iss=aliquota,
        numero_rps=args.numero_rps,
        serie_rps=args.serie_rps,
        tp_amb=cfg.get("ambiente", 2),
    )
    xml_bytes = builder.build_xml()
    logger.info("XML montado com sucesso (%d bytes).", len(xml_bytes))

    # ── 3. Assinar (opcional) ───────────────────────────────────────────────
    cert_cfg = cfg.get("certificado", {})
    xml_bytes = sign_xml(
        xml_bytes,
        pfx_path=cert_cfg.get("path", ""),
        pfx_password=cert_cfg.get("password", ""),
    )

    # ── 4. Salvar XML enviado ───────────────────────────────────────────────
    saida = cfg.get("saida", {})
    dir_xmls = saida.get("dir_xmls", "output/xmls")
    dir_logs = saida.get("dir_logs", "output/logs")

    arquivo_enviado = salvar_xml_enviado(xml_bytes, args.numero_rps, dir_xmls)

    # ── 5. Enviar ao portal ─────────────────────────────────────────────────
    ep = cfg.get("endpoint", {})
    if args.dry_run:
        logger.warning("⚡ DRY-RUN ativado — XML NÃO será enviado ao portal.")
        resposta = type("R", (), {
            "sucesso": None, "status_http": 0, "protocolo": None,
            "mensagem": "DRY-RUN", "xml_resposta": "", "timestamp": ""
        })()
    else:
        resposta = enviar_lote_rps(
            xml_bytes=xml_bytes,
            base_url=ep.get("base_url", "https://notanacional.speedgov.com.br"),
            rota=ep.get("recepcionar_lote", "/nfse-service/v1/nfse/recepcionar-lote-rps"),
            timeout=ep.get("timeout_segundos", 30),
            cnpj_emitente=emitente.get("cnpj", ""),
        )

    # ── 6. Salvar resposta e sumário ────────────────────────────────────────
    if resposta.xml_resposta:
        salvar_resposta(resposta.xml_resposta, args.numero_rps, dir_xmls)

    sumario = {
        "numero_rps":    args.numero_rps,
        "serie_rps":     args.serie_rps,
        "tomador":       args.nome_tomador,
        "cnpj_tomador":  args.cnpj_tomador,
        "codigo_servico": args.codigo_servico,
        "valor_servico": str(args.valor),
        "aliquota_iss":  aliquota,
        "arquivo_enviado": str(arquivo_enviado),
        "sucesso_envio":  resposta.sucesso,
        "status_http":    resposta.status_http,
        "protocolo":      resposta.protocolo,
        "mensagem":       resposta.mensagem,
        "timestamp":      resposta.timestamp,
    }
    salvar_sumario(sumario, args.numero_rps, dir_logs)

    # ── 7. Resultado final ──────────────────────────────────────────────────
    if resposta.sucesso:
        logger.info("✅ NFS-e emitida com sucesso! Protocolo: %s", resposta.protocolo)
    elif args.dry_run:
        logger.info("✅ Dry-run concluído. XML salvo em: %s", arquivo_enviado)
    else:
        logger.error(
            "❌ Falha no envio (HTTP %d): %s",
            resposta.status_http, resposta.mensagem
        )

    return sumario


# ── CLI ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Emite NFS-e fictícia no Portal Nacional — HOMOLOGAÇÃO",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--config",          default="config/config.yaml",   help="Arquivo de configuração")
    p.add_argument("--cnpj-emitente",   default=DEFAULTS["cnpj_emitente"], help="CNPJ do emitente (14 dígitos, sem pontuação)")
    p.add_argument("--nome-tomador",    default=DEFAULTS["nome_tomador"], help="Nome fictício do tomador")
    p.add_argument("--cnpj-tomador",    default=DEFAULTS["cnpj_tomador"], help="CPF (11) ou CNPJ (14) fictício do tomador")
    p.add_argument("--codigo-servico",  default=DEFAULTS["codigo_servico"], help="Código ABRASF do serviço (ex.: 1.07)")
    p.add_argument("--descricao",       default=DEFAULTS["descricao"],   help="Descrição do serviço")
    p.add_argument("--valor",           default=DEFAULTS["valor"],       help="Valor do serviço em R$")
    p.add_argument("--numero-rps",      type=int, default=DEFAULTS["numero_rps"], help="Número sequencial do RPS")
    p.add_argument("--serie-rps",       default=DEFAULTS["serie_rps"],   help="Série do RPS")
    p.add_argument("--dry-run",         action="store_true",             help="Monta e salva o XML mas NÃO envia ao portal")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Carrega config e inicializa logging
    try:
        cfg = carregar_config(args.config)
    except FileNotFoundError:
        print(f"[ERRO] Arquivo de config não encontrado: {args.config}")
        sys.exit(1)

    saida = cfg.get("saida", {})
    configurar_logging(saida.get("dir_logs", "output/logs"))

    resultado = emitir_nfse(args, cfg)
    sys.exit(0 if resultado.get("sucesso_envio") or args.dry_run else 1)
