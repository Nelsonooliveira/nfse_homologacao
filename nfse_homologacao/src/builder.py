"""
src/builder.py
==============
Monta o XML de NFS-e (lote de RPS) seguindo o padrão do Portal Nacional ABRASF v2.04.
Todos os dados gerados aqui são FICTÍCIOS e destinados apenas a homologação.

Referência de schema: NFS-e Nacional — tipos_nfse_v2_04.xsd
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from lxml import etree


# Namespace principal da ABRASF
NS_ABRASF = "http://www.abrasf.org.br/nfse"

NSMAP = {
    None: NS_ABRASF,
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}


def _ns(tag: str, namespace: str = NS_ABRASF) -> str:
    return f"{{{namespace}}}{tag}"


def _text(parent: etree._Element, tag: str, value: str, ns: str = NS_ABRASF) -> etree._Element:
    el = etree.SubElement(parent, _ns(tag, ns))
    el.text = str(value)
    return el


class NFSeBuilder:
    """
    Constrói o envelope XML para envio ao Portal Nacional de NFS-e.

    Parâmetros de negócio:
        emitente        : dict com chaves cnpj, razao_social, im, codigo_municipio
        tomador_nome    : str  — nome fictício do tomador
        tomador_doc     : str  — CPF (11 dígitos) ou CNPJ (14 dígitos) fictício
        codigo_servico  : str  — código ABRASF (ex.: "1.07")
        descricao       : str  — descrição do serviço prestado
        valor_servico   : Decimal — valor em R$
        aliquota_iss    : float — percentual (ex.: 2.0 para 2%)
        numero_rps      : int  — número sequencial do RPS
        serie_rps       : str  — série do RPS (ex.: "A")
        competencia     : datetime — mês/ano de competência (default: hoje)
        tp_amb          : int  — 1=Produção | 2=Homologação (default: 2)
    """

    def __init__(
        self,
        emitente: dict,
        tomador_nome: str,
        tomador_doc: str,
        codigo_servico: str,
        descricao: str,
        valor_servico: Decimal,
        aliquota_iss: float = 2.0,
        numero_rps: int = 1,
        serie_rps: str = "A",
        competencia: datetime | None = None,
        tp_amb: int = 2,
    ):
        self.emitente = emitente
        self.tomador_nome = tomador_nome
        self.tomador_doc = tomador_doc.replace(".", "").replace("/", "").replace("-", "").strip()
        self.codigo_servico = codigo_servico
        self.descricao = descricao
        self.valor_servico = Decimal(str(valor_servico))
        self.aliquota_iss = float(aliquota_iss)
        self.numero_rps = numero_rps
        self.serie_rps = serie_rps
        self.competencia = competencia or datetime.now(tz=timezone.utc)
        self.tp_amb = tp_amb

        # Derivados
        self.valor_iss = (self.valor_servico * Decimal(str(self.aliquota_iss)) / 100).quantize(
            Decimal("0.01")
        )
        self.valor_liquido = self.valor_servico  # sem retenções para simplificar
        self.id_lote = str(uuid.uuid4().int)[:15]  # 15 dígitos numéricos
        self.cnpj_emitente = (
            emitente["cnpj"].replace(".", "").replace("/", "").replace("-", "").strip()
        )

    # ------------------------------------------------------------------
    # Ponto de entrada principal
    # ------------------------------------------------------------------
    def build_xml(self) -> bytes:
        """
        Retorna o XML completo em bytes (UTF-8), pronto para envio ou assinatura.
        """
        root = self._build_envelope_lote()
        return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8")

    def build_xml_pretty(self) -> str:
        """Versão legível do XML (string)."""
        return self.build_xml().decode("utf-8")

    # ------------------------------------------------------------------
    # Envelope de Lote RPS
    # ------------------------------------------------------------------
    def _build_envelope_lote(self) -> etree._Element:
        root = etree.Element(_ns("EnviarLoteRpsEnvio"), nsmap=NSMAP)
        root.set(
            "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation",
            "http://www.abrasf.org.br/nfse http://www.abrasf.org.br/nfse.xsd"
        )

        lote = etree.SubElement(root, _ns("LoteRps"))
        lote.set("versao", "2.04")
        lote.set("Id", f"Lote{self.id_lote}")

        _text(lote, "NumeroLote", self.id_lote)
        cpf_cnpj_lote = etree.SubElement(lote, _ns("CpfCnpj"))
        cpf_cnpj_lote.set("id", "E1")
        _text(cpf_cnpj_lote, "Cnpj", self.cnpj_emitente)
        _text(lote, "InscricaoMunicipal", self.emitente.get("im", "12345678"))
        _text(lote, "QuantidadeRps", "1")

        lista_rps = etree.SubElement(lote, _ns("ListaRps"))
        lista_rps.append(self._build_rps())

        return root

    # ------------------------------------------------------------------
    # RPS (Recibo Provisório de Serviços)
    # ------------------------------------------------------------------
    def _build_rps(self) -> etree._Element:
        rps = etree.Element(_ns("Rps"))
        info = etree.SubElement(rps, _ns("InfDeclaracaoPrestacaoServico"))
        info.set("Id", f"RPS{self.numero_rps}")

        # -- Identificação do RPS --
        self._build_identificacao_rps(info)

        _text(info, "DataEmissao", self.competencia.strftime("%Y-%m-%d"))
        _text(info, "Competencia", self.competencia.strftime("%Y-%m-%d"))
        _text(info, "TipoAmbiente", str(self.tp_amb))  # 2 = Homologação

        # -- Serviço --
        self._build_servico(info)

        # -- Prestador --
        self._build_prestador(info)

        # -- Tomador --
        self._build_tomador(info)

        _text(info, "OptanteSimplesNacional",
              "1" if self.emitente.get("optante_simples") else "2")
        _text(info, "IncentivoFiscal", "2")  # 2 = Não

        return rps

    def _build_identificacao_rps(self, parent: etree._Element) -> None:
        id_rps = etree.SubElement(parent, _ns("IdentificacaoRps"))
        _text(id_rps, "Numero", str(self.numero_rps))
        _text(id_rps, "Serie", self.serie_rps)
        _text(id_rps, "Tipo", "1")  # 1 = RPS

    def _build_servico(self, parent: etree._Element) -> None:
        svc = etree.SubElement(parent, _ns("Servico"))

        valores = etree.SubElement(svc, _ns("Valores"))
        _text(valores, "ValorServicos",    f"{self.valor_servico:.2f}")
        _text(valores, "ValorDeducoes",    "0.00")
        _text(valores, "ValorPis",         "0.00")
        _text(valores, "ValorCofins",      "0.00")
        _text(valores, "ValorInss",        "0.00")
        _text(valores, "ValorIr",          "0.00")
        _text(valores, "ValorCsll",        "0.00")
        _text(valores, "IssRetido",        "2")    # 2 = Não retido
        _text(valores, "ValorIss",         f"{self.valor_iss:.2f}")
        _text(valores, "OutrasRetencoes",  "0.00")
        _text(valores, "BaseCalculo",      f"{self.valor_servico:.2f}")
        _text(valores, "Aliquota",         f"{self.aliquota_iss / 100:.4f}")
        _text(valores, "ValorLiquidoNfse", f"{self.valor_liquido:.2f}")
        _text(valores, "DescontoIncondicionado", "0.00")
        _text(valores, "DescontoCondicionado",   "0.00")

        _text(svc, "ItemListaServico",  self.codigo_servico)
        _text(svc, "CodigoCnae",        "6201501")  # CNAE fictício — Desenvolvimento de programas
        _text(svc, "CodigoTributacaoMunicipio", self.codigo_servico.replace(".", "").zfill(7))
        _text(svc, "Discriminacao",     self.descricao[:2000])  # limite do schema
        _text(svc, "CodigoMunicipio",   self.emitente.get("codigo_municipio", "3550308"))
        _text(svc, "CodigoPais",        "1058")  # Brasil
        _text(svc, "ExigibilidadeISS",  "1")     # 1 = Exigível
        _text(svc, "MunicipioIncidencia", self.emitente.get("codigo_municipio", "3550308"))

    def _build_prestador(self, parent: etree._Element) -> None:
        prestador = etree.SubElement(parent, _ns("Prestador"))
        cpf_cnpj = etree.SubElement(prestador, _ns("CpfCnpj"))
        cpf_cnpj.set("id", "E2")
        _text(cpf_cnpj, "Cnpj", self.cnpj_emitente)
        _text(prestador, "InscricaoMunicipal", self.emitente.get("im", "12345678"))

    def _build_tomador(self, parent: etree._Element) -> None:
        tomador = etree.SubElement(parent, _ns("TomadorServico"))

        ident = etree.SubElement(tomador, _ns("IdentificacaoTomador"))
        cpf_cnpj = etree.SubElement(ident, _ns("CpfCnpj"))
        cpf_cnpj.set("id", "E3")

        if len(self.tomador_doc) == 11:
            _text(cpf_cnpj, "Cpf", self.tomador_doc)
        else:
            _text(cpf_cnpj, "Cnpj", self.tomador_doc.ljust(14, "0")[:14])

        _text(tomador, "RazaoSocial", self.tomador_nome[:150])

        end = etree.SubElement(tomador, _ns("Endereco"))
        _text(end, "Endereco",    "Rua Ficticia de Homologacao")
        _text(end, "Numero",      "1")
        _text(end, "Bairro",      "Centro")
        _text(end, "CodigoMunicipio", "3550308")
        _text(end, "Uf",          "SP")
        _text(end, "CodigoPais",  "1058")
        _text(end, "Cep",         "01310100")

        contato = etree.SubElement(tomador, _ns("Contato"))
        _text(contato, "Telefone", "1100000000")
        _text(contato, "Email",    "homologacao@teste.exemplo.com")
