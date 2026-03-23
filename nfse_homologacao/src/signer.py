"""
src/signer.py
=============
Assina digitalmente o XML de NFS-e com certificado A1 (.pfx).

Em homologação o certificado é OPCIONAL — a maioria dos municípios
aceita envios sem assinatura no ambiente de testes.

Dependências: cryptography, signxml (lxml-xmlsec alternativo puro-Python)
"""

import logging
from pathlib import Path

logger = logging.getLogger("nfse.signer")


def sign_xml(xml_bytes: bytes, pfx_path: str, pfx_password: str) -> bytes:
    """
    Assina o XML com o certificado A1 (.pfx) informado.

    Args:
        xml_bytes   : XML cru gerado pelo builder (bytes UTF-8)
        pfx_path    : Caminho para o arquivo .pfx
        pfx_password: Senha do certificado

    Returns:
        XML assinado como bytes
    """
    if not pfx_path:
        logger.info("Nenhum certificado configurado — XML enviado SEM assinatura (modo homologação).")
        return xml_bytes

    try:
        from cryptography.hazmat.primitives.serialization import pkcs12
        from cryptography.hazmat.backends import default_backend
        from signxml import XMLSigner, methods

        pfx_data = Path(pfx_path).read_bytes()
        private_key, certificate, _ = pkcs12.load_key_and_certificates(
            pfx_data, pfx_password.encode(), backend=default_backend()
        )

        from lxml import etree

        root = etree.fromstring(xml_bytes)
        signer = XMLSigner(
            method=methods.enveloped,
            signature_algorithm="rsa-sha256",
            digest_algorithm="sha256",
            c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
        )
        signed_root = signer.sign(
            root,
            key=private_key,
            cert=certificate,
            reference_uri="#RPS1",  # ID do elemento a assinar
        )

        signed_bytes = etree.tostring(
            signed_root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
        )
        logger.info("XML assinado com sucesso usando certificado: %s", pfx_path)
        return signed_bytes

    except ImportError:
        logger.error(
            "Bibliotecas de assinatura não instaladas. "
            "Execute: pip install cryptography signxml"
        )
        return xml_bytes
    except Exception as exc:
        logger.error("Erro ao assinar XML: %s", exc)
        raise
