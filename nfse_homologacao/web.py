import sys
from decimal import Decimal
from pathlib import Path
from flask import Flask, request, Response

# Ajusta path para importar a pasta src/
sys.path.insert(0, str(Path(__file__).parent))
from src.builder import NFSeBuilder

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Gerador de NFS-e (Localhost)</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; max-width: 600px; background-color: #f9f9f9;}
        label { display: block; margin-top: 10px; font-weight: bold; color: #333; }
        input, textarea { width: 100%; padding: 8px; margin-top: 5px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
        button { margin-top: 20px; padding: 10px 20px; font-size: 16px; cursor: pointer; background-color: #28a745; color: white; border: none; border-radius: 4px; width: 100%;}
        button:hover { background-color: #218838; }
        .section { background: white; border: 1px solid #ddd; padding: 15px; margin-top: 15px; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>Emissor de NFS-e (Homologação)</h1>
    <form method="POST" action="/gerar">
        <div class="section">
            <h3>🏢 Dados do Emitente</h3>
            <label>CNPJ:</label> <input type="text" name="emi_cnpj" value="12345678000195">
            <label>Razão Social:</label> <input type="text" name="emi_razao" value="EMPRESA TESTE LTDA">
            <label>Inscrição Municipal:</label> <input type="text" name="emi_im" value="123456">
            <label>Código Município (IBGE):</label> <input type="text" name="emi_mun" value="3550308">
        </div>

        <div class="section">
            <h3>👤 Dados do Tomador (Cliente)</h3>
            <label>Nome / Razão Social:</label> <input type="text" name="tom_nome" value="CLIENTE TESTE LTDA">
            <label>CPF / CNPJ:</label> <input type="text" name="tom_doc" value="00000000000191">
        </div>

        <div class="section">
            <h3>⚙️ Dados do Serviço</h3>
            <label>Código do Serviço (Ex: 1.07):</label> <input type="text" name="srv_codigo" value="1.07">
            <label>Descrição:</label> <textarea name="srv_desc" rows="3">Serviço de teste localhost</textarea>
            <label>Valor (R$):</label> <input type="number" step="0.01" name="srv_valor" value="150.00">
            <label>Alíquota ISS (%):</label> <input type="number" step="0.01" name="srv_aliq" value="2.0">
        </div>

        <button type="submit">Gerar XML</button>
    </form>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return HTML_TEMPLATE

@app.route("/gerar", methods=["POST"])
def gerar_xml():
    emitente = {
        "cnpj": request.form.get("emi_cnpj"),
        "razao_social": request.form.get("emi_razao"),
        "im": request.form.get("emi_im"),
        "codigo_municipio": request.form.get("emi_mun"),
        "optante_simples": False
    }

    builder = NFSeBuilder(
        emitente=emitente,
        tomador_nome=request.form.get("tom_nome"),
        tomador_doc=request.form.get("tom_doc"),
        codigo_servico=request.form.get("srv_codigo"),
        descricao=request.form.get("srv_desc"),
        valor_servico=Decimal(request.form.get("srv_valor", "0.00")),
        aliquota_iss=float(request.form.get("srv_aliq", "2.0"))
    )

    xml_bytes = builder.build_xml()
    return Response(
        xml_bytes,
        mimetype="application/xml",
        headers={"Content-Disposition": "attachment; filename=nfse_gerada.xml"}
    )

if __name__ == "__main__":
    print("🚀 Servidor rodando! Acesse http://localhost:5000 no seu navegador.")
    app.run(debug=True, port=5000)