import os
import sqlite3
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional
from defusedxml import ElementTree as ET
from xml.etree.ElementTree import Element
import pandas as pd
import plotly.express as px
import streamlit as st

import auth
import security

DB_PATH = "banco_notas.db"
PASTA_XMLS_PROCESSADOS = "xmls_processados"


def inicializar_banco() -> None:
    """Inicializa as pastas, tabelas de notas e usuários."""
    os.makedirs(PASTA_XMLS_PROCESSADOS, exist_ok=True)
    conn = security.get_db_connection(DB_PATH)
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
            data_importacao TEXT,
            usuario_id INTEGER
        )
    """)
    # Garante migração da coluna usuario_id caso a tabela já existisse antes
    cursor.execute("PRAGMA table_info(historico_nfe)")
    colunas = [col[1] for col in cursor.fetchall()]
    if "usuario_id" not in colunas:
        cursor.execute("ALTER TABLE historico_nfe ADD COLUMN usuario_id INTEGER")

    # Tabela para configurações de cálculo por nota (markup, impostos, etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes_nota (
            chave_acesso TEXT PRIMARY KEY,
            markup REAL DEFAULT 60.0,
            custo_adicional REAL DEFAULT 0.0,
            impostos TEXT DEFAULT '[]',
            unidades_por_embalagem TEXT DEFAULT '{}',
            atualizado_em TEXT
        )
    """)

    conn.commit()
    conn.close()

    # Garante a tabela de usuários
    auth.inicializar_tabela_usuarios(DB_PATH)


