import os
import sqlite3
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional
from defusedxml import ElementTree as ET
import pandas as pd
import plotly.express as px
import streamlit as st

import auth

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "banco_notas.db")
PASTA_XMLS_PROCESSADOS = os.path.join(BASE_DIR, "xmls_processados")


def inicializar_banco() -> None:
    """Inicializa as pastas, tabelas de notas e usuários."""
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
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
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
    page_title="Gestão de Produtos",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
    <style>
    html, body, [class*="css"] { font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; }
    .block-container { padding-top: 2rem; padding-bottom: 3rem; }
    h1 { color: #1B4F8C; font-weight: 700; border-bottom: 3px solid #1B4F8C; padding-bottom: 0.5rem; margin-bottom: 0.6rem; }
    h2, h3 { color: #1B4F8C; font-weight: 600; margin-top: 1.8rem; }
    [data-testid="stCaptionContainer"], .stCaption, small { color: #33475B !important; opacity: 1 !important; font-size: 0.92rem !important; }
    section[data-testid="stSidebar"] { background-color: #0E2A47; }
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] span:not(input span) {
        color: #FFFFFF !important;
        opacity: 1 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"], section[data-testid="stSidebar"] .stCaption, section[data-testid="stSidebar"] small { color: #C7D6E8 !important; opacity: 1 !important; }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 { color: #FFFFFF !important; border-bottom: none; }
    section[data-testid="stSidebar"] .stCheckbox { background-color: rgba(255, 255, 255, 0.06); border-radius: 6px; padding: 2px 6px; margin-bottom: 2px; }
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea,
    section[data-testid="stSidebar"] [data-baseweb="input"] input,
    section[data-testid="stSidebar"] [data-baseweb="base-input"] input,
    section[data-testid="stSidebar"] [data-testid="stNumberInput"] input,
    section[data-testid="stSidebar"] input[type="number"] {
        background-color: #FFFFFF !important;
        color: #0E2A47 !important;
        -webkit-text-fill-color: #0E2A47 !important;
        caret-color: #0E2A47 !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        opacity: 1 !important;
        border: 1px solid rgba(255, 255, 255, 0.55) !important;
        border-radius: 6px !important;
    }
    section[data-testid="stSidebar"] [data-testid="stNumberInput"] input:focus,
    section[data-testid="stSidebar"] input[type="number"]:focus {
        color: #0E2A47 !important;
        -webkit-text-fill-color: #0E2A47 !important;
        background-color: #FFFFFF !important;
        outline: 2px solid #66B3FF !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="input"],
    section[data-testid="stSidebar"] [data-baseweb="base-input"],
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        background-color: rgba(255, 255, 255, 0.10) !important;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        border-radius: 8px !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * { color: #FFFFFF !important; }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {
        background-color: rgba(255,255,255,0.2) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255,255,255,0.35) !important;
    }
    section[data-testid="stSidebar"] input::placeholder {
        color: #5B7087 !important;
        -webkit-text-fill-color: #5B7087 !important;
        opacity: 1 !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="select"] > div,
    section[data-testid="stSidebar"] [data-baseweb="select"] input {
        background-color: rgba(255, 255, 255, 0.12) !important;
        color: #FFFFFF !important;
        border-color: rgba(255,255,255,0.25) !important;
    }
    div[data-testid="stMetric"] { background-color: #F0F4F8; border: 1px solid #D6E0EA; border-left: 5px solid #1B4F8C; border-radius: 8px; padding: 1rem 1.2rem; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06); }
    div[data-testid="stMetricLabel"] { color: #4A5A6A; font-weight: 600; }
    div[data-testid="stMetricValue"] { color: #1B4F8C; font-weight: 700; }
    .stButton button, .stDownloadButton button { background-color: #1B4F8C; color: white; border-radius: 6px; border: none; font-weight: 600; padding: 0.5rem 1.2rem; }
    .stButton button:hover, .stDownloadButton button:hover { background-color: #163F70; color: white; }
    div[data-testid="stAlert"] { border-radius: 8px; }
    div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] { border: 1px solid #D6E0EA; border-radius: 8px; overflow: hidden; }
    hr { border-top: 1px solid #D6E0EA; }
    .user-profile-badge {
        background: linear-gradient(135deg, rgba(255,255,255,0.12), rgba(255,255,255,0.05));
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 15px;
    }
    .auth-card {
        background-color: #FFFFFF;
        border: 1px solid #D6E0EA;
        border-radius: 12px;
        padding: 2rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
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
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.markdown("<h1 style='text-align: center; border-bottom: none;'>📦 Gestão de Produtos</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #4A5A6A; font-size: 1.1rem; margin-bottom: 1.5rem;'>Acesse sua conta para gerenciar NF-e, custos e preços de revenda</p>", unsafe_allow_html=True)

        tab_login, tab_cadastro = st.tabs(["🔑 Entrar no Sistema", "📝 Criar Nova Conta"])

        with tab_login:
            with st.form("form_login"):
                st.subheader("Login")
                identificador = st.text_input("Usuário ou E-mail", placeholder="ex: felipe ou felipe@empresa.com")
                senha = st.text_input("Senha", type="password", placeholder="Sua senha")
                btn_entrar = st.form_submit_button("Entrar", use_container_width=True)

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
                st.subheader("Cadastre-se")
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

                st.caption("Suas preferências de precificação padrão poderão ser editadas a qualquer momento em seu perfil.")
                btn_cadastrar = st.form_submit_button("Criar Conta", use_container_width=True)

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
        st.title("📦 Gestão de Produtos e Precificação")
        st.markdown("<p style='color:#4A5A6A; font-size:1.05rem; margin-top:-0.8rem;'>Importe XMLs de NF-e, calcule custos automáticos e defina preços de revenda com base no seu perfil.</p>", unsafe_allow_html=True)

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
                        "_conteudo_bytes": conteudo_bytes,
                    }
                    novas_notas.append(nova_nota)

            return todos_produtos, novas_notas, avisos, erros

        if not arquivos:
            st.info("💡 Envie um ou mais arquivos XML de NF-e na barra lateral para iniciar o processamento de custos e formação de preços.")

            # Exibe resumo do histórico recente
            if indice:
                st.divider()
                st.subheader("📋 Últimas notas fiscais processadas")
                df_historico_recente = pd.DataFrame(list(indice.values())).head(5)
                cols_recentes = [c for c in ["numero", "serie", "fornecedor", "data_emissao", "valor_total", "data_importacao"] if c in df_historico_recente.columns]
                st.dataframe(df_historico_recente[cols_recentes], use_container_width=True, hide_index=True)
        else:
            arquivos_para_cache = [(arq.name, arq.getvalue()) for arq in arquivos]
            produtos_extraidos, notas_para_salvar, avisos_gerados, erros_gerados = processar_arquivos_upload(
                arquivos_para_cache, impostos_selecionados, indice, usuario_logado["id"]
            )

            for aviso in avisos_gerados:
                st.warning(aviso)
            for erro in erros_gerados:
                st.error(erro)

            if not produtos_extraidos:
                st.error("Nenhum produto novo foi encontrado nos arquivos enviados.")
            else:
                df = pd.DataFrame(produtos_extraidos)

                st.divider()
                st.subheader("🔢 1. Ajuste de Unidades Reais por Embalagem")
                st.caption("Caso o produto tenha sido comprado em caixa/fardo e você revenda individualmente, ajuste a quantidade por embalagem.")

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

                # Métricas em destaque
                st.divider()
                st.subheader("📊 2. Resumo Consolidado dos Produtos")

                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                col_m1.metric("Qtd. Itens Únicos", f"{len(df)}")
                col_m2.metric("Custo Total Acumulado", f"R$ {df['Custo final'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                col_m3.metric("Faturamento Estimado", f"R$ {df['Total de revenda'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                col_m4.metric("Lucro Bruto Estimado", f"R$ {df['Lucro total'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

                st.divider()
                st.subheader("📋 3. Tabela Detalhada de Custos e Formação de Preço")
                st.dataframe(df, use_container_width=True, hide_index=True)

                col_finalize, col_export = st.columns([1, 1])
                with col_finalize:
                    chave_nota = ",".join(sorted(n.get("chave_acesso", "") for n in notas_para_salvar))
                    if st.button("Finalizar NF-e", use_container_width=True, key=f"btn_finalizar_nfe_{chave_nota or 'pendente'}"):
                        for nota in notas_para_salvar:
                            conteudo_xml = nota.get("_conteudo_bytes")
                            if conteudo_xml is None:
                                continue
                            caminho_salvo = os.path.join(PASTA_XMLS_PROCESSADOS, nota["arquivo_salvo"])
                            with open(caminho_salvo, "wb") as arquivo_salvo:
                                arquivo_salvo.write(conteudo_xml)
                            salvar_nota({k: v for k, v in nota.items() if not k.startswith("_")})
                        st.success("NF-e finalizada e enviada para os arquivos arquivados.")
                        st.rerun()

                with col_export:
                    csv_data = df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
                    st.download_button(
                        label="Exportar Tabela para Excel (CSV)",
                        data=csv_data,
                        file_name=f"precificacao_produtos_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

    # ==========================================
    # ABA 2: HISTÓRICO DE NF-E
    # ==========================================
    elif menu_selecionado == "📁 Histórico de NF-e":
        st.title("📁 Histórico de Notas Fiscais Importadas")
        st.markdown("<p style='color:#4A5A6A; font-size:1.05rem; margin-top:-0.8rem;'>Consulte todas as NF-e vinculadas à sua conta, revise os produtos e edite as configurações de precificação.</p>", unsafe_allow_html=True)

        indice = carregar_indice(usuario_id=usuario_logado["id"])

        if not indice:
            st.info("Nenhuma nota fiscal foi importada ainda para este usuário.")
        else:
            df_hist = pd.DataFrame(list(indice.values())).sort_values("data_importacao", ascending=False)

            col_h1, col_h2, col_h3 = st.columns(3)
            col_h1.metric("Total de Notas Importadas", f"{len(df_hist)}")
            col_h2.metric("Valor Total Acumulado", f"R$ {df_hist['valor_total'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            col_h3.metric("Fornecedores Atendidos", f"{df_hist['fornecedor'].nunique()}")

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
        st.title("👤 Meu Perfil e Preferências")
        st.markdown("<p style='color:#4A5A6A; font-size:1.05rem; margin-top:-0.8rem;'>Gerencie seus dados de acesso, informações da empresa e salve suas preferências padrão de cálculo.</p>", unsafe_allow_html=True)

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
