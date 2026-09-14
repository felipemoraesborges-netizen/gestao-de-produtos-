import io
import json
import os
import re
import sqlite3
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional
from defusedxml import ElementTree as ET
from xml.etree.ElementTree import Element
from fastapi import FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
import pandas as pd

import auth
import security

DB_PATH = security.DB_PATH
PASTA_XMLS_PROCESSADOS = "xmls_processados"

app = FastAPI(
    title="Gestão de Produtos API",
    description="API Corporativa de Alta Performance - Precificação, Estoque & Auditoria (Hardened)",
    version="3.0.0",
)

# ==========================================
# 1. CORS SEGURO (OWASP: Sem allow_origins=* com credentials)
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=security.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin"],
)


# ==========================================
# 2. MIDDLEWARE DE HEADERS DE SEGURANÇA (OWASP)
# ==========================================
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    if security.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ==========================================
# 3. TRATAMENTO GLOBAL DE EXCEÇÕES
# ==========================================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Loga erro interno no terminal sem expor stacktrace, paths ou segredos ao cliente
    print(f"[ERRO NÃO TRATADO] Rota: {request.url.path} | Tipo: {type(exc).__name__} | Detalhes: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Ocorreu um erro interno no servidor. Por favor, tente novamente mais tarde."},
    )


# ==========================================
# 4. INICIALIZAÇÃO DE BANCO E ÍNDICES
# ==========================================
def inicializar_banco() -> None:
    os.makedirs(PASTA_XMLS_PROCESSADOS, exist_ok=True)
    conn = security.get_db_connection(DB_PATH)
    cursor = conn.cursor()

    # Tabela historico_nfe
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
    cursor.execute("PRAGMA table_info(historico_nfe)")
    colunas_nfe = [col[1] for col in cursor.fetchall()]
    if "usuario_id" not in colunas_nfe:
        cursor.execute("ALTER TABLE historico_nfe ADD COLUMN usuario_id INTEGER")

    # Tabela estoque_produtos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS estoque_produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL,
            produto TEXT NOT NULL,
            unidade TEXT DEFAULT 'UN',
            quantidade_atual REAL DEFAULT 0.0,
            estoque_minimo REAL DEFAULT 5.0,
            custo_unitario REAL DEFAULT 0.0,
            preco_venda REAL DEFAULT 0.0,
            fornecedor_ultimo TEXT DEFAULT '',
            categoria TEXT DEFAULT 'Geral',
            usuario_id INTEGER,
            criado_em TEXT NOT NULL,
            atualizado_em TEXT NOT NULL,
            UNIQUE(codigo, usuario_id)
        )
    """)

    # Tabela estoque_movimentacoes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS estoque_movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            quantidade REAL NOT NULL,
            quantidade_anterior REAL NOT NULL,
            quantidade_nova REAL NOT NULL,
            motivo TEXT,
            documento_ref TEXT,
            usuario_id INTEGER,
            usuario_nome TEXT DEFAULT '',
            data_hora TEXT NOT NULL
        )
    """)

    # Tabela trilha_auditoria
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trilha_auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            usuario_nome TEXT,
            acao TEXT NOT NULL,
            detalhes TEXT NOT NULL,
            ip TEXT DEFAULT '127.0.0.1',
            data_hora TEXT NOT NULL
        )
    """)

    # Índices essenciais para isolamento e performance por usuario_id
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_nfe_usuario ON historico_nfe(usuario_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_estoque_usuario ON estoque_produtos(usuario_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mov_usuario ON estoque_movimentacoes(usuario_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_auditoria_usuario ON trilha_auditoria(usuario_id)")

    conn.commit()
    conn.close()
    auth.inicializar_tabela_usuarios(DB_PATH)


inicializar_banco()


def registrar_auditoria(
    usuario_id: Optional[int],
    usuario_nome: str,
    acao: str,
    detalhes: str,
    ip: str = "127.0.0.1",
) -> None:
    """Registra uma ação segura na trilha de auditoria sem gravar dados sensíveis."""
    try:
        conn = security.get_db_connection(DB_PATH)
        cursor = conn.cursor()
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        cursor.execute("""
            INSERT INTO trilha_auditoria (usuario_id, usuario_nome, acao, detalhes, ip, data_hora)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (usuario_id, usuario_nome or "Sistema", acao, detalhes, ip or "127.0.0.1", data_hora))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Auditoria] Falha ao registrar evento: {e}")


# ==========================================
# 5. PROCESSAMENTO DE XML E RATEIO FISCAL
# ==========================================
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
            "id": f"{codigo}_{datetime.now().timestamp()}",
            "codigo": codigo,
            "produto": descricao,
            "unidade": unidade,
            "quantidade": float(quantidade),
            "valor_produtos": float(valor_produto),
            "custo_unitario_original": float(valor_unitario),
            "frete": float(frete),
            "seguro": float(seguro),
            "desconto": float(desconto),
            "outras_despesas": float(outras_despesas),
            "icms": float(impostos["ICMS"]),
            "icms_st": float(impostos["ICMS ST"]),
            "fcp": float(impostos["FCP"]),
            "fcp_st": float(impostos["FCP ST"]),
            "ipi": float(impostos["IPI"]),
            "ii": float(impostos["II"]),
            "pis": float(impostos["PIS"]),
            "cofins": float(impostos["COFINS"]),
            "impostos_incluidos": float(total_impostos_incluidos),
            "custo_base_final": float(custo_final),
            "custo_unitario_final": float(custo_unitario_final),
            "unidades_por_embalagem": 1.0,
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


def nome_arquivo_padronizado(chave: str, metadados: Dict[str, Any], usuario_id: int) -> str:
    numero = "".join(c for c in str(metadados.get("numero", "")) if c.isdigit()) or "SN"
    data = metadados.get("data_emissao", "")
    data_compacta = data.replace("-", "") if data else "sem-data"
    return f"u{usuario_id}_{data_compacta}_NFe{numero}_{chave}.xml"


