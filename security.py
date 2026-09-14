import os
import re
import secrets
import string
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import sqlite3

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError
    HAS_ARGON2 = True
    ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=1, hash_len=32)
except ImportError:
    HAS_ARGON2 = False
    ph = None

# Carrega variáveis de ambiente
load_dotenv()

# ==========================================
# CONFIGURAÇÕES DE SEGURANÇA E AMBIENTE
# ==========================================
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()

# Segredo criptográfico para assinatura dos tokens JWT
_SECRET_FROM_ENV = os.getenv("SECRET_KEY", "").strip()
if not _SECRET_FROM_ENV:
    # Se não configurado em dev, gera uma chave estável para a sessão com aviso
    _TEMP_SECRET = secrets.token_hex(32)
    SECRET_KEY = _TEMP_SECRET
    print("[AVISO DE SEGURANÇA] SECRET_KEY não definida em .env! Utilizando chave temporária de alta entropia.")
else:
    SECRET_KEY = _SECRET_FROM_ENV

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256").strip()
ALGORITHM = JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Limites de Brute-Force
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOGIN_LOCKOUT_MINUTES = int(os.getenv("LOGIN_LOCKOUT_MINUTES", "15"))

# Limites de Upload de XML
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
MAX_FILES_PER_UPLOAD = int(os.getenv("MAX_FILES_PER_UPLOAD", "20"))

# CORS
_ORIGINS_RAW = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:8000,http://127.0.0.1:5173,http://127.0.0.1:8000",
)
ALLOWED_ORIGINS = [orig.strip() for orig in _ORIGINS_RAW.split(",") if orig.strip()]

DB_PATH = os.getenv("DATABASE_PATH", "banco_notas.db")

# Esquema de autenticação Bearer
bearer_scheme = HTTPBearer(auto_error=False)


# ==========================================
# CONEXÃO SQLITE CENTRALIZADA (ANTI-LOCK)
# ==========================================
# Timeout alto + WAL: evita "database is locked" sob concorrência real,
# permitindo leitores e escritores conviverem sem se bloquearem mutuamente.
_SQLITE_TIMEOUT_SECONDS = float(os.getenv("SQLITE_TIMEOUT_SECONDS", "30"))
_wal_configurado: set = set()


def get_db_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """
    Cria uma conexão SQLite padronizada para todo o projeto, com:
    - timeout alto (evita estourar 'database is locked' em picos de concorrência)
    - modo WAL habilitado (permite leituras concorrentes com escrita em andamento)
    - busy_timeout no próprio SQLite (reforça o timeout também no nível do motor)
    """
    conn = sqlite3.connect(db_path, timeout=_SQLITE_TIMEOUT_SECONDS)
    if db_path not in _wal_configurado:
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            _wal_configurado.add(db_path)
        except sqlite3.Error:
            pass
    conn.execute(f"PRAGMA busy_timeout={int(_SQLITE_TIMEOUT_SECONDS * 1000)}")
    return conn


