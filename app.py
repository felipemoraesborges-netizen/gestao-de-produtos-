
import os
import sqlite3
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional
from defusedxml import ElementTree as ET
import pandas as pd
import plotly.express as px
import streamlit as st


DB_PATH = "banco_notas.db"
PASTA_XMLS_PROCESSADOS = "xmls_processados"

def inicializar_banco() -> None:
    
    os.makedirs(PASTA_XMLS_PROCESSADOS, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_nfe (
            chave_acesso TEXT PRIMARY KEY,
            numero TEXT,
            serie TEXT,
            data_emissao TEXT,
            fornecedor TEXT,
            cnpj_emit TEXT,
            valor_total REAL,
            arquivo_original TEXT,
            arquivo_salvo TEXT,
            data_importacao TEXT
        )
    """)
    conn.commit()
    conn.close()

def carregar_indice() -> Dict[str, Dict[str, Any]]:
    """Carrega o histórico do SQLite em formato de dicionário."""
    inicializar_banco()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM historico_nfe")
    linhas = cursor.fetchall()
    conn.close()
    return {linha["chave_acesso"]: dict(linha) for linha in linhas}

def salvar_nota(dados: Dict[str, Any]) -> None:
    """Salva uma nova nota fiscal no banco de dados."""
    inicializar_banco()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO historico_nfe 
        (chave_acesso, numero, serie, data_emissao, fornecedor, cnpj_emit, valor_total, arquivo_original, arquivo_salvo, data_importacao)
        VALUES (:chave_acesso, :numero, :serie, :data_emissao, :fornecedor, :cnpj_emit, :valor_total, :arquivo_original, :arquivo_salvo, :data_importacao)
    """, dados)
    conn.commit()
    conn.close()

def nome_tag(elemento: ET.Element) -> str:
    return elemento.tag.split("}")[-1]

def encontrar_elemento(elemento_pai: Optional[ET.Element], nome: str) -> Optional[ET.Element]:
    if elemento_pai is None:
        return None
    for elemento in elemento_pai.iter():
        if nome_tag(elemento) == nome:
            return elemento
    return None

def encontrar_filho(elemento_pai: Optional[ET.Element], nome: str) -> Optional[ET.Element]:
    if elemento_pai is None:
        return None
    for filho in list(elemento_pai):
        if nome_tag(filho) == nome:
            return filho
    return None

def obter_texto(elemento_pai: Optional[ET.Element], nome: str, padrao: str = "") -> str:
    elemento = encontrar_elemento(elemento_pai, nome)
    if elemento is not None and elemento.text:
        return elemento.text.strip()
    return padrao

def converter_decimal(valor: Any, padrao: Decimal = Decimal("0")) -> Decimal:
    if valor is None:
        return padrao
    texto = str(valor).strip()
    if not texto:
        return padrao
    try:
        return Decimal(texto.replace(",", "."))
    except InvalidOperation:
        return padrao

def valor_tag(elemento_pai: Optional[ET.Element], nome: str) -> Decimal:
    elemento = encontrar_elemento(elemento_pai, nome)
    if elemento is not None and elemento.text:
        return converter_decimal(elemento.text)
    return Decimal("0")

def ler_totais_nfe(root: ET.Element) -> Dict[str, Decimal]:
    total_node = encontrar_elemento(root, "ICMSTot")
    if total_node is None:
        return {
            "frete": Decimal("0"), "seguro": Decimal("0"),
            "desconto": Decimal("0"), "outras_despesas": Decimal("0"),
        }
    return {
        "frete": valor_tag(total_node, "vFrete"),
        "seguro": valor_tag(total_node, "vSeg"),
        "desconto": valor_tag(total_node, "vDesc"),
        "outras_despesas": valor_tag(total_node, "vOutro"),
    }