# ==========================================
# 6. MODELOS PYDANTIC RIGOROSOS (VALIDAÇÃO OWASP)
# ==========================================
class LoginRequest(BaseModel):
    identificador: str = Field(..., min_length=3, max_length=100)
    senha: str = Field(..., min_length=1, max_length=128)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10)


class CadastroRequest(BaseModel):
    usuario: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_\.\-]+$")
    nome: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    senha: str = Field(..., min_length=10, max_length=128)
    empresa: Optional[str] = Field("", max_length=100)
    cargo: Optional[str] = Field("", max_length=100)


class PerfilUpdateRequest(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    empresa: Optional[str] = Field("", max_length=100)
    cargo: Optional[str] = Field("", max_length=100)
    markup_padrao: float = Field(60.0, ge=0.0, le=5000.0)
    custo_adicional_padrao: float = Field(0.0, ge=0.0, le=1000000.0)
    impostos_padrao: List[str] = Field(default_factory=lambda: ["ICMS ST", "FCP ST", "IPI", "II"])


class AlterarSenhaRequest(BaseModel):
    senha_atual: str = Field(..., min_length=1, max_length=128)
    nova_senha: str = Field(..., min_length=10, max_length=128)


class CalculoRequest(BaseModel):
    produtos: List[Dict[str, Any]]
    markup: float = Field(..., ge=0.0, le=5000.0)
    custo_adicional_unitario: float = Field(0.0, ge=0.0, le=1000000.0)
    impostos_selecionados: List[str]
    unidades_por_embalagem: Dict[str, float]


class EstoqueItemRequest(BaseModel):
    id: Optional[int] = None
    codigo: str = Field(..., min_length=1, max_length=60)
    produto: str = Field(..., min_length=1, max_length=200)
    unidade: Optional[str] = Field("UN", max_length=20)
    quantidade_atual: float = Field(0.0, ge=0.0, le=10000000.0)
    estoque_minimo: float = Field(5.0, ge=0.0, le=10000000.0)
    custo_unitario: float = Field(0.0, ge=0.0, le=100000000.0)
    preco_venda: float = Field(0.0, ge=0.0, le=100000000.0)
    fornecedor_ultimo: Optional[str] = Field("", max_length=150)
    categoria: Optional[str] = Field("Geral", max_length=100)


class MovimentacaoRequest(BaseModel):
    produto_id: int
    tipo: str = Field(..., pattern=r"^(ENTRADA|SAIDA|AJUSTE|entrada|saida|ajuste)$")
    quantidade: float = Field(..., ge=0.000001, le=10000000.0)
    motivo: Optional[str] = Field("", max_length=200)
    documento_ref: Optional[str] = Field("", max_length=100)


class IncorporarNfeRequest(BaseModel):
    produtos: List[Dict[str, Any]]
    numero_nota: Optional[str] = Field("", max_length=50)


class AuditoriaLogRequest(BaseModel):
    acao: str = Field(..., min_length=1, max_length=60)
    detalhes: str = Field(..., min_length=1, max_length=500)


# ==========================================
# 7. ENDPOINTS DE AUTENTICAÇÃO COM JWT E RATE LIMITING
# ==========================================
@app.post("/api/auth/register")
def register(req: CadastroRequest, request: Request):
    ip = request.client.host if request.client else "127.0.0.1"
    sucesso, msg = auth.cadastrar_usuario(
        usuario=req.usuario,
        nome=req.nome,
        email=req.email,
        senha=req.senha,
        empresa=req.empresa or "",
        cargo=req.cargo or "",
    )
    if not sucesso:
        registrar_auditoria(None, req.usuario, "CADASTRO_FALHA", f"Tentativa falhou: {msg}", ip)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    registrar_auditoria(None, req.nome, "CADASTRO_SUCESSO", f"Novo usuário '{req.usuario}' registrado.", ip)
    return {"message": msg}


@app.post("/api/auth/login")
def login(req: LoginRequest, request: Request):
    ip = security.obter_ip_cliente(request)

    # Verificação de Brute Force / Rate Limit
    bloqueado, segundos_restantes = security.login_rate_limiter.verificar_limite(ip, req.identificador)
    if bloqueado:
        minutos = max(1, segundos_restantes // 60)
        registrar_auditoria(
            None, req.identificador, "BLOQUEIO_BRUTE_FORCE",
            f"Tentativa de login bloqueada por limite de falhas. Restam {segundos_restantes}s.", ip
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Muitas tentativas falhas. Acesso bloqueado temporariamente por {minutos} minuto(s).",
        )

    sucesso, resultado = auth.autenticar_usuario(req.identificador, req.senha)
    if not sucesso:
        security.login_rate_limiter.registrar_tentativa(ip, req.identificador, sucesso=False)
        registrar_auditoria(None, req.identificador, "LOGIN_FALHA", "Tentativa de login incorreta.", ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário ou senha inválidos.")

    # Sucesso no login: reseta falhas e emite tokens JWT
    security.login_rate_limiter.registrar_tentativa(ip, req.identificador, sucesso=True)
    access_token = security.create_access_token(user_id=resultado["id"], username=resultado["usuario"])
    refresh_token = security.create_refresh_token(user_id=resultado["id"])

    registrar_auditoria(resultado["id"], resultado["nome"], "LOGIN_SUCESSO", "Login realizado com sucesso.", ip)

    return {
        "user": resultado,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@app.post("/api/auth/refresh")
def refresh_token(req: RefreshTokenRequest):
    payload = security.decode_token(req.refresh_token, expected_type="refresh")
    user_id = int(payload["sub"])

    user = auth.obter_usuario_por_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado.")

    new_access_token = security.create_access_token(user_id=user["id"], username=user["usuario"])
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
    }


@app.post("/api/auth/logout")
def logout(request: Request, current_user: Dict[str, Any] = Depends(security.get_current_user)):
    ip = request.client.host if request.client else "127.0.0.1"
    registrar_auditoria(current_user["id"], current_user["nome"], "LOGOUT", "Sessão encerrada pelo usuário.", ip)
    return {"message": "Sessão encerrada com sucesso."}


@app.get("/api/auth/me")
def get_me(current_user: Dict[str, Any] = Depends(security.get_current_user)):
    return {"user": current_user}


@app.get("/api/auth/me/{usuario_id}")
def get_me_by_id(usuario_id: int, current_user: Dict[str, Any] = Depends(security.get_current_user)):
    # Previne BOLA: só permite consultar os próprios dados
    if current_user["id"] != usuario_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso não autorizado aos dados de outro usuário.")
    return {"user": current_user}


@app.put("/api/auth/profile")
def update_profile(
    req: PerfilUpdateRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(security.get_current_user),
):
    ip = request.client.host if request.client else "127.0.0.1"
    # REGRA: Nunca confiar em usuario_id vindo do cliente; usar o ID do token autenticado
    sucesso, msg = auth.atualizar_perfil(
        usuario_id=current_user["id"],
        nome=req.nome,
        email=req.email,
        empresa=req.empresa or "",
        cargo=req.cargo or "",
        markup_padrao=req.markup_padrao,
        custo_adicional_padrao=req.custo_adicional_padrao,
        impostos_padrao=req.impostos_padrao,
    )
    if not sucesso:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    registrar_auditoria(current_user["id"], req.nome, "ATUALIZACAO_PERFIL", "Perfil e preferências atualizados.", ip)
    updated_user = auth.obter_usuario_por_id(current_user["id"])
    return {"message": msg, "user": updated_user}


@app.post("/api/auth/change-password")
def change_password(
    req: AlterarSenhaRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(security.get_current_user),
):
    ip = request.client.host if request.client else "127.0.0.1"
    sucesso, msg = auth.alterar_senha(
        usuario_id=current_user["id"],
        senha_atual=req.senha_atual,
        nova_senha=req.nova_senha,
    )
    if not sucesso:
        registrar_auditoria(current_user["id"], current_user["nome"], "ALTERACAO_SENHA_FALHA", f"Falha: {msg}", ip)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    registrar_auditoria(current_user["id"], current_user["nome"], "ALTERACAO_SENHA_SUCESSO", "Senha alterada com sucesso.", ip)
    return {"message": msg}


# ==========================================
# 8. ENDPOINTS DE NF-E COM UPLOAD SEGURO
# ==========================================
@app.post("/api/nfe/upload")
async def upload_xmls(
    request: Request,
    files: List[UploadFile] = File(...),
    impostos_selecionados: Optional[str] = Form("[\"ICMS ST\", \"FCP ST\", \"IPI\", \"II\"]"),
    current_user: Dict[str, Any] = Depends(security.get_current_user),
):
    ip = request.client.host if request.client else "127.0.0.1"

    # Validação de quantidade máxima de arquivos
    if len(files) > security.MAX_FILES_PER_UPLOAD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limite de no máximo {security.MAX_FILES_PER_UPLOAD} arquivos por envio excedido.",
        )

    try:
        impostos_ativos = json.loads(impostos_selecionados) if impostos_selecionados else ["ICMS ST", "FCP ST", "IPI", "II"]
    except Exception:
        impostos_ativos = ["ICMS ST", "FCP ST", "IPI", "II"]

    # Carrega histórico exclusivo do usuário autenticado
    conn = security.get_db_connection(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT chave_acesso FROM historico_nfe WHERE usuario_id = ?", (current_user["id"],))
    chaves_usuario = {row["chave_acesso"] for row in cursor.fetchall()}
    conn.close()

    todos_produtos = []
    avisos = []
    erros = []
    notas_processadas = []

    for file in files:
        # Validação da extensão
        ext = os.path.splitext(file.filename)[1].lower()
        if ext != ".xml":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Arquivo rejeitado: '{file.filename}'. Apenas arquivos .xml são permitidos.",
            )

        conteudo_bytes = await file.read()

        # Validações de segurança do conteúdo XML (tamanho máximo, DTD/XXE)
        security.validar_conteudo_xml(conteudo_bytes)
        try:
            root = ET.fromstring(conteudo_bytes)
        except Exception as erro:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Erro ao analisar XML de {file.filename}: {erro}",
            )

        chave_acesso = obter_chave_acesso(root)
        metadados = obter_metadados_nfe(root)

        if chave_acesso and chave_acesso in chaves_usuario:
            avisos.append(f"Nota {metadados.get('numero', '')} ({file.filename}) já havia sido importada anteriormente.")
            continue

        produtos = localizar_produtos(root, impostos_ativos)
        if not produtos:
            erros.append(f"Nenhum produto foi localizado no arquivo {file.filename}.")
            continue

        # Sanitização do nome original para prevenir Path Traversal
        nome_original_sanitizado = security.sanitizar_nome_arquivo(file.filename)

        for prod in produtos:
            prod["arquivo_xml"] = nome_original_sanitizado
            prod["chave_acesso"] = chave_acesso or ""
            prod["numero_nota"] = metadados.get("numero", "")
            prod["fornecedor"] = metadados.get("fornecedor", "")

        todos_produtos.extend(produtos)

        if chave_acesso:
            nome_salvo = nome_arquivo_padronizado(chave_acesso, metadados, current_user["id"])
            caminho_salvo = os.path.join(PASTA_XMLS_PROCESSADOS, nome_salvo)
            with open(caminho_salvo, "wb") as f_out:
                f_out.write(conteudo_bytes)

            nova_nota = {
                "chave_acesso": chave_acesso,
                "numero": metadados.get("numero", ""),
                "serie": metadados.get("serie", ""),
                "data_emissao": metadados.get("data_emissao", ""),
                "fornecedor": metadados.get("fornecedor", ""),
                "cnpj_emit": metadados.get("cnpj_emit", ""),
                "valor_total": metadados.get("valor_total", 0),
                "arquivo_original": nome_original_sanitizado,
                "arquivo_salvo": nome_salvo,
                "data_importacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "usuario_id": current_user["id"],
            }

            conn = security.get_db_connection(DB_PATH)
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO historico_nfe 
                (chave_acesso, numero, serie, data_emissao, fornecedor, cnpj_emit, valor_total, arquivo_original, arquivo_salvo, data_importacao, usuario_id)
                VALUES (:chave_acesso, :numero, :serie, :data_emissao, :fornecedor, :cnpj_emit, :valor_total, :arquivo_original, :arquivo_salvo, :data_importacao, :usuario_id)
            """, nova_nota)
            conn.commit()
            conn.close()

            notas_processadas.append(nova_nota)
            chaves_usuario.add(chave_acesso)

    if notas_processadas or todos_produtos:
        registrar_auditoria(
            current_user["id"],
            current_user["nome"],
            "IMPORTACAO_NFE",
            f"Importação de {len(notas_processadas)} NF-e(s) e {len(todos_produtos)} produto(s) localizado(s).",
            ip,
        )

    return {
        "produtos": todos_produtos,
        "novas_notas": notas_processadas,
        "avisos": avisos,
        "erros": erros,
    }


@app.post("/api/nfe/calculate")
def recalculate(req: CalculoRequest, current_user: Dict[str, Any] = Depends(security.get_current_user)):
    produtos_calculados = []
    fator_markup = 1 + (req.markup / 100)

    for item in req.produtos:
        item_id = str(item.get("id", ""))
        unidades_embalagem = float(req.unidades_por_embalagem.get(item_id, item.get("unidades_por_embalagem", 1.0)))
        if unidades_embalagem <= 0:
            unidades_embalagem = 1.0

        qtd_original = float(item.get("quantidade", 1.0))
        valor_prod = float(item.get("valor_produtos", 0.0))
        frete = float(item.get("frete", 0.0))
        seguro = float(item.get("seguro", 0.0))
        desconto = float(item.get("desconto", 0.0))
        outras = float(item.get("outras_despesas", 0.0))

        impostos_map = {
            "ICMS": float(item.get("icms", 0.0)),
            "ICMS ST": float(item.get("icms_st", 0.0)),
            "FCP": float(item.get("fcp", 0.0)),
            "FCP ST": float(item.get("fcp_st", 0.0)),
            "IPI": float(item.get("ipi", 0.0)),
            "II": float(item.get("ii", 0.0)),
            "PIS": float(item.get("pis", 0.0)),
            "COFINS": float(item.get("cofins", 0.0)),
        }

        impostos_somados = sum(val for nome_imp, val in impostos_map.items() if nome_imp in req.impostos_selecionados)

        custo_base = valor_prod + frete + seguro + outras + impostos_somados - desconto
        quantidade_real = qtd_original * unidades_embalagem
        custo_adicional_total = quantidade_real * req.custo_adicional_unitario
        custo_final_total = custo_base + custo_adicional_total

        custo_unitario_final = custo_final_total / quantidade_real if quantidade_real > 0 else 0.0
        preco_revenda_unitario = custo_unitario_final * fator_markup
        total_revenda = quantidade_real * preco_revenda_unitario
        lucro_unitario = preco_revenda_unitario - custo_unitario_final
        lucro_total = quantidade_real * lucro_unitario
        margem_lucro_pct = (lucro_unitario / preco_revenda_unitario * 100) if preco_revenda_unitario > 0 else 0.0

        p_calc = dict(item)
        p_calc.update({
            "unidades_por_embalagem": unidades_embalagem,
            "quantidade_real": round(quantidade_real, 2),
            "impostos_incluidos": round(impostos_somados, 2),
            "custo_adicional_total": round(custo_adicional_total, 2),
            "custo_final": round(custo_final_total, 2),
            "custo_unitario_final": round(custo_unitario_final, 2),
            "preco_revenda_unitario": round(preco_revenda_unitario, 2),
            "total_revenda": round(total_revenda, 2),
            "lucro_unitario": round(lucro_unit, 2),
            "lucro_total": round(lucro_total, 2),
            "margem_lucro_pct": round(margem_lucro_pct, 2),
        })
        produtos_calculados.append(p_calc)

    total_custo = sum(p["custo_final"] for p in produtos_calculados)
    total_faturamento = sum(p["total_revenda"] for p in produtos_calculados)
    total_lucro = sum(p["lucro_total"] for p in produtos_calculados)
    total_impostos = sum(p["impostos_incluidos"] for p in produtos_calculados)
    total_frete = sum(p.get("frete", 0.0) for p in produtos_calculados)
    margem_media = (total_lucro / total_faturamento * 100) if total_faturamento > 0 else 0.0

    return {
        "produtos": produtos_calculados,
        "resumo": {
            "total_itens": len(produtos_calculados),
            "total_custo": round(total_custo, 2),
            "total_faturamento": round(total_faturamento, 2),
            "total_lucro": round(total_lucro, 2),
            "total_impostos": round(total_impostos, 2),
            "total_frete": round(total_frete, 2),
            "margem_media_pct": round(margem_media, 2),
        }
    }


@app.get("/api/nfe/history")
def get_history(current_user: Dict[str, Any] = Depends(security.get_current_user)):
    # Isolamento estrito de dados por usuário autenticado
    conn = security.get_db_connection(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM historico_nfe 
        WHERE usuario_id = ? 
        ORDER BY data_importacao DESC
    """, (current_user["id"],))
    notas = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"notas": notas}


