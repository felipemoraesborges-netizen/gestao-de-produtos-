import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import security

DB_PATH = security.DB_PATH
DEFAULT_IMPOSTOS = ["ICMS ST", "FCP ST", "IPI", "II"]

# Evita reabrir uma conexão extra + refazer CREATE TABLE/INDEX a cada chamada
# de cadastrar_usuario/autenticar_usuario/etc — isso só precisa rodar uma vez
# por processo/caminho de banco, e era uma das causas dos locks concorrentes.
_tabelas_prontas: set = set()


def _garantir_tabela_usuarios(db_path: str = DB_PATH) -> None:
    """Garante que a tabela de usuários existe, executando a inicialização só uma vez."""
    if db_path in _tabelas_prontas:
        return
    inicializar_tabela_usuarios(db_path)
    _tabelas_prontas.add(db_path)


def inicializar_tabela_usuarios(db_path: str = DB_PATH) -> None:
    """Cria a tabela de usuários com índices apropriados se não existir."""
    conn = security.get_db_connection(db_path)
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
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_usuario ON usuarios(lower(usuario))")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(lower(email))")
    conn.commit()
    conn.close()


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
    """Cadastra um novo usuário no banco de dados com validação rigorosa de senha."""
    _garantir_tabela_usuarios(db_path)
    usuario = usuario.strip().lower()
    nome = nome.strip()
    email = email.strip().lower()

    if not usuario or not nome or not email or not senha:
        return False, "Todos os campos obrigatórios devem ser preenchidos."

    # Valida política de senha OWASP
    valida, msg_senha = security.validar_politica_senha(senha)
    if not valida:
        return False, msg_senha

    if impostos_padrao is None:
        impostos_padrao = DEFAULT_IMPOSTOS

    # Gera hash usando Argon2id (ou PBKDF2 se indisponível)
    senha_hash, salt = security.gerar_hash_senha_seguro(senha)
    criado_em = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    impostos_json = json.dumps(impostos_padrao)

    try:
        conn = security.get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO usuarios (
                usuario, nome, email, senha_hash, salt, empresa, cargo,
                markup_padrao, custo_adicional_padrao, impostos_padrao, criado_em, ultimo_login
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            usuario, nome, email, senha_hash, salt, empresa.strip()[:100], cargo.strip()[:100],
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
        return False, "Ocorreu um erro ao cadastrar o usuário. Tente novamente."


def autenticar_usuario(
    usuario_ou_email: str,
    senha: str,
    db_path: str = DB_PATH,
) -> Tuple[bool, Any]:
    """
    Autentica o usuário pelo nome de usuário ou e-mail.
    Em caso de sucesso com hash antigo, atualiza automaticamente para Argon2id.
    Retorna mensagem genérica segura em caso de falha para prevenir enumeração de contas.
    """
    _garantir_tabela_usuarios(db_path)
    identificador = usuario_ou_email.strip().lower()

    MENSAGEM_ERRO_GENERICA = "Usuário ou senha inválidos."

    if not identificador or not senha:
        return False, MENSAGEM_ERRO_GENERICA

    conn = security.get_db_connection(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM usuarios WHERE lower(usuario) = ? OR lower(email) = ?
    """, (identificador, identificador))
    linha = cursor.fetchone()

    if not linha:
        conn.close()
        return False, MENSAGEM_ERRO_GENERICA

    usuario_dict = dict(linha)
    stored_hash = usuario_dict["senha_hash"]
    stored_salt = usuario_dict["salt"]

    valido, needs_rehash = security.verificar_hash_senha_seguro(senha, stored_hash, stored_salt)
    if not valido:
        conn.close()
        return False, MENSAGEM_ERRO_GENERICA

    # Migração progressiva e automática de hash para Argon2id
    if needs_rehash:
        try:
            novo_hash, novo_salt = security.gerar_hash_senha_seguro(senha)
            cursor.execute(
                "UPDATE usuarios SET senha_hash = ?, salt = ? WHERE id = ?",
                (novo_hash, novo_salt, usuario_dict["id"]),
            )
            conn.commit()
        except Exception as e:
            print(f"[Segurança] Falha no upgrade de hash: {e}")

    # Atualiza data do último login
    ultimo_login = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    cursor.execute("UPDATE usuarios SET ultimo_login = ? WHERE id = ?", (ultimo_login, usuario_dict["id"]))
    conn.commit()
    conn.close()

    # Prepara dicionário do usuário logado garantindo remoção de credenciais
    usuario_dict["ultimo_login"] = ultimo_login
    usuario_dict.pop("senha_hash", None)
    usuario_dict.pop("salt", None)

    try:
        usuario_dict["impostos_padrao"] = json.loads(usuario_dict.get("impostos_padrao") or "[]")
    except Exception:
        usuario_dict["impostos_padrao"] = DEFAULT_IMPOSTOS

    return True, usuario_dict


def obter_usuario_por_id(usuario_id: int, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """Recupera os dados cadastrais do usuário sem expor credenciais."""
    _garantir_tabela_usuarios(db_path)
    conn = security.get_db_connection(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,))
    linha = cursor.fetchone()
    conn.close()

    if not linha:
        return None

    usuario_dict = dict(linha)
    usuario_dict.pop("senha_hash", None)
    usuario_dict.pop("salt", None)

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
    _garantir_tabela_usuarios(db_path)
    nome = nome.strip()
    email = email.strip().lower()

    if not nome or not email:
        return False, "Nome e e-mail são obrigatórios."

    # Validação de limites
    if len(nome) > 100 or len(email) > 120 or len(empresa) > 100 or len(cargo) > 100:
        return False, "Tamanho dos campos excede o limite permitido."

    impostos_json = json.dumps(impostos_padrao)

    try:
        conn = security.get_db_connection(db_path)
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
        return False, "Erro ao atualizar perfil."


def alterar_senha(
    usuario_id: int,
    senha_atual: str,
    nova_senha: str,
    db_path: str = DB_PATH,
) -> Tuple[bool, str]:
    """Altera a senha do usuário após validar a senha atual e a política de complexidade."""
    _garantir_tabela_usuarios(db_path)
    if not senha_atual or not nova_senha:
        return False, "Preencha a senha atual e a nova senha."

    # Valida política de complexidade na nova senha
    valida, msg_senha = security.validar_politica_senha(nova_senha)
    if not valida:
        return False, msg_senha

    conn = security.get_db_connection(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT senha_hash, salt FROM usuarios WHERE id = ?", (usuario_id,))
    linha = cursor.fetchone()

    if not linha:
        conn.close()
        return False, "Usuário não encontrado."

    valido, _ = security.verificar_hash_senha_seguro(senha_atual, linha["senha_hash"], linha["salt"])
    if not valido:
        conn.close()
        return False, "Senha atual incorreta."

    novo_hash, novo_salt = security.gerar_hash_senha_seguro(nova_senha)
    cursor.execute("""
        UPDATE usuarios SET senha_hash = ?, salt = ? WHERE id = ?
    """, (novo_hash, novo_salt, usuario_id))
    conn.commit()
    conn.close()

    return True, "Senha alterada com sucesso!"
