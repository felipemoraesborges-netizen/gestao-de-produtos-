import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "banco_notas.db")

DEFAULT_IMPOSTOS = ["ICMS ST", "FCP ST", "IPI", "II"]


def inicializar_tabela_usuarios(db_path: str = DB_PATH) -> None:
    """Cria a tabela de usuários se não existir."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            empresa TEXT DEFAULT '',
            cargo TEXT DEFAULT '',
            markup_padrao REAL DEFAULT 60.0,
            custo_adicional_padrao REAL DEFAULT 0.0,
            impostos_padrao TEXT DEFAULT '["ICMS ST", "FCP ST", "IPI", "II"]',
            criado_em TEXT NOT NULL,
            ultimo_login TEXT
        )
    """)
    conn.commit()
    conn.close()


def gerar_hash_senha(senha: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Gera hash PBKDF2-HMAC-SHA256 seguro para a senha com salt aleatório."""
    if not salt:
        salt = secrets.token_hex(16)
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    )
    return hash_bytes.hex(), salt


def verificar_senha(senha: str, senha_hash: str, salt: str) -> bool:
    """Verifica se a senha fornecida corresponde ao hash armazenado."""
    novo_hash, _ = gerar_hash_senha(senha, salt)
    return secrets.compare_digest(novo_hash, senha_hash)


def cadastrar_usuario(
    usuario: str,
    nome: str,
    email: str,
    senha: str,
    empresa: str = "",
    cargo: str = "",
    markup_padrao: float = 60.0,
    custo_adicional_padrao: float = 0.0,
    impostos_padrao: Optional[List[str]] = None,
    db_path: str = DB_PATH,
) -> Tuple[bool, str]:
    """Cadastra um novo usuário no banco de dados."""
    inicializar_tabela_usuarios(db_path)
    usuario = usuario.strip().lower()
    nome = nome.strip()
    email = email.strip().lower()

    if not usuario or not nome or not email or not senha:
        return False, "Todos os campos obrigatórios devem ser preenchidos."

    if len(senha) < 6:
        return False, "A senha deve conter no mínimo 6 caracteres."

    if impostos_padrao is None:
        impostos_padrao = DEFAULT_IMPOSTOS

    senha_hash, salt = gerar_hash_senha(senha)
    criado_em = datetime.now().strftime("%d/%m/%Y %H:%M")
    impostos_json = json.dumps(impostos_padrao)

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO usuarios (
                usuario, nome, email, senha_hash, salt, empresa, cargo,
                markup_padrao, custo_adicional_padrao, impostos_padrao, criado_em, ultimo_login
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            usuario, nome, email, senha_hash, salt, empresa, cargo,
            float(markup_padrao), float(custo_adicional_padrao), impostos_json, criado_em, None
        ))
        conn.commit()
        conn.close()
        return True, "Usuário cadastrado com sucesso!"
    except sqlite3.IntegrityError as e:
        erro_str = str(e).lower()
        if "usuario" in erro_str:
            return False, "Nome de usuário já está em uso."
        elif "email" in erro_str:
            return False, "E-mail já cadastrado."
        return False, "Usuário ou e-mail já cadastrado no sistema."
    except Exception as e:
        return False, f"Erro ao cadastrar usuário: {e}"


def autenticar_usuario(
    usuario_ou_email: str,
    senha: str,
    db_path: str = DB_PATH,
) -> Tuple[bool, Any]:
    """Autentica o usuário pelo nome de usuário ou e-mail."""
    inicializar_tabela_usuarios(db_path)
    identificador = usuario_ou_email.strip().lower()

    if not identificador or not senha:
        return False, "Informe o usuário/e-mail e a senha."

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM usuarios WHERE lower(usuario) = ? OR lower(email) = ?
    """, (identificador, identificador))
    linha = cursor.fetchone()

    if not linha:
        conn.close()
        return False, "Usuário ou senha incorretos."

    usuario_dict = dict(linha)
    if not verificar_senha(senha, usuario_dict["senha_hash"], usuario_dict["salt"]):
        conn.close()
        return False, "Usuário ou senha incorretos."

    # Atualiza data do último login
    ultimo_login = datetime.now().strftime("%d/%m/%Y %H:%M")
    cursor.execute("UPDATE usuarios SET ultimo_login = ? WHERE id = ?", (ultimo_login, usuario_dict["id"]))
    conn.commit()
    conn.close()

    # Prepara dicionário do usuário logado (removendo campos sensíveis de segurança)
    usuario_dict["ultimo_login"] = ultimo_login
    del usuario_dict["senha_hash"]
    del usuario_dict["salt"]

    # Decodifica JSON de impostos
    try:
        usuario_dict["impostos_padrao"] = json.loads(usuario_dict.get("impostos_padrao") or "[]")
    except Exception:
        usuario_dict["impostos_padrao"] = DEFAULT_IMPOSTOS

    return True, usuario_dict