@app.post("/api/nfe/export-csv")
def export_csv(
    produtos: List[Dict[str, Any]],
    request: Request,
    current_user: Dict[str, Any] = Depends(security.get_current_user),
):
    df = pd.DataFrame(produtos)
    mapeamento_colunas = {
        "codigo": "Código",
        "produto": "Produto",
        "unidade": "Unidade Original",
        "quantidade": "Qtd NF-e",
        "unidades_por_embalagem": "Unidades / Embalagem",
        "quantidade_real": "Qtd Real para Venda",
        "valor_produtos": "Valor dos Produtos (R$)",
        "custo_unitario_original": "Custo Unitário Original (R$)",
        "frete": "Frete (R$)",
        "seguro": "Seguro (R$)",
        "desconto": "Desconto (R$)",
        "outras_despesas": "Outras Despesas (R$)",
        "impostos_incluidos": "Total Impostos no Custo (R$)",
        "custo_adicional_total": "Custo Adicional Total (R$)",
        "custo_final": "Custo Final Total (R$)",
        "custo_unitario_final": "Custo Unitário Final (R$)",
        "preco_revenda_unitario": "Preço de Venda Sugerido (R$)",
        "total_revenda": "Faturamento Estimado (R$)",
        "lucro_unitario": "Lucro Unitário (R$)",
        "lucro_total": "Lucro Total Estimado (R$)",
        "margem_lucro_pct": "Margem de Lucro (%)",
        "arquivo_xml": "Arquivo XML",
        "fornecedor": "Fornecedor",
        "numero_nota": "NF-e Nº",
    }

    colunas_presentes = [c for c in mapeamento_colunas.keys() if c in df.columns]
    df_export = df[colunas_presentes].rename(columns=mapeamento_colunas)

    csv_buffer = io.StringIO()
    df_export.to_csv(csv_buffer, index=False, sep=";", decimal=",", encoding="utf-8-sig")

    ip = request.client.host if request and request.client else "127.0.0.1"
    registrar_auditoria(current_user["id"], current_user["nome"], "EXPORTACAO_CSV_PRECIFICACAO", f"Planilha de {len(produtos)} item(ns) gerada.", ip)

    return Response(
        content=csv_buffer.getvalue().encode("utf-8-sig"),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=precificacao_produtos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )


