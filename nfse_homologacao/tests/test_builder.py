"""
tests/test_builder.py
=====================
Testes unitários para a montagem do XML de NFS-e.

Execute com:
    pip install pytest
    pytest tests/
"""

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.builder import NFSeBuilder
from lxml import etree

# ── Fixtures ──────────────────────────────────────────────────────────────────

EMITENTE = {
    "cnpj": "12345678000195",
    "razao_social": "EMPRESA TESTE HOMOLOGACAO LTDA",
    "im": "123456",
    "codigo_municipio": "3550308",
    "optante_simples": False,
}


def builder_padrao(**kwargs):
    defaults = dict(
        emitente=EMITENTE,
        tomador_nome="TOMADOR FICTICIO LTDA",
        tomador_doc="00000000000191",
        codigo_servico="1.07",
        descricao="Servico de teste para homologacao",
        valor_servico=Decimal("100.00"),
        aliquota_iss=2.0,
        numero_rps=1,
        serie_rps="A",
        tp_amb=2,
    )
    defaults.update(kwargs)
    return NFSeBuilder(**defaults)


# ── Testes ────────────────────────────────────────────────────────────────────

class TestBuild:
    def test_xml_e_valido_utf8(self):
        b = builder_padrao()
        xml = b.build_xml()
        assert isinstance(xml, bytes)
        assert b"UTF-8" in xml or b"utf-8" in xml.lower()

    def test_xml_parseavel(self):
        b = builder_padrao()
        xml = b.build_xml()
        root = etree.fromstring(xml)
        assert root is not None

    def test_tp_amb_homologacao(self):
        b = builder_padrao(tp_amb=2)
        xml = b.build_xml()
        root = etree.fromstring(xml)
        els = root.xpath("//*[local-name()='TipoAmbiente']")
        assert els, "TipoAmbiente não encontrado no XML"
        assert els[0].text == "2", "Deve ser 2 (homologação)"

    def test_valor_servico_correto(self):
        b = builder_padrao(valor_servico=Decimal("250.00"))
        xml = b.build_xml()
        root = etree.fromstring(xml)
        els = root.xpath("//*[local-name()='ValorServicos']")
        assert els
        assert els[0].text == "250.00"

    def test_calculo_iss(self):
        b = builder_padrao(valor_servico=Decimal("100.00"), aliquota_iss=2.0)
        assert b.valor_iss == Decimal("2.00")

    def test_calculo_iss_diferente(self):
        b = builder_padrao(valor_servico=Decimal("500.00"), aliquota_iss=5.0)
        assert b.valor_iss == Decimal("25.00")

    def test_cnpj_tomador_14_digitos(self):
        b = builder_padrao(tomador_doc="00.000.000/0001-91")
        xml = b.build_xml()
        root = etree.fromstring(xml)
        els = root.xpath("//*[local-name()='Cnpj']")
        # O CNPJ do tomador deve estar limpo (14 dígitos)
        cnpjs = [e.text for e in els if e.text and len(e.text) == 14]
        assert cnpjs, "CNPJ do tomador deve ter 14 dígitos sem pontuação"

    def test_cpf_tomador_11_digitos(self):
        b = builder_padrao(tomador_doc="123.456.789-09")
        xml = b.build_xml()
        root = etree.fromstring(xml)
        els = root.xpath("//*[local-name()='Cpf']")
        assert els, "CPF deve ser emitido quando doc tem 11 dígitos"
        assert els[0].text and len(els[0].text) == 11

    def test_codigo_servico_presente(self):
        b = builder_padrao(codigo_servico="1.07")
        xml = b.build_xml()
        root = etree.fromstring(xml)
        els = root.xpath("//*[local-name()='ItemListaServico']")
        assert els
        assert els[0].text == "1.07"

    def test_numero_rps_presente(self):
        b = builder_padrao(numero_rps=42)
        xml = b.build_xml()
        root = etree.fromstring(xml)
        els = root.xpath("//*[local-name()='Numero']")
        assert any(e.text == "42" for e in els), "Número do RPS deve ser 42"

    def test_descricao_truncada(self):
        descricao_longa = "X" * 3000  # > 2000 chars (limite do schema)
        b = builder_padrao(descricao=descricao_longa)
        xml = b.build_xml()
        root = etree.fromstring(xml)
        els = root.xpath("//*[local-name()='Discriminacao']")
        assert els
        assert len(els[0].text) <= 2000, "Discriminação deve ser truncada em 2000 chars"

    def test_xml_pretty_e_string(self):
        b = builder_padrao()
        pretty = b.build_xml_pretty()
        assert isinstance(pretty, str)
        assert "EnviarLoteRpsEnvio" in pretty


class TestSumarioValores:
    """Verifica que campos financeiros estão coerentes no XML."""

    def test_valor_liquido_igual_valor_servico_sem_retencoes(self):
        b = builder_padrao(valor_servico=Decimal("300.00"))
        assert b.valor_liquido == Decimal("300.00")

    def test_aliquota_no_xml(self):
        b = builder_padrao(valor_servico=Decimal("100.00"), aliquota_iss=5.0)
        xml = b.build_xml()
        root = etree.fromstring(xml)
        els = root.xpath("//*[local-name()='Aliquota']")
        assert els
        # 5% → 0.0500
        assert els[0].text == "0.0500"