def carregar_indice(usuario_id: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
    """Carrega o histórico do SQLite em formato de dicionário."""
    inicializar_banco()
    conn = security.get_db_connection(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if usuario_id is not None:
        cursor.execute("""
            SELECT * FROM historico_nfe 
            WHERE usuario_id = ? OR usuario_id IS NULL 
            ORDER BY data_importacao DESC
        """, (usuario_id,))
    else:
        cursor.execute("SELECT * FROM historico_nfe ORDER BY data_importacao DESC")
    linhas = cursor.fetchall()
    conn.close()
    return {linha["chave_acesso"]: dict(linha) for linha in linhas}


def salvar_nota(dados: Dict[str, Any]) -> None:
    """Salva uma nova nota fiscal no banco de dados."""
    inicializar_banco()
    conn = security.get_db_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO historico_nfe 
        (chave_acesso, numero, serie, data_emissao, fornecedor, cnpj_emit, valor_total, arquivo_original, arquivo_salvo, data_importacao, usuario_id)
        VALUES (:chave_acesso, :numero, :serie, :data_emissao, :fornecedor, :cnpj_emit, :valor_total, :arquivo_original, :arquivo_salvo, :data_importacao, :usuario_id)
    """, dados)
    conn.commit()
    conn.close()


def salvar_config_nota(chave_acesso: str, markup: float, custo_adicional: float,
                       impostos: List[str], unidades_por_embalagem: Dict[str, float]) -> None:
    """Salva as configurações de cálculo de uma nota específica."""
    import json
    inicializar_banco()
    conn = security.get_db_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO configuracoes_nota
        (chave_acesso, markup, custo_adicional, impostos, unidades_por_embalagem, atualizado_em)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        chave_acesso,
        markup,
        custo_adicional,
        json.dumps(impostos),
        json.dumps(unidades_por_embalagem),
        datetime.now().strftime("%d/%m/%Y %H:%M"),
    ))
    conn.commit()
    conn.close()


def carregar_config_nota(chave_acesso: str, defaults: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Carrega as configurações salvas de uma nota. Retorna defaults se não houver registro."""
    import json
    inicializar_banco()
    conn = security.get_db_connection(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM configuracoes_nota WHERE chave_acesso = ?", (chave_acesso,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "markup": row["markup"],
            "custo_adicional": row["custo_adicional"],
            "impostos": json.loads(row["impostos"]),
            "unidades_por_embalagem": json.loads(row["unidades_por_embalagem"]),
            "atualizado_em": row["atualizado_em"],
        }
    # Sem registro salvo — usa defaults do usuário ou valores padrão
    d = defaults or {}
    return {
        "markup": d.get("markup_padrao", 60.0),
        "custo_adicional": d.get("custo_adicional_padrao", 0.0),
        "impostos": d.get("impostos_padrao", ["ICMS ST", "FCP ST", "IPI", "II"]),
        "unidades_por_embalagem": {},
        "atualizado_em": None,
    }


def carregar_produtos_da_nota(arquivo_salvo: str, impostos_selecionados: List[str]) -> List[Dict[str, Any]]:
    """Relê o XML salvo em xmls_processados/ e retorna lista de produtos brutos."""
    caminho = os.path.join(PASTA_XMLS_PROCESSADOS, arquivo_salvo)
    if not os.path.exists(caminho):
        return []
    try:
        root = ET.parse(caminho).getroot()
        return localizar_produtos(root, impostos_selecionados)
    except Exception:
        return []


def nome_tag(elemento: Element) -> str:
    return elemento.tag.split("}")[-1]


def encontrar_elemento(elemento_pai: Optional[Element], nome: str) -> Optional[Element]:
    if elemento_pai is None:
        return None
    for elemento in elemento_pai.iter():
        if nome_tag(elemento) == nome:
            return elemento
    return None


def encontrar_filho(elemento_pai: Optional[Element], nome: str) -> Optional[Element]:
    if elemento_pai is None:
        return None
    for filho in list(elemento_pai):
        if nome_tag(filho) == nome:
            return filho
    return None


def obter_texto(elemento_pai: Optional[Element], nome: str, padrao: str = "") -> str:
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


def valor_tag(elemento_pai: Optional[Element], nome: str) -> Decimal:
    elemento = encontrar_elemento(elemento_pai, nome)
    if elemento is not None and elemento.text:
        return converter_decimal(elemento.text)
    return Decimal("0")


def ler_totais_nfe(root: Element) -> Dict[str, Decimal]:
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


def localizar_produtos(root: Element, impostos_selecionados: List[str]) -> List[Dict[str, Any]]:
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


def obter_chave_acesso(root: Element) -> Optional[str]:
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


def obter_metadados_nfe(root: Element) -> Dict[str, Any]:
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


def processar_metricas_revenda(
    df: pd.DataFrame,
    unidades_por_embalagem_dict: Dict[str, float],
    custo_adicional_unitario: float,
    markup: float,
) -> pd.DataFrame:
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


# --- Configuração do Streamlit ---
st.set_page_config(
    page_title="Gestão de Produtos • ERP & Precificação",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

    /* Reset e Tipografia Global */
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Fundo Temático Principal com Mesh Gradient Tecnológico */
    .stApp {
        background-color: #F8FAFC !important;
        background-image: 
            radial-gradient(at 0% 0%, rgba(37, 99, 235, 0.08) 0px, transparent 45%),
            radial-gradient(at 100% 0%, rgba(14, 165, 233, 0.07) 0px, transparent 40%),
            radial-gradient(at 50% 100%, rgba(99, 102, 241, 0.06) 0px, transparent 50%),
            radial-gradient(rgba(15, 23, 42, 0.05) 1px, transparent 1px) !important;
        background-size: 100% 100%, 100% 100%, 100% 100%, 24px 24px !important;
        background-attachment: fixed !important;
    }

    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 3.5rem;
        max-width: 1400px;
    }

    /* Títulos e Tipografia */
    h1 {
        color: #0F2744 !important;
        font-weight: 800 !important;
        font-size: 1.85rem !important;
        letter-spacing: -0.02em !important;
        margin-bottom: 0.4rem !important;
    }
    h2, h3 {
        color: #1E3A8A !important;
        font-weight: 700 !important;
        letter-spacing: -0.01em !important;
    }
    p, span, label {
        color: #334155;
    }
    [data-testid="stCaptionContainer"], .stCaption, small {
        color: #64748B !important;
        font-size: 0.88rem !important;
    }

    /* Sidebar Temática Escura e Moderna */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #07152B 0%, #0A1E38 50%, #0E2A4E 100%) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 4px 0 24px rgba(0, 0, 0, 0.25);
    }
    section[data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] small {
        color: #94A3B8 !important;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #FFFFFF !important;
        border-bottom: none !important;
        font-weight: 700 !important;
    }

    /* Inputs na Sidebar */
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea,
    section[data-testid="stSidebar"] [data-baseweb="input"] input,
    section[data-testid="stSidebar"] [data-baseweb="base-input"] input,
    section[data-testid="stSidebar"] [data-testid="stNumberInput"] input {
        background-color: rgba(255, 255, 255, 0.12) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.22) !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
    }
    section[data-testid="stSidebar"] input:focus,
    section[data-testid="stSidebar"] [data-baseweb="input"]:focus-within {
        border-color: #38BDF8 !important;
        box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.25) !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="input"],
    section[data-testid="stSidebar"] [data-baseweb="base-input"] {
        background-color: transparent !important;
        border: none !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        background-color: rgba(255, 255, 255, 0.08) !important;
        border: 1.5px dashed rgba(255, 255, 255, 0.3) !important;
        border-radius: 12px !important;
        padding: 1rem !important;
        transition: all 0.2s ease !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]:hover {
        background-color: rgba(255, 255, 255, 0.14) !important;
        border-color: #38BDF8 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {
        background: linear-gradient(135deg, #2563EB, #0284C7) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    section[data-testid="stSidebar"] .stCheckbox {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 4px 10px;
        margin-bottom: 4px;
        transition: background 0.15s ease;
    }
    section[data-testid="stSidebar"] .stCheckbox:hover {
        background-color: rgba(255, 255, 255, 0.1);
    }
    section[data-testid="stSidebar"] [data-baseweb="select"] > div {
        background-color: rgba(255, 255, 255, 0.12) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        border-radius: 8px !important;
    }

    /* Cards de Métricas Premium */
    div[data-testid="stMetric"] {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-top: 4px solid #2563EB !important;
        border-radius: 12px !important;
        padding: 1.1rem 1.3rem !important;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04) !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(37, 99, 235, 0.08) !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #64748B !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
    }
    div[data-testid="stMetricValue"] {
        color: #0F172A !important;
        font-weight: 800 !important;
        font-size: 1.65rem !important;
    }

    /* Botões Modernos com Gradiente */
    .stButton button, .stDownloadButton button {
        background: linear-gradient(135deg, #1E40AF 0%, #0284C7 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 9px !important;
        font-weight: 600 !important;
        padding: 0.55rem 1.4rem !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.25) !important;
        transition: all 0.2s ease !important;
    }
    .stButton button:hover, .stDownloadButton button:hover {
        background: linear-gradient(135deg, #1D4ED8 0%, #0369A1 100%) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 16px rgba(2, 132, 199, 0.35) !important;
        color: #FFFFFF !important;
    }

    /* Tabelas e Dataframes */
    div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
        background: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 12px !important;
        overflow: hidden !important;
        box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04) !important;
    }

    /* Abas / Tabs Estilizadas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(241, 245, 249, 0.8);
        padding: 6px;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 18px;
        font-weight: 600;
        color: #475569;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background: #FFFFFF !important;
        color: #1E40AF !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    }

    /* Componentes Customizados */
    .user-profile-badge {
        background: linear-gradient(135deg, rgba(255,255,255,0.15) 0%, rgba(255,255,255,0.05) 100%);
        border: 1px solid rgba(255,255,255,0.22);
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 16px;
        backdrop-filter: blur(8px);
    }
    .theme-banner {
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 60%, #0284C7 100%);
        border-radius: 16px;
        padding: 1.6rem 2rem;
        color: #FFFFFF;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
        margin-bottom: 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.15);
    }
    .stepper-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 0.9rem 1.4rem;
        margin-bottom: 1.4rem;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.03);
    }
    .step-pill {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 600;
        font-size: 0.88rem;
        color: #64748B;
    }
    .step-pill.active {
        color: #1E40AF;
    }
    .step-circle {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 26px;
        height: 26px;
        border-radius: 50%;
        background: #E2E8F0;
        color: #475569;
        font-size: 0.8rem;
        font-weight: 700;
    }
    .step-pill.active .step-circle {
        background: #2563EB;
        color: #FFFFFF;
        box-shadow: 0 0 10px rgba(37, 99, 235, 0.4);
    }
    .step-sep {
        color: #CBD5E1;
        font-weight: 700;
    }
    .feature-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 1.3rem;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.03);
        margin-bottom: 1rem;
        transition: transform 0.2s ease;
    }
    .feature-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(37, 99, 235, 0.08);
    }
    .auth-hero-box {
        background: linear-gradient(135deg, #07152B 0%, #0F2A4A 100%);
        border-radius: 18px;
        padding: 2.2rem;
        color: #FFFFFF;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.15);
        height: 100%;
    }
    .auth-form-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 18px;
        padding: 2rem;
        box-shadow: 0 10px 25px rgba(15, 23, 42, 0.06);
    }
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(16, 185, 129, 0.1);
        color: #059669;
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# Inicializa banco de dados
inicializar_banco()

