from io import BytesIO
from decimal import Decimal, InvalidOperation

import pandas as pd
import plotly.express as px
import streamlit as st
from defusedxml import ElementTree as ET

st.set_page_config(
    page_title="Gestão de Produtos",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
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


def ler_xml(arquivo, impostos_selecionados):
    try:
        conteudo = arquivo.getvalue()
        root = ET.fromstring(conteudo)

        produtos = localizar_produtos(
            root,
            impostos_selecionados
        )

        return produtos, None

    except ET.ParseError:
        return [], (
            f"O arquivo {arquivo.name} "
            "não possui um XML válido."
        )

    except Exception as erro:
        return [], (
            f"Erro ao processar {arquivo.name}: {erro}"
        )


st.title("📦 Gestão de Produtos")
st.write(
    "Importe XMLs de NF-e, calcule custos e defina preços de revenda."
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

if not arquivos:
    st.info(
        "Envie um ou mais arquivos XML na barra lateral para começar."
    )

    st.stop()

todos_produtos = []
erros = []

for arquivo in arquivos:
    produtos, erro = ler_xml(
        arquivo,
        impostos_selecionados
    )

    if erro:
        erros.append(erro)
        continue

    for produto in produtos:
        produto["Arquivo XML"] = arquivo.name

    todos_produtos.extend(produtos)

if erros:
    for erro in erros:
        st.warning(erro)

if not todos_produtos:
    st.error(
        "Nenhum produto foi encontrado nos arquivos enviados."
    )

    st.stop()

df = pd.DataFrame(todos_produtos)
df["Custo adicional"] = (
    df["Quantidade"] * custo_adicional_unitario
)

df["Custo final"] = (
    df["Custo final"]
    + df["Custo adicional"]
)

df["Custo unitário final"] = (
    df["Custo final"] / df["Quantidade"].replace(0, 1)
)

fator_markup = 1 + (markup / 100)

df["Preço de revenda unitário"] = (
    df["Custo unitário final"] * fator_markup
)

df["Total de revenda"] = (
    df["Quantidade"]
    * df["Preço de revenda unitário"]
)

df["Lucro unitário"] = (
    df["Preço de revenda unitário"]
    - df["Custo unitário final"]
)

df["Lucro total"] = (
    df["Quantidade"] * df["Lucro unitário"]
)

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

st.subheader("📋 Produtos processados")

st.dataframe(
    df[colunas_tabela],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Quantidade": st.column_config.NumberColumn(
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

st.subheader("📈 Gráfico de análise")

tipo_grafico = st.selectbox(
    "Escolha o tipo de gráfico",
    [
        "Total de revenda",
        "Quantidade",
        "Lucro total",
        "Custo final",
    ]
)

agrupado = df.groupby(
    "Produto",
    as_index=False
).agg({
    "Quantidade": "sum",
    "Total de revenda": "sum",
    "Lucro total": "sum",
    "Custo final": "sum",
})

if tipo_grafico == "Total de revenda":
    coluna_valor = "Total de revenda"

elif tipo_grafico == "Quantidade":
    coluna_valor = "Quantidade"

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

st.plotly_chart(
    fig,
    use_container_width=True
)

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