def obter_usuario_por_id(usuario_id: int, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """Recupera os dados atualizados do usuário pelo ID."""
    inicializar_tabela_usuarios(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,))
    linha = cursor.fetchone()
    conn.close()

    if not linha:
        return None

    usuario_dict = dict(linha)
    if "senha_hash" in usuario_dict:
        del usuario_dict["senha_hash"]
    if "salt" in usuario_dict:
        del usuario_dict["salt"]

    try:
        usuario_dict["impostos_padrao"] = json.loads(usuario_dict.get("impostos_padrao") or "[]")
    except Exception:
        usuario_dict["impostos_padrao"] = DEFAULT_IMPOSTOS

    return usuario_dict


def atualizar_perfil(
    usuario_id: int,
    nome: str,
    email: str,
    empresa: str,
    cargo: str,
    markup_padrao: float,
    custo_adicional_padrao: float,
    impostos_padrao: List[str],
    db_path: str = DB_PATH,
) -> Tuple[bool, str]:
    """Atualiza as informações cadastrais e preferências de precificação do usuário."""
    inicializar_tabela_usuarios(db_path)
    nome = nome.strip()
    email = email.strip().lower()

    if not nome or not email:
        return False, "Nome e e-mail são obrigatórios."

    impostos_json = json.dumps(impostos_padrao)

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE usuarios SET
                nome = ?,
                email = ?,
                empresa = ?,
                cargo = ?,
                markup_padrao = ?,
                custo_adicional_padrao = ?,
                impostos_padrao = ?
            WHERE id = ?
        """, (
            nome, email, empresa.strip(), cargo.strip(),
            float(markup_padrao), float(custo_adicional_padrao),
            impostos_json, usuario_id
        ))
        conn.commit()
        conn.close()
        return True, "Perfil e preferências atualizados com sucesso!"
    except sqlite3.IntegrityError:
        return False, "O e-mail informado já está em uso por outro usuário."
    except Exception as e:
        return False, f"Erro ao atualizar perfil: {e}"


def alterar_senha(
    usuario_id: int,
    senha_atual: str,
    nova_senha: str,
    db_path: str = DB_PATH,
) -> Tuple[bool, str]:
    """Altera a senha do usuário após validar a senha atual."""
    inicializar_tabela_usuarios(db_path)
    if not senha_atual or not nova_senha:
        return False, "Preencha a senha atual e a nova senha."

    if len(nova_senha) < 6:
        return False, "A nova senha deve ter no mínimo 6 caracteres."

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT senha_hash, salt FROM usuarios WHERE id = ?", (usuario_id,))
    linha = cursor.fetchone()

    if not linha:
        conn.close()
        return False, "Usuário não encontrado."

    if not verificar_senha(senha_atual, linha["senha_hash"], linha["salt"]):
        conn.close()
        return False, "Senha atual incorreta."

    novo_hash, novo_salt = gerar_hash_senha(nova_senha)
    cursor.execute("""
        UPDATE usuarios SET senha_hash = ?, salt = ? WHERE id = ?
    """, (novo_hash, novo_salt, usuario_id))
    conn.commit()
    conn.close()

    return True, "Senha alterada com sucesso!"
