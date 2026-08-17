
import json
import os
from datetime import datetime
from io import BytesIO
from decimal import Decimal, InvalidOperation

import pandas as pd
import plotly.express as px
import streamlit as st
from defusedxml import ElementTree as ET

PASTA_XMLS_PROCESSADOS = "xmls_processados"
ARQUIVO_INDICE = os.path.join(PASTA_XMLS_PROCESSADOS, "indice.json")

st.set_page_config(
    page_title="Gestão de Produtos",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    /* Fonte e espaçamento geral */
    html, body, [class*="css"] {
        font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* Título principal */
    h1 {
        color: #1B4F8C;
        font-weight: 700;
        border-bottom: 3px solid #1B4F8C;
        padding-bottom: 0.5rem;
        margin-bottom: 0.6rem;
    }

    /* Subtítulos de seção */
    h2, h3 {
        color: #1B4F8C;
        font-weight: 600;
        margin-top: 1.8rem;
    }

    /* Legendas e textos de apoio (st.caption, help, descrições) */
    [data-testid="stCaptionContainer"],
    .stCaption,
    small {
        color: #33475B !important;
        opacity: 1 !important;
        font-size: 0.92rem !important;
    }

    /* Barra lateral */
    section[data-testid="stSidebar"] {
        background-color: #0E2A47;
    }

    section[data-testid="stSidebar"] * {
        color: #FFFFFF !important;
        opacity: 1 !important;
    }

    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] small {
        color: #C7D6E8 !important;
        opacity: 1 !important;
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #FFFFFF !important;
        border-bottom: none;
    }

    section[data-testid="stSidebar"] .stCheckbox {
        background-color: rgba(255, 255, 255, 0.06);
        border-radius: 6px;
        padding: 2px 6px;
        margin-bottom: 2px;
    }

    /* Cartões de métricas */
    div[data-testid="stMetric"] {
        background-color: #F0F4F8;
        border: 1px solid #D6E0EA;
        border-left: 5px solid #1B4F8C;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
    }

    div[data-testid="stMetricLabel"] {
        color: #4A5A6A;
        font-weight: 600;
    }

    div[data-testid="stMetricValue"] {
        color: #1B4F8C;
        font-weight: 700;
    }

    /* Botões */
    .stButton button, .stDownloadButton button {
        background-color: #1B4F8C;
        color: white;
        border-radius: 6px;
        border: none;
        font-weight: 600;
        padding: 0.5rem 1.2rem;
    }

    .stButton button:hover, .stDownloadButton button:hover {
        background-color: #163F70;
        color: white;
    }

    /* Alertas (sucesso, aviso, erro, info) */
    div[data-testid="stAlert"] {
        border-radius: 8px;
    }

    /* Tabelas e data editor */
    div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
        border: 1px solid #D6E0EA;
        border-radius: 8px;
        overflow: hidden;
    }

    /* Divisor visual entre seções */
    hr {
        border-top: 1px solid #D6E0EA;
    }
    </style>
    """,
    unsafe_allow_html=True,
)



def nome_tag(elemento):
    """
    Retorna o nome da tag sem o namespace.
    """
    return elemento.tag.split("}")[-1]


def encontrar_elemento(elemento_pai, nome):
    """
    Procura qualquer elemento descendente pelo nome da tag.
    """
    if elemento_pai is None:
        return None

    for elemento in elemento_pai.iter():
        if nome_tag(elemento) == nome:
            return elemento

    return None


def encontrar_filho(elemento_pai, nome):
    """
    Procura um filho direto pelo nome da tag.
    """
    if elemento_pai is None:
        return None

    for filho in list(elemento_pai):
        if nome_tag(filho) == nome:
            return filho
    return None


def obter_texto(elemento_pai, nome, padrao=""):
    elemento = encontrar_elemento(elemento_pai, nome)

    if elemento is not None and elemento.text:
        return elemento.text.strip()

    return padrao


def converter_decimal(valor, padrao=Decimal("0")):
    if valor is None:
        return padrao

    texto = str(valor).strip()

    if not texto:
        return padrao

    try:
        return Decimal(texto.replace(",", "."))
    except InvalidOperation:
        return padrao


def valor_tag(elemento_pai, nome):
    elemento = encontrar_elemento(elemento_pai, nome)

    if elemento is not None and elemento.text:
        return converter_decimal(elemento.text)

    return Decimal("0")


def ler_totais_nfe(root):
    total_node = encontrar_elemento(root, "ICMSTot")

    if total_node is None:
        return {
            "frete": Decimal("0"),
            "seguro": Decimal("0"),
            "desconto": Decimal("0"),
            "outras_despesas": Decimal("0"),
        }

    return {
        "frete": valor_tag(total_node, "vFrete"),
        "seguro": valor_tag(total_node, "vSeg"),
        "desconto": valor_tag(total_node, "vDesc"),
        "outras_despesas": valor_tag(total_node, "vOutro"),
    }


def localizar_produtos(root, impostos_selecionados):
    produtos = []
    totais_nfe = ler_totais_nfe(root)

    detalhes = []

    for elemento in root.iter():
        if nome_tag(elemento) != "det":
            continue

        produto_node = encontrar_filho(elemento, "prod")
        imposto_node = encontrar_filho(elemento, "imposto")

        if produto_node is None:
            continue

        detalhes.append({
            "produto_node": produto_node,
            "imposto_node": imposto_node
        })

    soma_produtos = sum(
        valor_tag(item["produto_node"], "vProd")
        for item in detalhes
    )

    if soma_produtos <= 0:
        soma_produtos = Decimal("1")

    # Verifica se os valores acessórios estão detalhados nos itens
    soma_frete_itens = sum(
        valor_tag(item["produto_node"], "vFrete")
        for item in detalhes
    )

    soma_seguro_itens = sum(
        valor_tag(item["produto_node"], "vSeg")
        for item in detalhes
    )

    soma_desconto_itens = sum(
        valor_tag(item["produto_node"], "vDesc")
        for item in detalhes
    )

    soma_outras_itens = sum(
        valor_tag(item["produto_node"], "vOutro")
        for item in detalhes
    )

    usar_frete_dos_itens = soma_frete_itens > 0
    usar_seguro_dos_itens = soma_seguro_itens > 0
    usar_desconto_dos_itens = soma_desconto_itens > 0
    usar_outras_dos_itens = soma_outras_itens > 0

    for item in detalhes:
        produto_node = item["produto_node"]
        imposto_node = item["imposto_node"]
        codigo = obter_texto(
            produto_node,
            "cProd",
            "Sem código"
        )

        descricao = obter_texto(
            produto_node,
            "xProd",
            "Produto sem descrição"
        )

        unidade = obter_texto(
            produto_node,
            "uCom",
            "UN"
        )

        quantidade = valor_tag(produto_node, "qCom")
        valor_produto = valor_tag(produto_node, "vProd")
        valor_unitario = valor_tag(produto_node, "vUnCom")

        if valor_unitario <= 0 and quantidade > 0:
            valor_unitario = valor_produto / quantidade

        proporcao = valor_produto / soma_produtos

        # Frete
        frete_item_xml = valor_tag(produto_node, "vFrete")

        if usar_frete_dos_itens:
            frete = frete_item_xml
        else:
            frete = totais_nfe["frete"] * proporcao

        # Seguro
        seguro_item_xml = valor_tag(produto_node, "vSeg")

        if usar_seguro_dos_itens:
            seguro = seguro_item_xml
        else:
            seguro = totais_nfe["seguro"] * proporcao

        # Desconto
        desconto_item_xml = valor_tag(produto_node, "vDesc")

        if usar_desconto_dos_itens:
            desconto = desconto_item_xml
        else:
            desconto = totais_nfe["desconto"] * proporcao

        # Outras despesas
        outras_item_xml = valor_tag(produto_node, "vOutro")

        if usar_outras_dos_itens:
            outras_despesas = outras_item_xml
        else:
            outras_despesas = totais_nfe["outras_despesas"] * proporcao

        impostos = {
            "ICMS": valor_tag(imposto_node, "vICMS"),
            "ICMS ST": valor_tag(imposto_node, "vICMSST"),
            "FCP": valor_tag(imposto_node, "vFCP"),
            "FCP ST": valor_tag(imposto_node, "vFCPST"),
            "IPI": valor_tag(imposto_node, "vIPI"),
            "II": valor_tag(imposto_node, "vII"),
            "PIS": valor_tag(imposto_node, "vPIS"),
            "COFINS": valor_tag(imposto_node, "vCOFINS"),
        }

        total_impostos_incluidos = sum(
            valor
            for nome, valor in impostos.items()
            if nome in impostos_selecionados
        )

        custo_final = (
            valor_produto
            + frete
            + seguro
            + outras_despesas
            + total_impostos_incluidos
            - desconto
        )

        custo_unitario_final = Decimal("0")

        if quantidade > 0:
            custo_unitario_final = custo_final / quantidade

        registro = {
            "Código": codigo,
            "Produto": descricao,
            "Unidade": unidade,
            "Quantidade": float(quantidade),
            "Valor dos produtos": float(valor_produto),
            "Custo unitário original": float(valor_unitario),
            "Frete": float(frete),
            "Seguro": float(seguro),
            "Desconto": float(desconto),
            "Outras despesas": float(outras_despesas),
            "ICMS": float(impostos["ICMS"]),
            "ICMS ST": float(impostos["ICMS ST"]),
            "FCP": float(impostos["FCP"]),
            "FCP ST": float(impostos["FCP ST"]),
            "IPI": float(impostos["IPI"]),
            "II": float(impostos["II"]),
            "PIS": float(impostos["PIS"]),
            "COFINS": float(impostos["COFINS"]),
            "Impostos incluídos": float(total_impostos_incluidos),
            "Custo final": float(custo_final),
            "Custo unitário final": float(custo_unitario_final),
        }

        produtos.append(registro)

    return produtos


def obter_chave_acesso(root):
    """
    Extrai a chave de acesso (44 dígitos) da NF-e, que é o
    identificador único de cada nota fiscal.
    """
    inf_nfe = encontrar_elemento(root, "infNFe")

    if inf_nfe is not None:
        id_attr = (inf_nfe.get("Id") or "").strip()
        chave = id_attr.replace("NFe", "").strip()

        if len(chave) == 44 and chave.isdigit():
            return chave

    ch_nfe = obter_texto(root, "chNFe")

    if len(ch_nfe) == 44 and ch_nfe.isdigit():
        return ch_nfe

    return None


def obter_metadados_nfe(root):
    """
    Extrai informações gerais da NF-e para exibir no histórico.
    """
    ide_node = encontrar_elemento(root, "ide")
    emit_node = encontrar_elemento(root, "emit")
    total_node = encontrar_elemento(root, "ICMSTot")

    numero = obter_texto(ide_node, "nNF", "")
    serie = obter_texto(ide_node, "serie", "")

    data_emissao = (
        obter_texto(ide_node, "dhEmi", "")
        or obter_texto(ide_node, "dEmi", "")
    )

    fornecedor = obter_texto(
        emit_node,
        "xNome",
        "Fornecedor não identificado"
    )

    cnpj_emit = obter_texto(emit_node, "CNPJ", "")

    valor_total = float(valor_tag(total_node, "vNF"))

    return {
        "numero": numero,
        "serie": serie,
        "data_emissao": data_emissao[:10] if data_emissao else "",
        "fornecedor": fornecedor,
        "cnpj_emit": cnpj_emit,
        "valor_total": round(valor_total, 2),
    }


def nome_arquivo_padronizado(chave, metadados):
    """
    Monta um nome de arquivo organizado: data_numero_chave.xml
    """
    numero = "".join(
        c for c in str(metadados.get("numero", "")) if c.isdigit()
    ) or "SN"

    data = metadados.get("data_emissao", "")
    data_compacta = data.replace("-", "") if data else "sem-data"

    return f"{data_compacta}_NFe{numero}_{chave}.xml"


def garantir_pasta_processados():
    os.makedirs(PASTA_XMLS_PROCESSADOS, exist_ok=True)


def carregar_indice():
    """
    Carrega o índice de XMLs já processados (chave -> metadados).
    """
    garantir_pasta_processados()

    if not os.path.exists(ARQUIVO_INDICE):
        return {}

    try:
        with open(ARQUIVO_INDICE, "r", encoding="utf-8") as arquivo_json:
            return json.load(arquivo_json)
    except (json.JSONDecodeError, OSError):
        return {}


def salvar_indice(indice):
    garantir_pasta_processados()

    with open(ARQUIVO_INDICE, "w", encoding="utf-8") as arquivo_json:
        json.dump(indice, arquivo_json, ensure_ascii=False, indent=2)


st.title("📦 Gestão de Produtos")
st.markdown(
    "<p style='color:#4A5A6A; font-size:1.05rem; margin-top:-0.8rem;'>"
    "Importe XMLs de NF-e, calcule custos e defina preços de revenda."
    "</p>",
    unsafe_allow_html=True,
)

st.sidebar.header("⚙️ Configurações")


arquivos = st.sidebar.file_uploader(
    "1. Escolha os arquivos XML",
    type=["xml"],
    accept_multiple_files=True
)

markup = st.sidebar.number_input(
    "2. Markup sobre o custo (%)",
    min_value=0.0,
    max_value=1000.0,
    value=60.0,
    step=1.0,
    format="%.2f"
)

st.sidebar.subheader("3. Impostos considerados no custo")

st.sidebar.caption(
    "Marque apenas os impostos que devem compor o custo do produto."
)

incluir_icms = st.sidebar.checkbox(
    "Incluir ICMS",
    value=False
)

incluir_icms_st = st.sidebar.checkbox(
    "Incluir ICMS-ST",
    value=True
)

incluir_fcp = st.sidebar.checkbox(
    "Incluir FCP",
    value=False
)

incluir_fcp_st = st.sidebar.checkbox(
    "Incluir FCP-ST",
    value=True
)

incluir_ipi = st.sidebar.checkbox(
    "Incluir IPI",
    value=True
)

incluir_ii = st.sidebar.checkbox(
    "Incluir II",
    value=True
)

incluir_pis = st.sidebar.checkbox(
    "Incluir PIS",
    value=False
)

incluir_cofins = st.sidebar.checkbox(
    "Incluir COFINS",
    value=False
)

impostos_selecionados = []

if incluir_icms:
    impostos_selecionados.append("ICMS")

if incluir_icms_st:
    impostos_selecionados.append("ICMS ST")

if incluir_fcp:
    impostos_selecionados.append("FCP")

if incluir_fcp_st:
    impostos_selecionados.append("FCP ST")

if incluir_ipi:
    impostos_selecionados.append("IPI")

if incluir_ii:
    impostos_selecionados.append("II")

if incluir_pis:
    impostos_selecionados.append("PIS")

if incluir_cofins:
    impostos_selecionados.append("COFINS")

st.sidebar.subheader("4. Outros custos")

custo_adicional_unitario = st.sidebar.number_input(
    "Custo adicional por unidade (R$)",
    min_value=0.0,
    value=0.0,
    step=0.01,
    format="%.2f",
    help=(
        "Use para embalagem, manuseio, comissão, "
        "mão de obra ou outro custo por unidade."
    )
)

indice = carregar_indice()

st.divider()
st.subheader("📁 Histórico de XMLs importados")

if not indice:
    st.caption(
        "Nenhum XML foi importado ainda. Envie arquivos abaixo para "
        "começar — cada nota processada com sucesso fica registrada "
        "aqui automaticamente."
    )
else:
    df_historico = pd.DataFrame(list(indice.values()))
    df_historico = df_historico.sort_values(
        "data_importacao",
        ascending=False
    )

    colunas_historico = {
        "numero": "Número",
        "serie": "Série",
        "data_emissao": "Data de emissão",
        "fornecedor": "Fornecedor",
        "cnpj_emit": "CNPJ emitente",
        "valor_total": "Valor total (R$)",
        "data_importacao": "Importado em",
        "arquivo_original": "Arquivo original",
    }

    colunas_presentes = [
        coluna
        for coluna in colunas_historico
        if coluna in df_historico.columns
    ]

    st.dataframe(
        df_historico[colunas_presentes].rename(
            columns=colunas_historico
        ),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Valor total (R$)": st.column_config.NumberColumn(
                format="R$ %.2f"
            ),
        },
    )

    with st.expander("🔍 Ver detalhes ou baixar um XML já importado"):
        opcoes = {
            chave: (
                f"NF-e {info.get('numero', '?')} "
                f"— {info.get('fornecedor', 'Fornecedor não identificado')} "
                f"({info.get('data_emissao', '?')})"
            )
            for chave, info in indice.items()
        }

        chave_escolhida = st.selectbox(
            "Selecione uma nota do histórico",
            options=list(opcoes.keys()),
            format_func=lambda chave: opcoes[chave],
        )

        if chave_escolhida:
            info_nota = indice[chave_escolhida]

            col_a, col_b = st.columns(2)

            with col_a:
                st.write(f"**Número:** {info_nota.get('numero', '')}")
                st.write(f"**Série:** {info_nota.get('serie', '')}")
                st.write(
                    f"**Data de emissão:** "
                    f"{info_nota.get('data_emissao', '')}"
                )
                st.write(
                    f"**Fornecedor:** {info_nota.get('fornecedor', '')}"
                )

            with col_b:
                st.write(f"**CNPJ emitente:** {info_nota.get('cnpj_emit', '')}")
                st.write(
                    f"**Valor total:** "
                    f"R$ {info_nota.get('valor_total', 0):,.2f}"
                )
                st.write(
                    f"**Importado em:** "
                    f"{info_nota.get('data_importacao', '')}"
                )
                st.write(f"**Chave de acesso:** {chave_escolhida}")

            caminho_arquivo_salvo = os.path.join(
                PASTA_XMLS_PROCESSADOS,
                info_nota.get("arquivo_salvo", "")
            )

            if os.path.exists(caminho_arquivo_salvo):
                with open(caminho_arquivo_salvo, "rb") as arquivo_bin:
                    st.download_button(
                        "⬇️ Baixar este XML novamente",
                        data=arquivo_bin.read(),
                        file_name=info_nota.get(
                            "arquivo_salvo", "nota.xml"
                        ),
                        mime="application/xml",
                        key=f"download_{chave_escolhida}",
                    )
            else:
                st.caption(
                    "O arquivo original não foi encontrado na pasta "
                    f"'{PASTA_XMLS_PROCESSADOS}'."
                )

st.divider()

if not arquivos:
    st.info(
        "Envie um ou mais arquivos XML na barra lateral para começar."
    )
    st.stop()

todos_produtos = []
erros = []
avisos_duplicados = []
indice_atualizado = False

for arquivo in arquivos:
    conteudo = arquivo.getvalue()

    try:
        root = ET.fromstring(conteudo)
    except ET.ParseError:
        erros.append(
            f"O arquivo {arquivo.name} não possui um XML válido."
        )
        continue
    except Exception as erro:
        erros.append(f"Erro ao processar {arquivo.name}: {erro}")
        continue

    chave_acesso = obter_chave_acesso(root)
    metadados_nota = obter_metadados_nfe(root)

    if chave_acesso and chave_acesso in indice:
        info_existente = indice[chave_acesso]
        avisos_duplicados.append(
            f"⚠️ **{arquivo.name}** já foi importado anteriormente "
            f"(NF-e nº {info_existente.get('numero', '?')}, "
            f"fornecedor {info_existente.get('fornecedor', '?')}, "
            f"importado em {info_existente.get('data_importacao', '?')}). "
            "Este arquivo foi ignorado para evitar duplicidade."
        )
        continue

    produtos = localizar_produtos(root, impostos_selecionados)

    if not produtos:
        erros.append(
            f"Nenhum produto foi encontrado em {arquivo.name}."
        )
        continue

    for produto in produtos:
        produto["Arquivo XML"] = arquivo.name

    todos_produtos.extend(produtos)

    if chave_acesso:
        garantir_pasta_processados()

        nome_salvo = nome_arquivo_padronizado(
            chave_acesso,
            metadados_nota
        )

        caminho_salvo = os.path.join(
            PASTA_XMLS_PROCESSADOS,
            nome_salvo
        )

        with open(caminho_salvo, "wb") as arquivo_salvo:
            arquivo_salvo.write(conteudo)

        indice[chave_acesso] = {
            "chave_acesso": chave_acesso,
            "numero": metadados_nota.get("numero", ""),
            "serie": metadados_nota.get("serie", ""),
            "data_emissao": metadados_nota.get("data_emissao", ""),
            "fornecedor": metadados_nota.get("fornecedor", ""),
            "cnpj_emit": metadados_nota.get("cnpj_emit", ""),
            "valor_total": metadados_nota.get("valor_total", 0),
            "arquivo_original": arquivo.name,
            "arquivo_salvo": nome_salvo,
            "data_importacao": datetime.now().strftime(
                "%d/%m/%Y %H:%M"
            ),
        }

        indice_atualizado = True

if indice_atualizado:
    salvar_indice(indice)

if avisos_duplicados:
    for aviso in avisos_duplicados:
        st.warning(aviso)

if erros:
    for erro in erros:
        st.warning(erro)

if not todos_produtos:
    st.error(
        "Nenhum produto novo foi encontrado nos arquivos enviados "
        "(ou todas as notas já haviam sido importadas antes)."
    )
    st.stop()

df = pd.DataFrame(todos_produtos)

st.divider()
st.subheader("🔢 Unidades reais por produto")

st.caption(
    "A quantidade do XML às vezes representa embalagens (caixa, fardo, "
    "pacote), não a unidade real vendida. Informe abaixo quantas "
    "unidades reais existem dentro de cada quantidade do XML para o "
    "custo e o preço por unidade saírem corretos. Deixe 1 se a "
    "quantidade do XML já é a unidade real."
)

# Correção 1: Criação de chave única combinando código do produto e nome do arquivo
df["ID_temp"] = df["Código"].astype(str) + "_" + df["Arquivo XML"].astype(str)

if "unidades_por_embalagem" not in st.session_state:
    st.session_state["unidades_por_embalagem"] = {}

df_editor_base = df[[
    "ID_temp",
    "Código",
    "Produto",
    "Unidade",
    "Quantidade",
    "Arquivo XML",
]].copy()

df_editor_base["Unidades por embalagem"] = df_editor_base["ID_temp"].map(
    lambda id_temp: st.session_state["unidades_por_embalagem"].get(
        id_temp, 1.0
    )
)

df_editado = st.data_editor(
    df_editor_base,
    use_container_width=True,
    hide_index=True,
    disabled=[
        "ID_temp",
        "Código",
        "Produto",
        "Unidade",
        "Quantidade",
        "Arquivo XML",
    ],
    column_config={
        "ID_temp": None,
        "Unidades por embalagem": st.column_config.NumberColumn(
            "Unidades reais por embalagem",
            help=(
                "Ex.: se a Quantidade do XML é 1 (uma caixa) e a caixa "
                "tem 12 peças, coloque 12 aqui."
            ),
            min_value=0.01,
            step=1.0,
            format="%.2f",
        ),
    },
    key="editor_unidades_por_embalagem",
)

# Correção 2: Atualização do dicionário sem loop for (mais performance)
novas_unidades = df_editado.set_index("ID_temp")["Unidades por embalagem"].to_dict()
st.session_state["unidades_por_embalagem"].update(novas_unidades)

df["Unidades por embalagem"] = df["ID_temp"].map(
    lambda id_temp: st.session_state["unidades_por_embalagem"].get(
        id_temp, 1.0
    )
)

df["Unidades por embalagem"] = df["Unidades por embalagem"].fillna(1.0)
df.loc[df["Unidades por embalagem"] <= 0, "Unidades por embalagem"] = 1.0

df["Quantidade real"] = (
    df["Quantidade"] * df["Unidades por embalagem"]
)

df["Custo adicional"] = (
    df["Quantidade real"] * custo_adicional_unitario
)

df["Custo final"] = (
    df["Custo final"]
    + df["Custo adicional"]
)

df["Custo unitário final"] = (
    df["Custo final"] / df["Quantidade real"].replace(0, 1)
)

fator_markup = 1 + (markup / 100)

df["Preço de revenda unitário"] = (
    df["Custo unitário final"] * fator_markup
)

df["Total de revenda"] = (
    df["Quantidade real"]
    * df["Preço de revenda unitário"]
)

df["Lucro unitário"] = (
    df["Preço de revenda unitário"]
    - df["Custo unitário final"]
)

df["Lucro total"] = (
    df["Quantidade real"] * df["Lucro unitário"]
)

df = df.drop(columns=["ID_temp"])

colunas_monetarias = [
    "Valor dos produtos",
    "Custo unitário original",
    "Frete",
    "Seguro",
    "Desconto",
    "Outras despesas",
    "ICMS",
    "ICMS ST",
    "FCP",
    "FCP ST",
    "IPI",
    "II",
    "PIS",
    "COFINS",
    "Impostos incluídos",
    "Custo adicional",
    "Custo final",
    "Custo unitário final",
    "Preço de revenda unitário",
    "Total de revenda",
    "Lucro unitário",
    "Lucro total",
]

for coluna in colunas_monetarias:
    if coluna in df.columns:
        df[coluna] = df[coluna].round(2)

st.success(
    f"{len(df)} produto(s) processado(s) com sucesso."
)

st.divider()
st.subheader("📊 Resumo financeiro")

custo_total = df["Custo final"].sum()
impostos_total = df["Impostos incluídos"].sum()
revenda_total = df["Total de revenda"].sum()
lucro_total = df["Lucro total"].sum()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Custo total",
        f"R$ {custo_total:,.2f}"
    )

with col2:
    st.metric(
        "Impostos no custo",
        f"R$ {impostos_total:,.2f}"
    )

with col3:
    st.metric(
        "Total de revenda",
        f"R$ {revenda_total:,.2f}"
    )

with col4:
    st.metric(
        "Lucro estimado",
        f"R$ {lucro_total:,.2f}"
    )

colunas_tabela = [
    "Código",
    "Produto",
    "Unidade",
    "Quantidade",
    "Unidades por embalagem",
    "Quantidade real",
    "Valor dos produtos",
    "Frete",
    "Seguro",
    "Desconto",
    "Impostos incluídos",
    "Custo adicional",
    "Custo final",
    "Custo unitário final",
    "Preço de revenda unitário",
    "Total de revenda",
    "Lucro unitário",
    "Lucro total",
    "Arquivo XML",
]

st.divider()
st.subheader("📋 Produtos processados")

# Correção 3: Formatação monetária padronizada em todos os .NumberColumn ("R$ %.2f")
st.dataframe(
    df[colunas_tabela],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Quantidade": st.column_config.NumberColumn(
            format="%.2f"
        ),
        "Unidades por embalagem": st.column_config.NumberColumn(
            format="%.2f"
        ),
        "Quantidade real": st.column_config.NumberColumn(
            format="%.2f"
        ),
        "Valor dos produtos": st.column_config.NumberColumn(
            format="R$ %.2f"
        ),
        "Frete": st.column_config.NumberColumn(
            format="R$ %.2f"
        ),
        "Seguro": st.column_config.NumberColumn(
            format="R$ %.2f"
        ),
        "Desconto": st.column_config.NumberColumn(
            format="R$ %.2f"
        ),
        "Impostos incluídos": st.column_config.NumberColumn(
            format="R$ %.2f"
        ),
        "Custo adicional": st.column_config.NumberColumn(
            format="R$ %.2f"
        ),
        "Custo final": st.column_config.NumberColumn(
            format="R$ %.2f"
        ),
        "Custo unitário final": st.column_config.NumberColumn(
            format="R$ %.2f"
        ),
        "Preço de revenda unitário": st.column_config.NumberColumn(
            format="R$ %.2f"
        ),
        "Total de revenda": st.column_config.NumberColumn(
            format="R$ %.2f"
        ),
        "Lucro unitário": st.column_config.NumberColumn(
            format="R$ %.2f"
        ),
        "Lucro total": st.column_config.NumberColumn(
            format="R$ %.2f"
        ),
    }
)

st.divider()
st.subheader("📈 Gráfico de análise")

tipo_grafico = st.selectbox(
    "Escolha o tipo de gráfico",
    [
        "Total de revenda",
        "Quantidade real",
        "Lucro total",
        "Custo final",
    ]
)

agrupado = df.groupby(
    "Produto",
    as_index=False
).agg({
    "Quantidade real": "sum",
    "Total de revenda": "sum",
    "Lucro total": "sum",
    "Custo final": "sum",
})

if tipo_grafico == "Total de revenda":
    coluna_valor = "Total de revenda"

elif tipo_grafico == "Quantidade real":
    coluna_valor = "Quantidade real"

elif tipo_grafico == "Lucro total":
    coluna_valor = "Lucro total"

else:
    coluna_valor = "Custo final"


fig = px.pie(
    agrupado,
    names="Produto",
    values=coluna_valor,
    hole=0.3,
    title=f"Distribuição por {tipo_grafico}"
)

fig.update_traces(
    textposition="inside",
    textinfo="percent+label"
)

fig.update_layout(
    height=700,
    font=dict(size=16),
    title_font_size=22,
    legend=dict(font=dict(size=14)),
)

st.plotly_chart(
    fig,
    use_container_width=True
)

st.divider()
st.subheader("📤 Exportação")

csv_data = df.to_csv(
    index=False,
    sep=";",
    encoding="utf-8-sig"
)
st.download_button(
    label="⬇️ Baixar CSV",
    data=csv_data,
    file_name="produtos_precificados.csv",
    mime="text/csv"
)

```