def localizar_produtos(root: ET.Element, impostos_selecionados: List[str]) -> List[Dict[str, Any]]:
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
        detalhes.append({"produto_node": produto_node, "imposto_node": imposto_node})

    soma_produtos = sum(valor_tag(item["produto_node"], "vProd") for item in detalhes)
    if soma_produtos <= 0:
        soma_produtos = Decimal("1")

    soma_frete_itens = sum(valor_tag(item["produto_node"], "vFrete") for item in detalhes)
    soma_seguro_itens = sum(valor_tag(item["produto_node"], "vSeg") for item in detalhes)
    soma_desconto_itens = sum(valor_tag(item["produto_node"], "vDesc") for item in detalhes)
    soma_outras_itens = sum(valor_tag(item["produto_node"], "vOutro") for item in detalhes)

    usar_frete_dos_itens = soma_frete_itens > 0
    usar_seguro_dos_itens = soma_seguro_itens > 0
    usar_desconto_dos_itens = soma_desconto_itens > 0
    usar_outras_dos_itens = soma_outras_itens > 0

    for item in detalhes:
        produto_node = item["produto_node"]
        imposto_node = item["imposto_node"]
        
        codigo = obter_texto(produto_node, "cProd", "Sem código")
        descricao = obter_texto(produto_node, "xProd", "Produto sem descrição")
        unidade = obter_texto(produto_node, "uCom", "UN")
        
        quantidade = valor_tag(produto_node, "qCom")
        valor_produto = valor_tag(produto_node, "vProd")
        valor_unitario = valor_tag(produto_node, "vUnCom")

        if valor_unitario <= 0 and quantidade > 0:
            valor_unitario = valor_produto / quantidade

        proporcao = valor_produto / soma_produtos

        frete = valor_tag(produto_node, "vFrete") if usar_frete_dos_itens else totais_nfe["frete"] * proporcao
        seguro = valor_tag(produto_node, "vSeg") if usar_seguro_dos_itens else totais_nfe["seguro"] * proporcao
        desconto = valor_tag(produto_node, "vDesc") if usar_desconto_dos_itens else totais_nfe["desconto"] * proporcao
        outras_despesas = valor_tag(produto_node, "vOutro") if usar_outras_dos_itens else totais_nfe["outras_despesas"] * proporcao

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
            valor for nome, valor in impostos.items() if nome in impostos_selecionados
        )

        custo_final = (valor_produto + frete + seguro + outras_despesas + total_impostos_incluidos - desconto)
        custo_unitario_final = custo_final / quantidade if quantidade > 0 else Decimal("0")

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

def obter_chave_acesso(root: ET.Element) -> Optional[str]:
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

def obter_metadados_nfe(root: ET.Element) -> Dict[str, Any]:
    ide_node = encontrar_elemento(root, "ide")
    emit_node = encontrar_elemento(root, "emit")
    total_node = encontrar_elemento(root, "ICMSTot")

    numero = obter_texto(ide_node, "nNF", "")
    serie = obter_texto(ide_node, "serie", "")
    data_emissao = obter_texto(ide_node, "dhEmi", "") or obter_texto(ide_node, "dEmi", "")
    fornecedor = obter_texto(emit_node, "xNome", "Fornecedor não identificado")
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

def nome_arquivo_padronizado(chave: str, metadados: Dict[str, Any]) -> str:
    numero = "".join(c for c in str(metadados.get("numero", "")) if c.isdigit()) or "SN"
    data = metadados.get("data_emissao", "")
    data_compacta = data.replace("-", "") if data else "sem-data"
    return f"{data_compacta}_NFe{numero}_{chave}.xml"

def processar_metricas_revenda(df: pd.DataFrame, unidades_por_embalagem_dict: Dict[str, float], custo_adicional_unitario: float, markup: float) -> pd.DataFrame:
    df["Unidades por embalagem"] = df["ID_temp"].map(
        lambda id_temp: unidades_por_embalagem_dict.get(id_temp, 1.0)
    )
    df["Unidades por embalagem"] = df["Unidades por embalagem"].fillna(1.0)
    df.loc[df["Unidades por embalagem"] <= 0, "Unidades por embalagem"] = 1.0

    df["Quantidade real"] = df["Quantidade"] * df["Unidades por embalagem"]
    df["Custo adicional"] = df["Quantidade real"] * custo_adicional_unitario
    df["Custo final"] = df["Custo final"] + df["Custo adicional"]
    df["Custo unitário final"] = df["Custo final"] / df["Quantidade real"].replace(0, 1)

    fator_markup = 1 + (markup / 100)
    df["Preço de revenda unitário"] = df["Custo unitário final"] * fator_markup
    df["Total de revenda"] = df["Quantidade real"] * df["Preço de revenda unitário"]
    df["Lucro unitário"] = df["Preço de revenda unitário"] - df["Custo unitário final"]
    df["Lucro total"] = df["Quantidade real"] * df["Lucro unitário"]

    colunas_monetarias = [
        "Valor dos produtos", "Custo unitário original", "Frete", "Seguro",
        "Desconto", "Outras despesas", "ICMS", "ICMS ST", "FCP", "FCP ST",
        "IPI", "II", "PIS", "COFINS", "Impostos incluídos", "Custo adicional",
        "Custo final", "Custo unitário final", "Preço de revenda unitário",
        "Total de revenda", "Lucro unitário", "Lucro total",
    ]
    
    for coluna in colunas_monetarias:
        if coluna in df.columns:
            df[coluna] = df[coluna].round(2)

    return df