# ==========================================
# 9. ENDPOINTS DE GESTÃO DE ESTOQUE (PROTEGIDOS)
# ==========================================
@app.get("/api/estoque")
def get_estoque(
    status_filtro: Optional[str] = None,
    busca: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(security.get_current_user),
):
    conn = security.get_db_connection(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM estoque_produtos 
        WHERE usuario_id = ? 
        ORDER BY produto ASC
    """, (current_user["id"],))
    todos = [dict(r) for r in cursor.fetchall()]
    conn.close()

    produtos_formatados = []
    totais = {
        "total_itens": len(todos),
        "itens_normais": 0,
        "itens_baixos": 0,
        "itens_zerados": 0,
        "valor_total_custo": 0.0,
        "valor_total_venda": 0.0,
        "lucro_potencial": 0.0,
    }

    termo_busca = (busca or "").strip().lower()

    for p in todos:
        qtd = float(p.get("quantidade_atual") or 0.0)
        minimo = float(p.get("estoque_minimo") or 5.0)
        custo = float(p.get("custo_unitario") or 0.0)
        venda = float(p.get("preco_venda") or 0.0)

        if qtd <= 0:
            st = "zerado"
            totais["itens_zerados"] += 1
        elif qtd <= minimo:
            st = "baixo"
            totais["itens_baixos"] += 1
        else:
            st = "normal"
            totais["itens_normais"] += 1

        val_custo = qtd * custo
        val_venda = qtd * venda
        lucro_item = val_venda - val_custo

        totais["valor_total_custo"] += val_custo
        totais["valor_total_venda"] += val_venda
        totais["lucro_potencial"] += lucro_item

        p["status_estoque"] = st
        p["valor_total_custo"] = round(val_custo, 2)
        p["valor_total_venda"] = round(val_venda, 2)
        p["lucro_potencial"] = round(lucro_item, 2)
        p["margem_lucro_pct"] = round(((venda - custo) / venda * 100), 2) if venda > 0 else 0.0
        p["quantidade_repor"] = round(max(0.0, (minimo * 1.5) - qtd), 2) if qtd <= minimo else 0.0

        if status_filtro and status_filtro != "todos" and st != status_filtro:
            continue

        if termo_busca:
            cod = str(p.get("codigo") or "").lower()
            prod = str(p.get("produto") or "").lower()
            forn = str(p.get("fornecedor_ultimo") or "").lower()
            cat = str(p.get("categoria") or "").lower()
            if termo_busca not in cod and termo_busca not in prod and termo_busca not in forn and termo_busca not in cat:
                continue

        produtos_formatados.append(p)

    totais["valor_total_custo"] = round(totais["valor_total_custo"], 2)
    totais["valor_total_venda"] = round(totais["valor_total_venda"], 2)
    totais["lucro_potencial"] = round(totais["lucro_potencial"], 2)
    totais["margem_media_pct"] = round((totais["lucro_potencial"] / totais["valor_total_venda"] * 100), 2) if totais["valor_total_venda"] > 0 else 0.0

    return {
        "produtos": produtos_formatados,
        "resumo": totais,
    }


@app.post("/api/estoque/item")
def save_estoque_item(
    req: EstoqueItemRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(security.get_current_user),
):
    conn = security.get_db_connection(DB_PATH)
    cursor = conn.cursor()
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ip = request.client.host if request.client else "127.0.0.1"

    if req.id:
        # Previne BOLA: valida se o item a ser editado pertence ao usuário logado
        cursor.execute("SELECT id FROM estoque_produtos WHERE id = ? AND usuario_id = ?", (req.id, current_user["id"]))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado no seu estoque.")

        cursor.execute("""
            UPDATE estoque_produtos SET
                codigo = ?, produto = ?, unidade = ?, quantidade_atual = ?,
                estoque_minimo = ?, custo_unitario = ?, preco_venda = ?,
                fornecedor_ultimo = ?, categoria = ?, atualizado_em = ?
            WHERE id = ? AND usuario_id = ?
        """, (
            req.codigo.strip(), req.produto.strip(), req.unidade.strip() or "UN",
            float(req.quantidade_atual), float(req.estoque_minimo),
            float(req.custo_unitario), float(req.preco_venda),
            req.fornecedor_ultimo or "", req.categoria or "Geral", agora, req.id, current_user["id"]
        ))
        conn.commit()
        conn.close()

        registrar_auditoria(
            current_user["id"], current_user["nome"], "EDICAO_ESTOQUE_ITEM",
            f"Item '{req.produto}' (Cód: {req.codigo}) editado.", ip
        )
        return {"message": "Produto de estoque atualizado com sucesso!"}
    else:
        try:
            cursor.execute("""
                INSERT INTO estoque_produtos (
                    codigo, produto, unidade, quantidade_atual, estoque_minimo,
                    custo_unitario, preco_venda, fornecedor_ultimo, categoria,
                    usuario_id, criado_em, atualizado_em
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                req.codigo.strip(), req.produto.strip(), req.unidade.strip() or "UN",
                float(req.quantidade_atual), float(req.estoque_minimo),
                float(req.custo_unitario), float(req.preco_venda),
                req.fornecedor_ultimo or "", req.categoria or "Geral",
                current_user["id"], agora, agora
            ))
            novo_id = cursor.lastrowid

            if req.quantidade_atual > 0:
                cursor.execute("""
                    INSERT INTO estoque_movimentacoes (
                        produto_id, codigo, tipo, quantidade, quantidade_anterior, quantidade_nova,
                        motivo, documento_ref, usuario_id, usuario_nome, data_hora
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    novo_id, req.codigo.strip(), "ENTRADA", float(req.quantidade_atual),
                    0.0, float(req.quantidade_atual), "Saldo Inicial", "Cadastro manual",
                    current_user["id"], current_user["nome"], agora
                ))

            conn.commit()
            conn.close()

            registrar_auditoria(
                current_user["id"], current_user["nome"], "CADASTRO_ESTOQUE_ITEM",
                f"Novo item '{req.produto}' cadastrado com saldo de {req.quantidade_atual}.", ip
            )
            return {"message": "Produto cadastrado com sucesso no estoque!", "id": novo_id}
        except sqlite3.IntegrityError:
            conn.close()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Já existe um produto com este código cadastrado em seu estoque.")


@app.delete("/api/estoque/{produto_id}")
def delete_estoque_item(
    produto_id: int,
    request: Request,
    current_user: Dict[str, Any] = Depends(security.get_current_user),
):
    conn = security.get_db_connection(DB_PATH)
    cursor = conn.cursor()
    # Valida ownership estrito
    cursor.execute("SELECT codigo, produto FROM estoque_produtos WHERE id = ? AND usuario_id = ?", (produto_id, current_user["id"]))
    item = cursor.fetchone()
    if not item:
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado no seu estoque.")

    codigo, produto = item[0], item[1]
    cursor.execute("DELETE FROM estoque_produtos WHERE id = ? AND usuario_id = ?", (produto_id, current_user["id"]))
    cursor.execute("DELETE FROM estoque_movimentacoes WHERE produto_id = ? AND usuario_id = ?", (produto_id, current_user["id"]))
    conn.commit()
    conn.close()

    ip = request.client.host if request and request.client else "127.0.0.1"
    registrar_auditoria(current_user["id"], current_user["nome"], "EXCLUSAO_ESTOQUE_ITEM", f"Produto '{produto}' ({codigo}) removido.", ip)
    return {"message": "Produto removido do estoque com sucesso!"}


@app.post("/api/estoque/movimentar")
def movimentar_estoque(
    req: MovimentacaoRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(security.get_current_user),
):
    conn = security.get_db_connection(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Previne BOLA: valida se o produto pertence ao usuário logado
    cursor.execute("SELECT * FROM estoque_produtos WHERE id = ? AND usuario_id = ?", (req.produto_id, current_user["id"]))
    item = cursor.fetchone()
    if not item:
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não localizado em seu estoque.")

    prod_dict = dict(item)
    qtd_anterior = float(prod_dict["quantidade_atual"])
    tipo = req.tipo.upper()
    qtd_mov = float(req.quantidade)

    if tipo == "ENTRADA":
        qtd_nova = qtd_anterior + qtd_mov
    elif tipo == "SAIDA":
        if qtd_mov > qtd_anterior:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Saldo insuficiente! Saldo atual em estoque: {qtd_anterior}, tentativa de saída: {qtd_mov}",
            )
        qtd_nova = qtd_anterior - qtd_mov
    elif tipo == "AJUSTE":
        qtd_nova = qtd_mov
    else:
        conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de movimentação inválido.")

    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    cursor.execute(
        "UPDATE estoque_produtos SET quantidade_atual = ?, atualizado_em = ? WHERE id = ? AND usuario_id = ?",
        (qtd_nova, agora, req.produto_id, current_user["id"]),
    )

    cursor.execute("""
        INSERT INTO estoque_movimentacoes (
            produto_id, codigo, tipo, quantidade, quantidade_anterior, quantidade_nova,
            motivo, documento_ref, usuario_id, usuario_nome, data_hora
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        req.produto_id, prod_dict["codigo"], tipo, qtd_mov,
        qtd_anterior, qtd_nova, req.motivo or "Movimentação manual", req.documento_ref or "",
        current_user["id"], current_user["nome"], agora
    ))
    conn.commit()
    conn.close()

    ip = request.client.host if request.client else "127.0.0.1"
    registrar_auditoria(
        current_user["id"], current_user["nome"], f"MOVIMENTACAO_{tipo}",
        f"{tipo} de {qtd_mov} un no item '{prod_dict['produto']}'. Saldo: {qtd_anterior} -> {qtd_nova}.", ip
    )

    return {
        "message": f"Movimentação de {tipo} registrada com sucesso!",
        "quantidade_anterior": qtd_anterior,
        "quantidade_nova": qtd_nova,
    }