# ==========================================
# GESTÃO DE TOKENS JWT
# ==========================================
def create_access_token(user_id: int, username: str) -> str:
    """Gera um JWT Access Token com tempo de expiração curto."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "username": username,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """Gera um JWT Refresh Token de longa duração para renovação de sessão."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> Dict[str, Any]:
    """Valida a assinatura, algoritmo e expiração do token JWT."""
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "sub", "type"]},
        )
        if payload.get("type") != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Tipo de token inválido. Esperado '{expected_type}'.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão expirada. Faça login novamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação inválido ou corrompido.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Dict[str, Any]:
    """Dependency do FastAPI que autentica a requisição e retorna os dados do usuário autenticado."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária para acessar este recurso.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_token(token, expected_type="access")
    user_id_str = payload.get("sub")

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identificador de usuário inválido no token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Consulta usuário no banco
    conn = get_db_connection(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,))
    linha = cursor.fetchone()
    conn.close()

    if not linha:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário associado a este token não foi encontrado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_dict = dict(linha)
    # Remove credenciais sensíveis da memória
    user_dict.pop("senha_hash", None)
    user_dict.pop("salt", None)
    return user_dict


# ==========================================
# POLÍTICA DE SENHAS E HASHING CRIPTOGRÁFICO
# ==========================================
SENHAS_COMUNS_PROIBIDAS = {
    "123456", "12345678", "password", "senha123", "admin123",
    "qwerty", "1234567890", "teste123", "mudar123", "brasil123",
    "gestao123", "senha1234", "admin1234", "master123",
}


def validar_politica_senha(senha: str) -> Tuple[bool, str]:
    """
    Verifica se a senha atende aos requisitos rigorosos do OWASP:
    - No mínimo 10 caracteres
    - Pelo menos uma letra maiúscula
    - Pelo menos uma letra minúscula
    - Pelo menos um número
    - Pelo menos um caractere especial
    - Não constar na lista de senhas comuns
    """
    if len(senha) < 10:
        return False, "A senha deve conter no mínimo 10 caracteres."

    if senha.lower() in SENHAS_COMUNS_PROIBIDAS:
        return False, "Esta senha é muito comum e insegura. Escolha uma senha mais forte."

    tem_maiuscula = any(c.isupper() for c in senha)
    tem_minuscula = any(c.islower() for c in senha)
    tem_numero = any(c.isdigit() for c in senha)
    tem_especial = any(c in string.punctuation for c in senha)

    if not (tem_maiuscula and tem_minuscula and tem_numero and tem_especial):
        return (
            False,
            "A senha deve conter letras maiúsculas, minúsculas, números e caracteres especiais.",
        )

    return True, "Senha válida."


def gerar_hash_senha_seguro(senha: str) -> Tuple[str, str]:
    """
    Gera hash seguro utilizando Argon2id (algoritmo preferencial do OWASP).
    Caso a biblioteca não esteja disponível, recorre ao PBKDF2-HMAC-SHA256 (100.000 iterações).
    """
    if HAS_ARGON2 and ph is not None:
        hash_argon2 = ph.hash(senha)
        return hash_argon2, "argon2id"

    # Fallback PBKDF2 com salt de 16 bytes
    salt = secrets.token_hex(16)
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    )
    return hash_bytes.hex(), salt


def verificar_hash_senha_seguro(
    senha: str, stored_hash: str, stored_salt: str
) -> Tuple[bool, bool]:
    """
    Verifica se a senha fornecida corresponde ao hash armazenado.
    Suporta Argon2id e PBKDF2 com migração automática transparente.
    Retorna: (is_valid, needs_rehash)
    """
    # 1. Caso hash seja Argon2id
    if stored_hash.startswith("$argon2id$") and HAS_ARGON2 and ph is not None:
        try:
            ph.verify(stored_hash, senha)
            needs_rehash = ph.check_needs_rehash(stored_hash)
            return True, needs_rehash
        except VerifyMismatchError:
            return False, False
        except Exception:
            return False, False

    # 2. Caso legado PBKDF2-HMAC-SHA256
    novo_hash_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        stored_salt.encode("utf-8"),
        100_000,
    )
    valido = secrets.compare_digest(novo_hash_bytes.hex(), stored_hash)
    # Se autenticou com sucesso com PBKDF2, sugere re-hash imediato para Argon2id
    needs_rehash = valido and HAS_ARGON2
    return valido, needs_rehash


# ==========================================
# PROTEÇÃO CONTRA FORÇA BRUTA (RATE LIMITING)
# ==========================================
class RateLimiterLogin:
    """Controlador em memória para limitação de tentativas de login por IP e Identificador."""

    def __init__(self):
        self._tentativas_ip: Dict[str, List[float]] = {}
        self._bloqueios_ip: Dict[str, float] = {}
        self._tentativas_usuario: Dict[str, List[float]] = {}
        self._bloqueios_usuario: Dict[str, float] = {}

    def _limpar_antigos(self, timestamps: List[float], janela_segundos: float) -> List[float]:
        agora = time.time()
        return [t for t in timestamps if agora - t < janela_segundos]

    def verificar_limite(self, ip: str, identificador: str) -> Tuple[bool, int]:
        """
        Verifica se o IP ou o usuário estão sob bloqueio temporário.
        Retorna: (bloqueado, segundos_restantes)
        """
        agora = time.time()

        # Verifica bloqueio de IP
        bloq_ip = self._bloqueios_ip.get(ip, 0)
        if bloq_ip > agora:
            return True, int(bloq_ip - agora)

        # Verifica bloqueio de Identificador
        id_limpo = identificador.strip().lower()
        bloq_user = self._bloqueios_usuario.get(id_limpo, 0)
        if bloq_user > agora:
            return True, int(bloq_user - agora)

        return False, 0

    def registrar_tentativa(self, ip: str, identificador: str, sucesso: bool) -> None:
        """Registra o resultado da tentativa de login e aplica bloqueio se atingir o limiar."""
        agora = time.time()
        id_limpo = identificador.strip().lower()
        janela = LOGIN_LOCKOUT_MINUTES * 60

        if sucesso:
            # Reseta histórico de falhas
            self._tentativas_ip.pop(ip, None)
            self._bloqueios_ip.pop(ip, None)
            self._tentativas_usuario.pop(id_limpo, None)
            self._bloqueios_usuario.pop(id_limpo, None)
            return

        # Registra falha de IP
        tentativas_ip = self._limpar_antigos(self._tentativas_ip.get(ip, []), janela)
        tentativas_ip.append(agora)
        self._tentativas_ip[ip] = tentativas_ip
        if len(tentativas_ip) >= MAX_LOGIN_ATTEMPTS:
            self._bloqueios_ip[ip] = agora + janela

        # Registra falha de Usuário
        tentativas_user = self._limpar_antigos(self._tentativas_usuario.get(id_limpo, []), janela)
        tentativas_user.append(agora)
        self._tentativas_usuario[id_limpo] = tentativas_user
        if len(tentativas_user) >= MAX_LOGIN_ATTEMPTS:
            self._bloqueios_usuario[id_limpo] = agora + janela


login_rate_limiter = RateLimiterLogin()


# ==========================================
# SANITIZAÇÃO E PROTEÇÃO DE ARQUIVOS / UPLOADS
# ==========================================
def sanitizar_nome_arquivo(nome_original: str) -> str:
    """
    Remove caminhos relativos (path traversal), caracteres de controle e restringe o nome.
    Garante que não contenha '../', '..\\' ou caracteres perigosos.
    """
    # Remove qualquer diretório precedente
    nome_base = os.path.basename(nome_original)
    # Remove caracteres que não sejam alfanuméricos, ponto, traço ou sublinhado
    nome_seguro = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", nome_base)
    # Previne nomes vazios ou ocultos
    if not nome_seguro or nome_seguro.startswith("."):
        nome_seguro = f"xml_{secrets.token_hex(8)}.xml"
    if len(nome_seguro) > 120:
        nome_seguro = nome_seguro[-120:]
    return nome_seguro


def validar_conteudo_xml(conteudo_bytes: bytes) -> None:
    """
    Validações de segurança em XML contra DoS, Entity Expansion e conteúdo malformado.
    """
    if len(conteudo_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo excede o tamanho máximo de {MAX_UPLOAD_SIZE_MB}MB.",
        )

    # Verifica se contém declaração XML ou tag raiz típica de NF-e
    snippet = conteudo_bytes[:1000].lower()
    if b"<?xml" not in snippet and b"<nfe" not in snippet and b"<infnfe" not in snippet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado não possui uma estrutura XML de NF-e válida.",
        )

    # Bloqueio de DTD e Entity Expansion (Bilion Laughs Attack / XXE)
    if b"<!doctype" in snippet or b"<!entity" in snippet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Declarações DTD/ENTITY externas não são permitidas por motivos de segurança.",
        )


def obter_ip_cliente(request: Request) -> str:
    """Extrai com segurança o endereço IP do cliente considerando proxies confiáveis."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"