st.set_page_config(page_title="Gestão de Produtos", page_icon="📦", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    html, body, [class*="css"] { font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; }
    .block-container { padding-top: 2rem; padding-bottom: 3rem; }
    h1 { color: #1B4F8C; font-weight: 700; border-bottom: 3px solid #1B4F8C; padding-bottom: 0.5rem; margin-bottom: 0.6rem; }
    h2, h3 { color: #1B4F8C; font-weight: 600; margin-top: 1.8rem; }
    [data-testid="stCaptionContainer"], .stCaption, small { color: #33475B !important; opacity: 1 !important; font-size: 0.92rem !important; }
    section[data-testid="stSidebar"] { background-color: #0E2A47; }
    section[data-testid="stSidebar"] * { color: #FFFFFF !important; opacity: 1 !important; }
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"], section[data-testid="stSidebar"] .stCaption, section[data-testid="stSidebar"] small { color: #C7D6E8 !important; opacity: 1 !important; }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 { color: #FFFFFF !important; border-bottom: none; }
    section[data-testid="stSidebar"] .stCheckbox { background-color: rgba(255, 255, 255, 0.06); border-radius: 6px; padding: 2px 6px; margin-bottom: 2px; }
    div[data-testid="stMetric"] { background-color: #F0F4F8; border: 1px solid #D6E0EA; border-left: 5px solid #1B4F8C; border-radius: 8px; padding: 1rem 1.2rem; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06); }
    div[data-testid="stMetricLabel"] { color: #4A5A6A; font-weight: 600; }
    div[data-testid="stMetricValue"] { color: #1B4F8C; font-weight: 700; }
    .stButton button, .stDownloadButton button { background-color: #1B4F8C; color: white; border-radius: 6px; border: none; font-weight: 600; padding: 0.5rem 1.2rem; }
    .stButton button:hover, .stDownloadButton button:hover { background-color: #163F70; color: white; }
    div[data-testid="stAlert"] { border-radius: 8px; }
    div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] { border: 1px solid #D6E0EA; border-radius: 8px; overflow: hidden; }
    hr { border-top: 1px solid #D6E0EA; }
    </style>
""", unsafe_allow_html=True) 

st.title("📦 Gestão de Produtos")
st.markdown("<p style='color:#4A5A6A; font-size:1.05rem; margin-top:-0.8rem;'>Importe XMLs de NF-e, calcule custos e defina preços de revenda.</p>", unsafe_allow_html=True)


st.sidebar.header("⚙️ Configurações")
arquivos = st.sidebar.file_uploader("1. Escolha os arquivos XML", type=["xml"], accept_multiple_files=True)
markup = st.sidebar.number_input("2. Markup sobre o custo (%)", min_value=0.0, max_value=1000.0, value=60.0, step=1.0, format="%.2f")

st.sidebar.subheader("3. Impostos considerados no custo")
impostos_opcoes = {
    "ICMS": st.sidebar.checkbox("Incluir ICMS", value=False),
    "ICMS ST": st.sidebar.checkbox("Incluir ICMS-ST", value=True),
    "FCP": st.sidebar.checkbox("Incluir FCP", value=False),
    "FCP ST": st.sidebar.checkbox("Incluir FCP-ST", value=True),
    "IPI": st.sidebar.checkbox("Incluir IPI", value=True),
    "II": st.sidebar.checkbox("Incluir II", value=True),
    "PIS": st.sidebar.checkbox("Incluir PIS", value=False),
    "COFINS": st.sidebar.checkbox("Incluir COFINS", value=False)
}
impostos_selecionados = [imp for imp, ativo in impostos_opcoes.items() if ativo]

st.sidebar.subheader("4. Outros custos")
custo_adicional_unitario = st.sidebar.number_input("Custo adicional por unidade (R$)", min_value=0.0, value=0.0, step=0.01)


indice = carregar_indice()
st.divider()
st.subheader("📁 Histórico de XMLs importados")

if not indice:
    st.caption("Nenhum XML foi importado ainda.")
else:
    df_historico = pd.DataFrame(list(indice.values())).sort_values("data_importacao", ascending=False)
    st.dataframe(df_historico, use_container_width=True, hide_index=True)


@st.cache_data(show_spinner="Processando XMLs...")
def processar_arquivos_upload(dados_arquivos: list, impostos_ativos: list, dict_indice: dict):
    todos_produtos = []
    avisos, erros = [], []
    novas_notas = []
    
    for nome_arquivo, conteudo_bytes in dados_arquivos:
        try:
            root = ET.fromstring(conteudo_bytes)
        except Exception as erro:
            erros.append(f"Erro ao processar {nome_arquivo}: {erro}")
            continue

        chave_acesso = obter_chave_acesso(root)
        metadados_nota = obter_metadados_nfe(root)

        if chave_acesso and chave_acesso in dict_indice:
            avisos.append(f"⚠️ **{nome_arquivo}** já foi importado anteriormente.")
            continue

        produtos = localizar_produtos(root, impostos_ativos)
        if not produtos:
            erros.append(f"Nenhum produto foi encontrado em {nome_arquivo}.")
            continue

        for produto in produtos:
            produto["Arquivo XML"] = nome_arquivo

        todos_produtos.extend(produtos)

        if chave_acesso:
            nome_salvo = nome_arquivo_padronizado(chave_acesso, metadados_nota)
            caminho_salvo = os.path.join(PASTA_XMLS_PROCESSADOS, nome_salvo)
            with open(caminho_salvo, "wb") as arquivo_salvo:
                arquivo_salvo.write(conteudo_bytes)
                
            nova_nota = {
                "chave_acesso": chave_acesso, "numero": metadados_nota.get("numero", ""),
                "serie": metadados_nota.get("serie", ""), "data_emissao": metadados_nota.get("data_emissao", ""),
                "fornecedor": metadados_nota.get("fornecedor", ""), "cnpj_emit": metadados_nota.get("cnpj_emit", ""),
                "valor_total": metadados_nota.get("valor_total", 0), "arquivo_original": nome_arquivo,
                "arquivo_salvo": nome_salvo, "data_importacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
            }
            novas_notas.append(nova_nota)
            
    return todos_produtos, novas_notas, avisos, erros

st.divider()
if not arquivos:
    st.info("Envie um ou mais arquivos XML na barra lateral para começar.")
    st.stop()

arquivos_para_cache = [(arq.name, arq.getvalue()) for arq in arquivos]
produtos_extraidos, notas_para_salvar, avisos_gerados, erros_gerados = processar_arquivos_upload(
    arquivos_para_cache, impostos_selecionados, indice
)

for nota in notas_para_salvar:
    salvar_nota(nota)

for aviso in avisos_gerados: st.warning(aviso)
for erro in erros_gerados: st.warning(erro)

if not produtos_extraidos:
    st.error("Nenhum produto novo foi encontrado nos arquivos enviados.")
    st.stop()

df = pd.DataFrame(produtos_extraidos)

st.divider()
st.subheader("🔢 Unidades reais por produto")

df["ID_temp"] = df["Código"].astype(str) + "_" + df["Arquivo XML"].astype(str)

if "unidades_por_embalagem" not in st.session_state:
    st.session_state["unidades_por_embalagem"] = {}

df_editor_base = df[["ID_temp", "Código", "Produto", "Unidade", "Quantidade", "Arquivo XML"]].copy()
df_editor_base["Unidades por embalagem"] = df_editor_base["ID_temp"].map(
    lambda id_temp: st.session_state["unidades_por_embalagem"].get(id_temp, 1.0)
)

df_editado = st.data_editor(
    df_editor_base, use_container_width=True, hide_index=True,
    disabled=["ID_temp", "Código", "Produto", "Unidade", "Quantidade", "Arquivo XML"],
    key="editor_unidades_por_embalagem",
)

novas_unidades = df_editado.set_index("ID_temp")["Unidades por embalagem"].to_dict()
st.session_state["unidades_por_embalagem"].update(novas_unidades)

df = processar_metricas_revenda(df, st.session_state["unidades_por_embalagem"], custo_adicional_unitario, markup)
df = df.drop(columns=["ID_temp"])

st.success(f"{len(df)} produto(s) processado(s) com sucesso.")

st.divider()
st.subheader("📋 Produtos processados")
st.dataframe(df, use_container_width=True, hide_index=True)