@app.post("/api/estoque/incorporar-nfe")
def incorporar_nfe(
    req: IncorporarNfeRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(security.get_current_user),
):
    conn = security.get_db_connection(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    incorporados_contagem = 0

    for item in req.produtos:
        codigo = str(item.get("codigo", "")).strip()
        produto_nome = str(item.get("produto", "")).strip()
        unidade = str(item.get("unidade", "UN")).strip()
        qtd_entrada = max(0.0, float(item.get("quantidade_real", item.get("quantidade", 0.0))))
        custo_unitario = max(0.0, float(item.get("custo_unitario_final", item.get("custo_unitario_original", 0.0))))
        preco_venda = max(0.0, float(item.get("preco_revenda_unitario", 0.0)))
        fornecedor = str(item.get("fornecedor", "")).strip()

        if not codigo or not produto_nome:
            continue

        cursor.execute(
            "SELECT * FROM estoque_produtos WHERE codigo = ? AND usuario_id = ?",
            (codigo, current_user["id"]),
        )
        existente = cursor.fetchone()

        if existente:
            p_id = existente["id"]
            qtd_anterior = float(existente["quantidade_atual"])
            qtd_nova = qtd_anterior + qtd_entrada

            cursor.execute("""
                UPDATE estoque_produtos SET
                    quantidade_atual = ?,
                    custo_unitario = ?,
                    preco_venda = ?,
                    fornecedor_ultimo = ?,
                    atualizado_em = ?
                WHERE id = ? AND usuario_id = ?
            """, (
                qtd_nova,
                custo_unitario if custo_unitario > 0 else existente["custo_unitario"],
                preco_venda if preco_venda > 0 else existente["preco_venda"],
                fornecedor or existente["fornecedor_ultimo"],
                agora,
                p_id,
                current_user["id"],
            ))

            cursor.execute("""
                INSERT INTO estoque_movimentacoes (
                    produto_id, codigo, tipo, quantidade, quantidade_anterior, quantidade_nova,
                    motivo, documento_ref, usuario_id, usuario_nome, data_hora
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p_id, codigo, "ENTRADA", qtd_entrada, qtd_anterior, qtd_nova,
                "Incorporação de NF-e", f"NF-e {req.numero_nota or ''}",
                current_user["id"], current_user["nome"], agora
            ))
        else:
            cursor.execute("""
                INSERT INTO estoque_produtos (
                    codigo, produto, unidade, quantidade_atual, estoque_minimo,
                    custo_unitario, preco_venda, fornecedor_ultimo, categoria,
                    usuario_id, criado_em, atualizado_em
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                codigo, produto_nome, unidade, qtd_entrada, 5.0,
                custo_unitario, preco_venda, fornecedor, "Geral",
                current_user["id"], agora, agora
            ))
            novo_id = cursor.lastrowid
            cursor.execute("""
                INSERT INTO estoque_movimentacoes (
                    produto_id, codigo, tipo, quantidade, quantidade_anterior, quantidade_nova,
                    motivo, documento_ref, usuario_id, usuario_nome, data_hora
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                novo_id, codigo, "ENTRADA", qtd_entrada, 0.0, qtd_entrada,
                "Entrada inicial NF-e", f"NF-e {req.numero_nota or ''}",
                current_user["id"], current_user["nome"], agora
            ))

        incorporados_contagem += 1

    conn.commit()
    conn.close()

    ip = request.client.host if request.client else "127.0.0.1"
    registrar_auditoria(
        current_user["id"], current_user["nome"], "INCORPORACAO_ESTOQUE",
        f"Incorporados {incorporados_contagem} itens da NF-e {req.numero_nota or 'N/A'} ao estoque.", ip
    )

    return {
        "message": f"{incorporados_contagem} produto(s) incorporado(s) ao estoque com sucesso!",
        "total_incorporados": incorporados_contagem,
    }


@app.get("/api/estoque/movimentacoes")
def get_movimentacoes(
    produto_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=500),
    current_user: Dict[str, Any] = Depends(security.get_current_user),
):
    conn = security.get_db_connection(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = """
        SELECT m.*, p.produto as nome_produto, p.unidade 
        FROM estoque_movimentacoes m
        LEFT JOIN estoque_produtos p ON m.produto_id = p.id
        WHERE m.usuario_id = ?
    """
    params = [current_user["id"]]

    if produto_id is not None:
        query += " AND m.produto_id = ?"
        params.append(produto_id)

    query += " ORDER BY m.id DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, tuple(params))
    linhas = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"movimentacoes": linhas}


# ==========================================
# 10. ENDPOINTS DE RELATÓRIOS & ANALYTICS (PROTEGIDOS)
# ==========================================
@app.get("/api/relatorios/desempenho")
def get_relatorio_desempenho(current_user: Dict[str, Any] = Depends(security.get_current_user)):
    conn = security.get_db_connection(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM estoque_produtos 
        WHERE usuario_id = ? 
        ORDER BY produto ASC
    """, (current_user["id"],))
    produtos = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT m.*, p.produto as nome_produto 
        FROM estoque_movimentacoes m
        LEFT JOIN estoque_produtos p ON m.produto_id = p.id
        WHERE m.usuario_id = ?
        ORDER BY m.id DESC LIMIT 15
    """, (current_user["id"],))
    ultimas_mov = [dict(r) for r in cursor.fetchall()]
    conn.close()

    total_itens = len(produtos)
    total_unidades = 0.0
    valor_total_custo = 0.0
    valor_total_venda = 0.0
    itens_baixo = 0
    itens_zerados = 0
    itens_normais = 0
    reposicao_sugerida = []
    produtos_analisados = []

    for p in produtos:
        qtd = float(p.get("quantidade_atual") or 0.0)
        minimo = float(p.get("estoque_minimo") or 5.0)
        custo = float(p.get("custo_unitario") or 0.0)
        venda = float(p.get("preco_venda") or 0.0)

        total_unidades += qtd
        custo_tot = qtd * custo
        venda_tot = qtd * venda
        valor_total_custo += custo_tot
        valor_total_venda += venda_tot

        lucro_unit = venda - custo
        lucro_tot = venda_tot - custo_tot
        margem_pct = (lucro_unit / venda * 100) if venda > 0 else 0.0

        if qtd <= 0:
            itens_zerados += 1
            st = "zerado"
        elif qtd <= minimo:
            itens_baixo += 1
            st = "baixo"
        else:
            itens_normais += 1
            st = "normal"

        produtos_analisados.append({
            "id": p["id"],
            "codigo": p["codigo"],
            "produto": p["produto"],
            "unidade": p.get("unidade", "UN"),
            "quantidade_atual": qtd,
            "estoque_minimo": minimo,
            "custo_unitario": custo,
            "preco_venda": venda,
            "lucro_unitario": round(lucro_unit, 2),
            "margem_pct": round(margem_pct, 2),
            "valor_investido": round(custo_tot, 2),
            "faturamento_projetado": round(venda_tot, 2),
            "lucro_projetado": round(lucro_tot, 2),
            "fornecedor": p.get("fornecedor_ultimo", ""),
            "status": st,
        })

        if qtd <= minimo:
            qtd_comprar = max(1.0, round((minimo * 1.5) - qtd, 2))
            reposicao_sugerida.append({
                "id": p["id"],
                "codigo": p["codigo"],
                "produto": p["produto"],
                "unidade": p.get("unidade", "UN"),
                "quantidade_atual": qtd,
                "estoque_minimo": minimo,
                "quantidade_sugerida": qtd_comprar,
                "custo_unitario": round(custo, 2),
                "custo_total_estimado": round(qtd_comprar * custo, 2),
                "fornecedor": p.get("fornecedor_ultimo", "Não informado"),
            })

    lucro_potencial = valor_total_venda - valor_total_custo
    margem_media = (lucro_potencial / valor_total_venda * 100) if valor_total_venda > 0 else 0.0
    total_custo_reposicao = sum(r["custo_total_estimado"] for r in reposicao_sugerida)

    top_lucrativos = sorted(produtos_analisados, key=lambda x: x["lucro_unitario"], reverse=True)[:10]
    top_capital = sorted(produtos_analisados, key=lambda x: x["valor_investido"], reverse=True)[:10]

    return {
        "metricas": {
            "total_itens": total_itens,
            "total_unidades": round(total_unidades, 2),
            "valor_total_custo": round(valor_total_custo, 2),
            "valor_total_venda": round(valor_total_venda, 2),
            "lucro_potencial": round(lucro_potencial, 2),
            "margem_media_pct": round(margem_media, 2),
            "itens_baixo_estoque": itens_baixo,
            "itens_esgotados": itens_zerados,
            "itens_normais": itens_normais,
            "total_custo_reposicao": round(total_custo_reposicao, 2),
            "itens_reposicao_qtd": len(reposicao_sugerida),
        },
        "top_lucrativos": top_lucrativos,
        "top_capital": top_capital,
        "reposicao_sugerida": reposicao_sugerida,
        "ultimas_movimentacoes": ultimas_mov,
    }


@app.get("/api/relatorios/reposicao-csv")
def download_reposicao_csv(
    request: Request,
    current_user: Dict[str, Any] = Depends(security.get_current_user),
):
    dados = get_relatorio_desempenho(current_user=current_user)
    lista = dados.get("reposicao_sugerida", [])

    if not lista:
        df = pd.DataFrame(columns=[
            "Código", "Produto", "Unidade", "Estoque Atual", "Estoque Mínimo",
            "Qtd Sugerida de Compra", "Custo Unitário (R$)", "Custo Total Estimado (R$)", "Fornecedor"
        ])
    else:
        df = pd.DataFrame(lista)
        mapa = {
            "codigo": "Código",
            "produto": "Produto",
            "unidade": "Unidade",
            "quantidade_atual": "Estoque Atual",
            "estoque_minimo": "Estoque Mínimo",
            "quantidade_sugerida": "Qtd Sugerida de Compra",
            "custo_unitario": "Custo Unitário (R$)",
            "custo_total_estimado": "Custo Total Estimado (R$)",
            "fornecedor": "Fornecedor",
        }
        df = df[[c for c in mapa.keys() if c in df.columns]].rename(columns=mapa)

    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, sep=";", decimal=",", encoding="utf-8-sig")

    ip = request.client.host if request and request.client else "127.0.0.1"
    registrar_auditoria(current_user["id"], current_user["nome"], "EXPORTACAO_RELATORIO_REPOSICAO", f"Exportado relatório com {len(lista)} item(ns).", ip)

    return Response(
        content=csv_buffer.getvalue().encode("utf-8-sig"),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=relatorio_reposicao_compras_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )


# ==========================================
# 11. ENDPOINTS DE TRILHA DE AUDITORIA (PROTEGIDOS)
# ==========================================
@app.get("/api/auditoria")
def get_auditoria(
    acao: Optional[str] = None,
    termo: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(security.get_current_user),
):
    conn = security.get_db_connection(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM trilha_auditoria WHERE usuario_id = ?"
    params = [current_user["id"]]

    if acao and acao != "TODAS":
        query += " AND acao LIKE ?"
        params.append(f"%{acao}%")

    if termo:
        query += " AND (detalhes LIKE ? OR acao LIKE ?)"
        termo_p = f"%{termo}%"
        params.extend([termo_p, termo_p])

    # Contagem total
    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    cursor.execute(count_query, tuple(params))
    total = cursor.fetchone()[0]

    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, tuple(params))
    logs = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {"logs": logs, "total": total}


@app.post("/api/auditoria/log")
def log_auditoria_evento(
    req: AuditoriaLogRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(security.get_current_user),
):
    ip = request.client.host if request.client else "127.0.0.1"
    # REGRA: usuário e id obtidos estritamente do token autenticado
    registrar_auditoria(
        current_user["id"],
        current_user["nome"],
        req.acao,
        req.detalhes,
        ip,
    )
    return {"status": "ok"}


@app.get("/api/auditoria/export-csv")
def export_auditoria_csv(
    acao: Optional[str] = None,
    termo: Optional[str] = None,
    request: Request = None,
    current_user: Dict[str, Any] = Depends(security.get_current_user),
):
    dados = get_auditoria(acao=acao, termo=termo, limit=5000, offset=0, current_user=current_user)
    logs = dados.get("logs", [])

    if not logs:
        df = pd.DataFrame(columns=["ID", "Data/Hora", "Usuário", "Ação", "Detalhes", "IP"])
    else:
        df = pd.DataFrame(logs)
        mapa = {
            "id": "ID",
            "data_hora": "Data/Hora",
            "usuario_nome": "Usuário",
            "acao": "Ação",
            "detalhes": "Detalhes",
            "ip": "IP",
        }
        df = df[[c for c in mapa.keys() if c in df.columns]].rename(columns=mapa)

    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, sep=";", decimal=",", encoding="utf-8-sig")

    ip = request.client.host if request and request.client else "127.0.0.1"
    registrar_auditoria(current_user["id"], current_user["nome"], "EXPORTACAO_TRILHA_AUDITORIA", f"Exportação de auditoria com {len(logs)} registros.", ip)

    return Response(
        content=csv_buffer.getvalue().encode("utf-8-sig"),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=trilha_auditoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )


# Servir build do frontend se existir
if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