# --- Gerenciamento de Sessão de Autenticação ---
if "usuario" not in st.session_state:
    st.session_state["usuario"] = None

# Sincroniza dados atualizados do usuário caso esteja logado
if st.session_state["usuario"] is not None:
    usuario_atualizado = auth.obter_usuario_por_id(st.session_state["usuario"]["id"])
    if usuario_atualizado:
        st.session_state["usuario"] = usuario_atualizado


# ==========================================
# TELA DE LOGIN / REGISTRO (Não Autenticado)
# ==========================================
if st.session_state["usuario"] is None:
    col_hero, col_form = st.columns([1.1, 1], gap="large")

    with col_hero:
        st.markdown("""
            <div class="auth-hero-box">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 1rem;">
                    <span style="font-size: 2rem;">📦</span>
                    <div>
                        <div style="font-size: 1.4rem; font-weight: 800; color: #FFFFFF; letter-spacing: -0.02em;">Gestão de Produtos</div>
                        <div style="font-size: 0.82rem; color: #38BDF8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em;">ERP & Precificação Inteligente</div>
                    </div>
                </div>
                <h2 style="color: #FFFFFF !important; font-size: 1.55rem; font-weight: 700; line-height: 1.3; margin-bottom: 1rem;">
                    Transforme seus XMLs de NF-e em preços de venda lucrativos e custos precisos.
                </h2>
                <p style="color: #CBD5E1; font-size: 0.95rem; line-height: 1.5; margin-bottom: 1.8rem;">
                    Sistema corporativo para automação de entrada de notas fiscais, rateio de frete, impostos (ST, IPI, PIS/COFINS), margem markup e precificação unitária.
                </p>
                <div style="display: flex; flex-direction: column; gap: 12px;">
                    <div style="display: flex; align-items: flex-start; gap: 10px; background: rgba(255,255,255,0.06); padding: 10px 14px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);">
                        <span style="font-size: 1.2rem;">⚡</span>
                        <div>
                            <div style="color: #FFFFFF; font-weight: 600; font-size: 0.9rem;">Importação de XML Automática</div>
                            <div style="color: #94A3B8; font-size: 0.8rem;">Lê múltiplos arquivos em segundos e extrai todos os itens e tributos.</div>
                        </div>
                    </div>
                    <div style="display: flex; align-items: flex-start; gap: 10px; background: rgba(255,255,255,0.06); padding: 10px 14px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);">
                        <span style="font-size: 1.2rem;">🎯</span>
                        <div>
                            <div style="color: #FFFFFF; font-weight: 600; font-size: 0.9rem;">Formação de Preço & Markup</div>
                            <div style="color: #94A3B8; font-size: 0.8rem;">Controle de custo real por unidade, embalagem e margem de lucro.</div>
                        </div>
                    </div>
                    <div style="display: flex; align-items: flex-start; gap: 10px; background: rgba(255,255,255,0.06); padding: 10px 14px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);">
                        <span style="font-size: 1.2rem;">📁</span>
                        <div>
                            <div style="color: #FFFFFF; font-weight: 600; font-size: 0.9rem;">Histórico e Revisão de Notas</div>
                            <div style="color: #94A3B8; font-size: 0.8rem;">Edite e recalcule qualquer nota já salva com total flexibilidade.</div>
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_form:
        st.markdown('<div class="auth-form-card">', unsafe_allow_html=True)
        tab_login, tab_cadastro = st.tabs(["🔑 Entrar no Sistema", "📝 Criar Nova Conta"])

        with tab_login:
            with st.form("form_login"):
                st.markdown("<h3 style='margin-top:0.5rem;'>Acessar Conta</h3>", unsafe_allow_html=True)
                identificador = st.text_input("Usuário ou E-mail", placeholder="ex: felipe ou felipe@empresa.com")
                senha = st.text_input("Senha", type="password", placeholder="Sua senha de acesso")
                btn_entrar = st.form_submit_button("🚀 Entrar no Sistema", use_container_width=True)

                if btn_entrar:
                    sucesso, resultado = auth.autenticar_usuario(identificador, senha)
                    if sucesso:
                        st.session_state["usuario"] = resultado
                        st.success(f"Bem-vindo de volta, {resultado['nome']}!")
                        st.rerun()
                    else:
                        st.error(resultado)

        with tab_cadastro:
            with st.form("form_cadastro"):
                st.markdown("<h3 style='margin-top:0.5rem;'>Criar Conta</h3>", unsafe_allow_html=True)
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    nome = st.text_input("Nome Completo *", placeholder="ex: Felipe Moraes")
                    usuario = st.text_input("Nome de Usuário *", placeholder="ex: felipe.moraes")
                    empresa = st.text_input("Empresa (Opcional)", placeholder="ex: Minha Empresa LTDA")
                with col_c2:
                    email = st.text_input("E-mail *", placeholder="ex: felipe@empresa.com")
                    cargo = st.text_input("Cargo / Função (Opcional)", placeholder="ex: Gestor de Compras")
                    senha_cad = st.text_input("Senha (mínimo 6 caracteres) *", type="password")

                senha_conf = st.text_input("Confirmar Senha *", type="password")
                st.caption("Você poderá configurar seus padrões de markup e impostos a qualquer momento.")
                btn_cadastrar = st.form_submit_button("✨ Criar Minha Conta", use_container_width=True)

                if btn_cadastrar:
                    if senha_cad != senha_conf:
                        st.error("As senhas digitadas não coincidem.")
                    else:
                        sucesso, msg = auth.cadastrar_usuario(
                            usuario=usuario,
                            nome=nome,
                            email=email,
                            senha=senha_cad,
                            empresa=empresa,
                            cargo=cargo,
                        )
                        if sucesso:
                            st.success(msg + " Você já pode fazer login na aba 'Entrar no Sistema'.")
                        else:
                            st.error(msg)
        st.markdown('</div>', unsafe_allow_html=True)

else:
    # ==========================================
    # ÁREA AUTENTICADA
    # ==========================================
    usuario_logado = st.session_state["usuario"]

    # --- BARRA LATERAL (Perfil e Navegação) ---
    with st.sidebar:
        empresa_txt = usuario_logado.get("empresa") or "Empresa não informada"
        cargo_txt = usuario_logado.get("cargo") or "Usuário"

        st.markdown(f"""
            <div class="user-profile-badge">
                <div style="font-size: 1.05rem; font-weight: 700; color: #FFFFFF;">👤 {usuario_logado['nome']}</div>
                <div style="font-size: 0.85rem; color: #C7D6E8;">🏢 {empresa_txt}</div>
                <div style="font-size: 0.80rem; color: #94B3D7;">💼 {cargo_txt}</div>
            </div>
        """, unsafe_allow_html=True)

        col_btn_logout, col_vazia = st.columns([1, 0.01])
        with col_btn_logout:
            if st.button("🚪 Sair (Logout)", use_container_width=True):
                st.session_state["usuario"] = None
                st.rerun()

        st.divider()
        menu_selecionado = st.radio(
            "Navegação",
            ["📦 Gestão & Precificação", "📁 Histórico de NF-e", "👤 Meu Perfil"],
            index=0,
        )
        st.divider()

    # ==========================================
    # ABA 1: GESTÃO & PRECIFICAÇÃO
    # ==========================================
    if menu_selecionado == "📦 Gestão & Precificação":
        # Configurações na Barra Lateral (inicializadas com as preferências salvas no perfil)
        pref_markup = float(usuario_logado.get("markup_padrao", 60.0))
        pref_custo_adicional = float(usuario_logado.get("custo_adicional_padrao", 0.0))
        pref_impostos = usuario_logado.get("impostos_padrao", ["ICMS ST", "FCP ST", "IPI", "II"])

        with st.sidebar:
            st.header("⚙️ Configurações de Cálculo")
            arquivos = st.file_uploader("1. Escolha os arquivos XML", type=["xml"], accept_multiple_files=True)

            markup = st.number_input(
                "2. Markup sobre o custo (%)",
                min_value=0.0,
                max_value=1000.0,
                value=pref_markup,
                step=1.0,
                format="%.2f",
                help="Definido pelo seu perfil. Pode ser ajustado pontualmente aqui."
            )

            st.subheader("3. Impostos considerados no custo")
            todos_impostos = ["ICMS", "ICMS ST", "FCP", "FCP ST", "IPI", "II", "PIS", "COFINS"]
            impostos_opcoes = {}
            for imp in todos_impostos:
                padrao_ativo = imp in pref_impostos
                impostos_opcoes[imp] = st.checkbox(f"Incluir {imp}", value=padrao_ativo, key=f"calc_imp_{imp}")

            impostos_selecionados = [imp for imp, ativo in impostos_opcoes.items() if ativo]

            st.subheader("4. Outros custos")
            custo_adicional_unitario = st.number_input(
                "Custo adicional por unidade (R$)",
                min_value=0.0,
                value=pref_custo_adicional,
                step=0.01,
                help="Custos extras como embalagem, etiquetagem, manuseio, etc."
            )

            if st.button("💾 Salvar como meu padrão de perfil", use_container_width=True):
                sucesso, msg = auth.atualizar_perfil(
                    usuario_id=usuario_logado["id"],
                    nome=usuario_logado["nome"],
                    email=usuario_logado["email"],
                    empresa=usuario_logado.get("empresa", ""),
                    cargo=usuario_logado.get("cargo", ""),
                    markup_padrao=markup,
                    custo_adicional_padrao=custo_adicional_unitario,
                    impostos_padrao=impostos_selecionados,
                )
                if sucesso:
                    st.session_state["usuario"] = auth.obter_usuario_por_id(usuario_logado["id"])
                    st.sidebar.success("Preferências salvas como padrão do seu perfil!")
                else:
                    st.sidebar.error(msg)

        # Banner Temático Principal
        st.markdown(f"""
            <div class="theme-banner">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 14px;">
                    <div>
                        <div class="status-pill" style="margin-bottom: 8px;">🟢 Módulo de Precificação Ativo</div>
                        <h1 style="color: #FFFFFF !important; margin: 0 0 6px 0; font-size: 1.7rem; font-weight: 800;">
                            📦 Gestão de Produtos & Precificação Inteligente
                        </h1>
                        <p style="color: #E2E8F0; margin: 0; font-size: 0.95rem;">
                            Importe seus XMLs de NF-e, rateie custos tributários e calcule margens de revenda em tempo real.
                        </p>
                    </div>
                    <div style="background: rgba(255, 255, 255, 0.12); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 12px; padding: 10px 18px; text-align: right; backdrop-filter: blur(8px);">
                        <div style="font-size: 0.78rem; color: #93C5FD; text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em;">Markup Atual</div>
                        <div style="font-size: 1.45rem; font-weight: 800; color: #FFFFFF;">{markup:.1f}%</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Stepper de Fluxo Intuitivo
        tem_xml = bool(arquivos)
        s1 = "active"
        s2 = "active" if tem_xml else ""
        s3 = "active" if tem_xml else ""
        s4 = "active" if tem_xml else ""

        st.markdown(f"""
            <div class="stepper-container">
                <div class="step-pill {s1}">
                    <span class="step-circle">1</span> 📤 1. Upload XML
                </div>
                <div class="step-sep">➔</div>
                <div class="step-pill {s2}">
                    <span class="step-circle">2</span> ⚙️ 2. Impostos & Custos
                </div>
                <div class="step-sep">➔</div>
                <div class="step-pill {s3}">
                    <span class="step-circle">3</span> 📦 3. Embalagem & Markup
                </div>
                <div class="step-sep">➔</div>
                <div class="step-pill {s4}">
                    <span class="step-circle">4</span> 📊 4. Lucro & Exportação
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Carrega índice existente
        indice = carregar_indice(usuario_id=usuario_logado["id"])

        @st.cache_data(show_spinner="Processando XMLs...")
        def processar_arquivos_upload(dados_arquivos: list, impostos_ativos: list, dict_indice: dict, id_user: int):
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
                        "chave_acesso": chave_acesso,
                        "numero": metadados_nota.get("numero", ""),
                        "serie": metadados_nota.get("serie", ""),
                        "data_emissao": metadados_nota.get("data_emissao", ""),
                        "fornecedor": metadados_nota.get("fornecedor", ""),
                        "cnpj_emit": metadados_nota.get("cnpj_emit", ""),
                        "valor_total": metadados_nota.get("valor_total", 0),
                        "arquivo_original": nome_arquivo,
                        "arquivo_salvo": nome_salvo,
                        "data_importacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "usuario_id": id_user,
                    }
                    novas_notas.append(nova_nota)

            return todos_produtos, novas_notas, avisos, erros

        if not arquivos:
            # Guia Rápido Intuitivo
            st.markdown("""
                <div style="background: #FFFFFF; border: 1.5px dashed #CBD5E1; border-radius: 16px; padding: 2.2rem; text-align: center; margin-bottom: 1.8rem; box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04);">
                    <div style="font-size: 3rem; margin-bottom: 0.6rem;">📥</div>
                    <h3 style="color: #0F2744; margin: 0 0 0.5rem 0; font-weight: 700;">Envie seus XMLs na barra lateral para começar</h3>
                    <p style="color: #64748B; max-width: 620px; margin: 0 auto 1.6rem auto; font-size: 0.95rem; line-height: 1.5;">
                        Selecione um ou mais arquivos XML de Notas Fiscais na barra à esquerda. O sistema processará impostos, rateará frete e formará seus preços automaticamente.
                    </p>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; text-align: left; max-width: 820px; margin: 0 auto;">
                        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; padding: 16px; border-radius: 12px;">
                            <div style="font-size: 1.2rem; margin-bottom: 6px;">📑</div>
                            <div style="font-weight: 700; color: #1E40AF; margin-bottom: 4px; font-size: 0.92rem;">1. Escolha o XML</div>
                            <div style="font-size: 0.83rem; color: #64748B;">Aceita múltiplos arquivos simultâneos emitidos pelos fornecedores.</div>
                        </div>
                        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; padding: 16px; border-radius: 12px;">
                            <div style="font-size: 1.2rem; margin-bottom: 6px;">⚡</div>
                            <div style="font-weight: 700; color: #1E40AF; margin-bottom: 4px; font-size: 0.92rem;">2. Defina Markup & Custos</div>
                            <div style="font-size: 0.83rem; color: #64748B;">Ajuste impostos recuperáveis ou de custo e despesas extras por unidade.</div>
                        </div>
                        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; padding: 16px; border-radius: 12px;">
                            <div style="font-size: 1.2rem; margin-bottom: 6px;">📊</div>
                            <div style="font-weight: 700; color: #1E40AF; margin-bottom: 4px; font-size: 0.92rem;">3. Baixe a Planilha</div>
                            <div style="font-size: 0.83rem; color: #64748B;">Exporte instantaneamente para Excel com todas as colunas de formação.</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # Exibe resumo do histórico recente
            if indice:
                st.subheader("📋 Últimas notas fiscais processadas")
                df_historico_recente = pd.DataFrame(list(indice.values())).head(5)
                cols_recentes = [c for c in ["numero", "serie", "fornecedor", "data_emissao", "valor_total", "data_importacao"] if c in df_historico_recente.columns]
                st.dataframe(df_historico_recente[cols_recentes], use_container_width=True, hide_index=True)
        else:
            arquivos_para_cache = [(arq.name, arq.getvalue()) for arq in arquivos]
            produtos_extraidos, notas_para_salvar, avisos_gerados, erros_gerados = processar_arquivos_upload(
                arquivos_para_cache, impostos_selecionados, indice, usuario_logado["id"]
            )

            for nota in notas_para_salvar:
                salvar_nota(nota)

            for aviso in avisos_gerados:
                st.warning(aviso)
            for erro in erros_gerados:
                st.error(erro)

            if not produtos_extraidos:
                st.error("Nenhum produto novo foi encontrado nos arquivos enviados.")
            else:
                df = pd.DataFrame(produtos_extraidos)

                st.subheader("🔢 1. Ajuste de Unidades Reais por Embalagem")
                st.caption("💡 Se você comprou caixas ou fardos e vende unidades avulsas, informe a quantidade contida em cada embalagem para recalcular o custo unitário real.")

                df["ID_temp"] = df["Código"].astype(str) + "_" + df["Arquivo XML"].astype(str)

                if "unidades_por_embalagem" not in st.session_state:
                    st.session_state["unidades_por_embalagem"] = {}

                df_editor_base = df[["ID_temp", "Código", "Produto", "Unidade", "Quantidade", "Arquivo XML"]].copy()
                df_editor_base["Unidades por embalagem"] = df_editor_base["ID_temp"].map(
                    lambda id_temp: st.session_state["unidades_por_embalagem"].get(id_temp, 1.0)
                )

                df_editado = st.data_editor(
                    df_editor_base,
                    use_container_width=True,
                    hide_index=True,
                    disabled=["ID_temp", "Código", "Produto", "Unidade", "Quantidade", "Arquivo XML"],
                    key="editor_unidades_por_embalagem",
                )

                novas_unidades = df_editado.set_index("ID_temp")["Unidades por embalagem"].to_dict()
                st.session_state["unidades_por_embalagem"].update(novas_unidades)

                df = processar_metricas_revenda(
                    df,
                    st.session_state["unidades_por_embalagem"],
                    custo_adicional_unitario,
                    markup,
                )
                df = df.drop(columns=["ID_temp"])

                # Métricas em destaque com Cards Estilizados
                st.divider()
                st.subheader("📊 2. Resumo Consolidado dos Produtos")

                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                col_m1.metric("Qtd. Itens Únicos", f"{len(df)} itens")
                col_m2.metric("Custo Total Acumulado", f"R$ {df['Custo final'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                col_m3.metric("Faturamento Estimado", f"R$ {df['Total de revenda'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                col_m4.metric("Lucro Bruto Estimado", f"R$ {df['Lucro total'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

                st.divider()
                st.subheader("📋 3. Tabela Detalhada de Custos e Formação de Preço")
                st.dataframe(df, use_container_width=True, hide_index=True)

                # Botão de exportação
                csv_data = df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
                st.download_button(
                    label="📥 Exportar Tabela para Excel (CSV)",
                    data=csv_data,
                    file_name=f"precificacao_produtos_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                )

    # ==========================================
    # ABA 2: HISTÓRICO DE NF-E
    # ==========================================
    elif menu_selecionado == "📁 Histórico de NF-e":
        st.markdown("""
            <div class="theme-banner">
                <div class="status-pill" style="margin-bottom: 8px;">📁 Base de Dados Segura</div>
                <h1 style="color: #FFFFFF !important; margin: 0 0 6px 0; font-size: 1.7rem; font-weight: 800;">
                    📁 Histórico de Notas Fiscais Importadas
                </h1>
                <p style="color: #E2E8F0; margin: 0; font-size: 0.95rem;">
                    Consulte todas as NF-e vinculadas à sua conta, revise os itens tributários e recalcule as precificações.
                </p>
            </div>
        """, unsafe_allow_html=True)

        indice = carregar_indice(usuario_id=usuario_logado["id"])

        if not indice:
            st.info("Nenhuma nota fiscal foi importada ainda para este usuário.")
        else:
            df_hist = pd.DataFrame(list(indice.values())).sort_values("data_importacao", ascending=False)

            col_h1, col_h2, col_h3 = st.columns(3)
            col_h1.metric("Total de Notas Importadas", f"{len(df_hist)} NF-es")
            col_h2.metric("Valor Total Acumulado", f"R$ {df_hist['valor_total'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            col_h3.metric("Fornecedores Atendidos", f"{df_hist['fornecedor'].nunique()} parceiros")

            st.divider()
            st.subheader("Filtros")
            filtro_pesquisa = st.text_input("🔍 Buscar por número de nota, fornecedor ou CNPJ", placeholder="Digite para filtrar...")

            if filtro_pesquisa:
                termo = filtro_pesquisa.lower()
                df_hist = df_hist[
                    df_hist["numero"].astype(str).str.lower().str.contains(termo) |
                    df_hist["fornecedor"].astype(str).str.lower().str.contains(termo) |
                    df_hist["cnpj_emit"].astype(str).str.lower().str.contains(termo)
                ]

            colunas_exibir = [
                "numero", "serie", "data_emissao", "fornecedor", "cnpj_emit",
                "valor_total", "data_importacao", "arquivo_original"
            ]
            colunas_existentes = [c for c in colunas_exibir if c in df_hist.columns]

            st.dataframe(df_hist[colunas_existentes], use_container_width=True, hide_index=True)

            # ------------------------------------------------------------------
            # SEÇÃO: Revisar e Editar produtos de uma nota selecionada
            # ------------------------------------------------------------------
            st.divider()
            st.subheader("👁️ Revisar / Editar Produtos de uma Nota")
            st.caption("Selecione uma nota para visualizar seus produtos, ajustar configurações de cálculo e salvar as preferências desta nota.")

            # Monta opções de seleção formatadas
            opcoes_notas = {
                f"NF {row.get('numero', '—')}  |  {row.get('fornecedor', '—')}  |  {row.get('data_emissao', '—')}": row.get("chave_acesso", "")
                for _, row in df_hist.iterrows()
                if row.get("arquivo_salvo")
            }

            if not opcoes_notas:
                st.warning("Nenhuma nota com arquivo XML salvo foi encontrada. Apenas notas importadas via upload possuem arquivo disponível para revisão.")
            else:
                nota_selecionada_label = st.selectbox(
                    "Selecione a Nota Fiscal",
                    options=list(opcoes_notas.keys()),
                    index=0,
                    key="hist_nota_selecionada"
                )
                chave_selecionada = opcoes_notas[nota_selecionada_label]

                # Recupera o registro completo da nota selecionada
                nota_info = indice.get(chave_selecionada, {})
                arquivo_salvo = nota_info.get("arquivo_salvo", "")

                # Carrega configurações salvas (ou defaults do perfil do usuário)
                config_salva = carregar_config_nota(chave_selecionada, defaults=usuario_logado)

                with st.expander("⚙️ Configurações de Cálculo desta Nota", expanded=True):
                    col_cfg1, col_cfg2 = st.columns(2)

                    with col_cfg1:
                        hist_markup = st.number_input(
                            "Markup sobre o custo (%)",
                            min_value=0.0, max_value=1000.0,
                            value=float(config_salva["markup"]),
                            step=1.0, format="%.2f",
                            key=f"hist_markup_{chave_selecionada}"
                        )
                        hist_custo_adicional = st.number_input(
                            "Custo adicional por unidade (R$)",
                            min_value=0.0,
                            value=float(config_salva["custo_adicional"]),
                            step=0.01,
                            key=f"hist_custo_{chave_selecionada}"
                        )
                        if config_salva.get("atualizado_em"):
                            st.caption(f"💾 Última configuração salva em: {config_salva['atualizado_em']}")

                    with col_cfg2:
                        st.markdown("**Impostos considerados no custo:**")
                        todos_impostos_h = ["ICMS", "ICMS ST", "FCP", "FCP ST", "IPI", "II", "PIS", "COFINS"]
                        impostos_salvos = config_salva["impostos"]
                        hist_impostos_opcoes = {}
                        col_i1h, col_i2h = st.columns(2)
                        for i, imp in enumerate(todos_impostos_h):
                            target_col = col_i1h if i < 4 else col_i2h
                            hist_impostos_opcoes[imp] = target_col.checkbox(
                                imp,
                                value=(imp in impostos_salvos),
                                key=f"hist_imp_{chave_selecionada}_{imp}"
                            )
                    hist_impostos_selecionados = [imp for imp, ativo in hist_impostos_opcoes.items() if ativo]

                # Carrega produtos do XML salvo
                produtos_nota = carregar_produtos_da_nota(arquivo_salvo, hist_impostos_selecionados)

                if not produtos_nota:
                    st.warning(f"Não foi possível carregar os produtos. O arquivo XML da nota pode não estar disponível em `{PASTA_XMLS_PROCESSADOS}/`.")
                else:
                    df_nota = pd.DataFrame(produtos_nota)
                    df_nota["ID_temp"] = df_nota["Código"].astype(str) + "_" + arquivo_salvo

                    # Unidades por embalagem
                    st.markdown("**📦 Ajuste de Unidades por Embalagem**")
                    st.caption("Caso o produto seja revendido individualmente (ex: caixa com 12 unidades), ajuste abaixo.")

                    unid_session_key = f"hist_unid_{chave_selecionada}"
                    if unid_session_key not in st.session_state:
                        st.session_state[unid_session_key] = {
                            k: v for k, v in config_salva["unidades_por_embalagem"].items()
                        }

                    df_editor_hist = df_nota[["ID_temp", "Código", "Produto", "Unidade", "Quantidade"]].copy()
                    df_editor_hist["Unidades por embalagem"] = df_editor_hist["ID_temp"].map(
                        lambda id_temp: st.session_state[unid_session_key].get(id_temp, 1.0)
                    )

                    df_editado_hist = st.data_editor(
                        df_editor_hist,
                        use_container_width=True,
                        hide_index=True,
                        disabled=["ID_temp", "Código", "Produto", "Unidade", "Quantidade"],
                        key=f"editor_hist_{chave_selecionada}",
                    )

                    novas_unid = df_editado_hist.set_index("ID_temp")["Unidades por embalagem"].to_dict()
                    st.session_state[unid_session_key].update(novas_unid)

                    # Processa métricas com as configurações desta nota
                    df_nota_calc = processar_metricas_revenda(
                        df_nota.copy(),
                        st.session_state[unid_session_key],
                        hist_custo_adicional,
                        hist_markup,
                    )
                    df_nota_calc = df_nota_calc.drop(columns=["ID_temp"], errors="ignore")

                    # Métricas resumo
                    st.divider()
                    st.subheader("📊 Resumo dos Produtos")
                    col_nm1, col_nm2, col_nm3, col_nm4 = st.columns(4)
                    col_nm1.metric("Itens", f"{len(df_nota_calc)}")
                    col_nm2.metric("Custo Total", f"R$ {df_nota_calc['Custo final'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    col_nm3.metric("Faturamento Estimado", f"R$ {df_nota_calc['Total de revenda'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    col_nm4.metric("Lucro Bruto Estimado", f"R$ {df_nota_calc['Lucro total'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

                    st.subheader("📋 Tabela Detalhada")
                    st.dataframe(df_nota_calc, use_container_width=True, hide_index=True)

                    col_save, col_export = st.columns([1, 1])

                    with col_save:
                        if st.button("💾 Salvar configurações desta nota", use_container_width=True, key=f"btn_salvar_cfg_{chave_selecionada}"):
                            salvar_config_nota(
                                chave_acesso=chave_selecionada,
                                markup=hist_markup,
                                custo_adicional=hist_custo_adicional,
                                impostos=hist_impostos_selecionados,
                                unidades_por_embalagem=st.session_state[unid_session_key],
                            )
                            st.success("✅ Configurações salvas com sucesso! Elas serão carregadas automaticamente na próxima vez que você acessar esta nota.")

                    with col_export:
                        csv_hist = df_nota_calc.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
                        st.download_button(
                            label="📥 Exportar para Excel (CSV)",
                            data=csv_hist,
                            file_name=f"produtos_nota_{nota_info.get('numero', 'SN')}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                            mime="text/csv",
                            use_container_width=True,
                            key=f"btn_export_{chave_selecionada}",
                        )

    # ==========================================
    # ABA 3: MEU PERFIL E SALVAMENTO DE CONFIGURAÇÕES
    # ==========================================
    elif menu_selecionado == "👤 Meu Perfil":
        st.markdown("""
            <div class="theme-banner">
                <div class="status-pill" style="margin-bottom: 8px;">👤 Conta de Usuário</div>
                <h1 style="color: #FFFFFF !important; margin: 0 0 6px 0; font-size: 1.7rem; font-weight: 800;">
                    👤 Meu Perfil & Preferências Padrão
                </h1>
                <p style="color: #E2E8F0; margin: 0; font-size: 0.95rem;">
                    Gerencie seus dados corporativos de acesso e personalize os valores padrão de markup e impostos.
                </p>
            </div>
        """, unsafe_allow_html=True)

        tab_dados, tab_preferencias, tab_seguranca = st.tabs([
            "📋 Dados Cadastrais",
            "⚙️ Preferências Padrão de Precificação",
            "🔒 Segurança e Senha"
        ])

        # Tab 1: Dados Cadastrais
        with tab_dados:
            st.subheader("Informações Cadastrais")
            with st.form("form_perfil_dados"):
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    p_nome = st.text_input("Nome Completo", value=usuario_logado["nome"])
                    p_usuario = st.text_input("Nome de Usuário", value=usuario_logado["usuario"], disabled=True, help="O nome de usuário não pode ser alterado.")
                    p_empresa = st.text_input("Empresa", value=usuario_logado.get("empresa", ""))
                with col_p2:
                    p_email = st.text_input("E-mail", value=usuario_logado["email"])
                    p_cargo = st.text_input("Cargo / Função", value=usuario_logado.get("cargo", ""))
                    p_criado = st.text_input("Membro desde", value=usuario_logado.get("criado_em", "-"), disabled=True)

                btn_salvar_dados = st.form_submit_button("💾 Salvar Dados do Perfil")

                if btn_salvar_dados:
                    sucesso, msg = auth.atualizar_perfil(
                        usuario_id=usuario_logado["id"],
                        nome=p_nome,
                        email=p_email,
                        empresa=p_empresa,
                        cargo=p_cargo,
                        markup_padrao=usuario_logado.get("markup_padrao", 60.0),
                        custo_adicional_padrao=usuario_logado.get("custo_adicional_padrao", 0.0),
                        impostos_padrao=usuario_logado.get("impostos_padrao", ["ICMS ST", "FCP ST", "IPI", "II"]),
                    )
                    if sucesso:
                        st.session_state["usuario"] = auth.obter_usuario_por_id(usuario_logado["id"])
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        # Tab 2: Preferências Padrão de Precificação
        with tab_preferencias:
            st.subheader("Configurações Padrão de Precificação")
            st.caption("Defina os valores que serão carregados automaticamente sempre que você entrar na aba de Gestão & Precificação.")

            with st.form("form_perfil_preferencias"):
                col_pref1, col_pref2 = st.columns(2)
                with col_pref1:
                    p_markup = st.number_input(
                        "Markup Padrão (%)",
                        min_value=0.0,
                        max_value=1000.0,
                        value=float(usuario_logado.get("markup_padrao", 60.0)),
                        step=1.0,
                        format="%.2f"
                    )
                    p_custo_adicional = st.number_input(
                        "Custo Adicional Padrão por Unidade (R$)",
                        min_value=0.0,
                        value=float(usuario_logado.get("custo_adicional_padrao", 0.0)),
                        step=0.01
                    )

                with col_pref2:
                    st.markdown("**Impostos Padrão Incluídos no Custo:**")
                    todos_impostos = ["ICMS", "ICMS ST", "FCP", "FCP ST", "IPI", "II", "PIS", "COFINS"]
                    impostos_atuais = usuario_logado.get("impostos_padrao", ["ICMS ST", "FCP ST", "IPI", "II"])

                    impostos_checks = {}
                    col_i1, col_i2 = st.columns(2)
                    for i, imp in enumerate(todos_impostos):
                        target_col = col_i1 if i < 4 else col_i2
                        impostos_checks[imp] = target_col.checkbox(
                            imp,
                            value=(imp in impostos_atuais),
                            key=f"pref_chk_{imp}"
                        )

                btn_salvar_pref = st.form_submit_button("💾 Salvar Preferências de Precificação")

            if btn_salvar_pref:
                novos_impostos = [imp for imp, ativo in impostos_checks.items() if ativo]
                sucesso, msg = auth.atualizar_perfil(
                    usuario_id=usuario_logado["id"],
                    nome=usuario_logado["nome"],
                    email=usuario_logado["email"],
                    empresa=usuario_logado.get("empresa", ""),
                    cargo=usuario_logado.get("cargo", ""),
                    markup_padrao=p_markup,
                    custo_adicional_padrao=p_custo_adicional,
                    impostos_padrao=novos_impostos,
                )
                if sucesso:
                    st.session_state["usuario"] = auth.obter_usuario_por_id(usuario_logado["id"])
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        # Tab 3: Segurança e Senha
        with tab_seguranca:
            st.subheader("Alteração de Senha")
            with st.form("form_alterar_senha"):
                s_atual = st.text_input("Senha Atual", type="password")
                s_nova = st.text_input("Nova Senha (mínimo 6 caracteres)", type="password")
                s_confirma = st.text_input("Confirmar Nova Senha", type="password")

                btn_trocar_senha = st.form_submit_button("🔒 Atualizar Senha")

                if btn_trocar_senha:
                    if s_nova != s_confirma:
                        st.error("A nova senha e a confirmação não coincidem.")
                    else:
                        sucesso, msg = auth.alterar_senha(
                            usuario_id=usuario_logado["id"],
                            senha_atual=s_atual,
                            nova_senha=s_nova,
                        )
                        if sucesso:
                            st.success(msg)
                        else:
                            st.error(msg)
