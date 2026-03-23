"""
exemplos.py — Exemplos de uso programático da biblioteca NFS-e Homologação
===========================================================================
Execute: python exemplos.py

Todos os dados são FICTÍCIOS — apenas para testes de integração.
"""

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.builder import NFSeBuilder
from src.signer import sign_xml
from src.sender import enviar_lote_rps
from src.logger import configurar_logging, salvar_xml_enviado, salvar_resposta, salvar_sumario

configurar_logging("output/logs")

# ── Emitente fictício padrão ─────────────────────────────────────────────────
EMITENTE = {
    "cnpj": "12345678000195",
    "razao_social": "EMPRESA TESTE HOMOLOGACAO LTDA",
    "im": "123456",
    "codigo_municipio": "3550308",
    "optante_simples": False,
}


# ═══════════════════════════════════════════════════════════════════════════════
# Exemplo 1 — NFS-e básica de suporte técnico (R$ 100,00)
# ═══════════════════════════════════════════════════════════════════════════════
def exemplo_basico():
    print("\n" + "═"*60)
    print("EXEMPLO 1 — NFS-e básica (R$ 100,00 | ISS 2%)")
    print("═"*60)

    builder = NFSeBuilder(
        emitente=EMITENTE,
        tomador_nome="TOMADOR FICTICIO LTDA",
        tomador_doc="00000000000191",          # CNPJ fictício
        codigo_servico="1.07",                  # Suporte técnico em informática
        descricao="Prestação de serviços de suporte técnico — HOMOLOGAÇÃO",
        valor_servico=Decimal("100.00"),
        aliquota_iss=2.0,
        numero_rps=1,
        serie_rps="A",
        tp_amb=2,                               # Homologação
    )

    xml_bytes = builder.build_xml()
    print(f"✅ XML gerado: {len(xml_bytes)} bytes")
    print(f"   ISS calculado: R$ {builder.valor_iss}")

    # Salva localmente (dry-run — não envia)
    salvar_xml_enviado(xml_bytes, builder.numero_rps, "output/xmls")


# ═══════════════════════════════════════════════════════════════════════════════
# Exemplo 2 — NFS-e de consultoria (R$ 5.000,00 | ISS 5%)
# ═══════════════════════════════════════════════════════════════════════════════
def exemplo_consultoria():
    print("\n" + "═"*60)
    print("EXEMPLO 2 — Consultoria (R$ 5.000,00 | ISS 5%)")
    print("═"*60)

    builder = NFSeBuilder(
        emitente=EMITENTE,
        tomador_nome="CLIENTE PESSOA FISICA TESTE",
        tomador_doc="12345678909",              # CPF fictício (11 dígitos)
        codigo_servico="17.01",                 # Assessoria/consultoria
        descricao=(
            "Consultoria em transformação digital e arquitetura de sistemas — "
            "AMBIENTE DE HOMOLOGAÇÃO — DADO FICTÍCIO"
        ),
        valor_servico=Decimal("5000.00"),
        aliquota_iss=5.0,
        numero_rps=2,
        serie_rps="A",
        tp_amb=2,
    )

    xml_bytes = builder.build_xml()
    print(f"✅ XML gerado: {len(xml_bytes)} bytes")
    print(f"   ISS calculado: R$ {builder.valor_iss}")
    print(f"   Valor líquido: R$ {builder.valor_liquido}")

    salvar_xml_enviado(xml_bytes, builder.numero_rps, "output/xmls")


# ═══════════════════════════════════════════════════════════════════════════════
# Exemplo 3 — Envio real ao portal (comentado por padrão)
# ═══════════════════════════════════════════════════════════════════════════════
def exemplo_envio_real():
    """
    Descomente e ajuste para enviar ao portal de homologação real.
    Certifique-se de ter acesso ao endpoint antes de executar.
    """
    print("\n" + "═"*60)
    print("EXEMPLO 3 — Envio ao portal de homologação")
    print("═"*60)

    builder = NFSeBuilder(
        emitente=EMITENTE,
        tomador_nome="TOMADOR ENVIO REAL LTDA",
        tomador_doc="00000000000191",
        codigo_servico="1.02",
        descricao="Desenvolvimento de software sob demanda — HOMOLOGAÇÃO",
        valor_servico=Decimal("250.00"),
        aliquota_iss=2.0,
        numero_rps=3,
        tp_amb=2,
    )

    xml_bytes = builder.build_xml()

    # Opcional: assinar com certificado A1
    # xml_bytes = sign_xml(xml_bytes, pfx_path="cert.pfx", pfx_password="senha")

    # Enviar ao portal
    resposta = enviar_lote_rps(
        xml_bytes=xml_bytes,
        base_url="https://notanacional.speedgov.com.br",
        rota="/nfse-service/v1/nfse/recepcionar-lote-rps",
        timeout=30,
        cnpj_emitente=EMITENTE["cnpj"],
    )

    # Salvar resultados
    salvar_xml_enviado(xml_bytes, builder.numero_rps, "output/xmls")
    if resposta.xml_resposta:
        salvar_resposta(resposta.xml_resposta, builder.numero_rps, "output/xmls")

    sumario = {
        "numero_rps":   builder.numero_rps,
        "sucesso":      resposta.sucesso,
        "status_http":  resposta.status_http,
        "protocolo":    resposta.protocolo,
        "mensagem":     resposta.mensagem,
    }
    salvar_sumario(sumario, builder.numero_rps, "output/logs")

    if resposta.sucesso:
        print(f"✅ NFS-e aceita! Protocolo: {resposta.protocolo}")
    else:
        print(f"❌ Erro HTTP {resposta.status_http}: {resposta.mensagem}")


# ═══════════════════════════════════════════════════════════════════════════════
# Exemplo 4 — Geração em lote (múltiplos RPS)
# ═══════════════════════════════════════════════════════════════════════════════
def exemplo_lote():
    print("\n" + "═"*60)
    print("EXEMPLO 4 — Geração em lote (3 RPS fictícios)")
    print("═"*60)

    servicos = [
        ("CLIENTE A LTDA",       "00000000000191", "1.01", "150.00", 2.0),
        ("CLIENTE B PESSOA FIS", "98765432100",    "1.05", "800.00", 2.0),
        ("CLIENTE C SA",         "11222333000181", "17.01","2000.00",5.0),
    ]

    for i, (nome, doc, cod, valor, aliq) in enumerate(servicos, start=10):
        builder = NFSeBuilder(
            emitente=EMITENTE,
            tomador_nome=nome,
            tomador_doc=doc,
            codigo_servico=cod,
            descricao=f"Serviço {cod} para homologação — cliente {nome}",
            valor_servico=Decimal(valor),
            aliquota_iss=aliq,
            numero_rps=i,
            tp_amb=2,
        )
        xml_bytes = builder.build_xml()
        salvar_xml_enviado(xml_bytes, builder.numero_rps, "output/xmls")
        print(f"  RPS {i:02d} | {nome:<25} | R$ {valor:>8} | ISS R$ {builder.valor_iss}")

    print("✅ Lote gerado e salvo em output/xmls/")


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    exemplo_basico()
    exemplo_consultoria()
    # exemplo_envio_real()    # descomente para testar envio real
    exemplo_lote()

    print("\n" + "═"*60)
    print("Todos os exemplos concluídos.")
    print("Arquivos salvos em output/xmls/ e output/logs/")
    print("═"*60)
