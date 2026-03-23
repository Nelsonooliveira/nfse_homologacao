# NFS-e Homologação — Portal Nacional

Aplicação local para emissão de **NFS-e fictícias** no ambiente de **homologação** do Portal Nacional de NFS-e (Padrão Nacional ABRASF/SEFIN).

> ⚠️ Todos os dados são fictícios. Esta aplicação **não** deve ser usada em produção.

---

## Estrutura de Pastas

```
nfse_homologacao/
├── config/
│   └── config.yaml          # Configurações do emitente e endpoint
├── src/
│   ├── builder.py           # Monta o XML de NFS-e
│   ├── sender.py            # Envia o XML ao endpoint de homologação
│   ├── signer.py            # Assina o XML com certificado A1 (opcional)
│   └── logger.py            # Salva respostas e logs
├── output/
│   ├── xmls/                # XMLs enviados e respostas
│   └── logs/                # Logs de erro e sucesso
├── tests/
│   └── test_builder.py      # Testes unitários
├── main.py                  # Ponto de entrada (CLI)
├── requirements.txt
└── README.md
```

---

## Pré-requisitos

```bash
pip install -r requirements.txt
```

---

## Configuração

Edite `config/config.yaml` com os dados do seu emitente de **homologação**:

```yaml
emitente:
  cnpj: "12345678000195"
  razao_social: "EMPRESA TESTE HOMOLOGACAO LTDA"
  im: "123456"           # Inscrição Municipal fictícia
  codigo_municipio: "3550308"  # São Paulo
```

---

## Uso

```bash
# Emitir NFS-e com dados padrão fictícios
python main.py

# Emitir com parâmetros customizados
python main.py \
  --cnpj-emitente 12345678000195 \
  --nome-tomador "TOMADOR FICTICIO LTDA" \
  --cnpj-tomador 00000000000191 \
  --valor 100.00 \
  --codigo-servico "1.07" \
  --descricao "Servicos de desenvolvimento de software para homologacao"
```

---

## Perguntas Frequentes

### Qual WSDL/XSD usar?
O Portal Nacional usa REST (JSON/XML) via `https://notanacional.speedgov.com.br`.  
Os schemas XSD de referência estão em: https://www.nfse.gov.br/EmissorNacional/

### Como usar certificado A1 em produção?
Edite `config/config.yaml` e informe `cert_path` e `cert_password`. O módulo `signer.py` carrega automaticamente o `.pfx` e assina o XML com `signxml`.

### O campo `tpAmb`
- `1` = Produção  
- `2` = Homologação ← **esta aplicação sempre usa 2**
