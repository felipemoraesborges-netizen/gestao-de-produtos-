"""
Suíte de Testes Automatizados de Segurança (OWASP Top 10)
Valida todas as proteções implementadas no backend FastAPI do Gestão de Produtos:
- Autenticação e Emissão de Tokens JWT
- Validação e Rejeição de Tokens Inválidos / Expirados
- Bloqueio contra Acesso Não Autenticado
- Prevenção de BOLA / IDOR (Isolamento entre Usuários A e B)
- Proteção contra Força Bruta (Rate Limiting e Lockout)
- Validação Estrita de Upload XML (Extensão, Tamanho, Path Traversal, Conteúdo)
- Validação de Entrada Pydantic (Valores Inválidos / Negativos)
- Resiliência contra SQL Injection
- Integridade da Trilha de Auditoria
"""

import sys
import os
import time
import unittest
import jwt
from fastapi.testclient import TestClient

# Garante que o diretório raiz esteja no path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import security
from server import app
import auth

client = TestClient(app)

class SecurityTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Cria dois usuários para testes de isolamento de dados (BOLA)
        cls.user_a_creds = {
            "nome": "Usuario Alpha",
            "usuario": "user_alpha_sec",
            "email": "alpha_sec@test.com",
            "senha": "Password@12345Alpha",
            "empresa": "Empresa Alpha",
            "cargo": "Auditor"
        }
        cls.user_b_creds = {
            "nome": "Usuario Beta",
            "usuario": "user_beta_sec",
            "email": "beta_sec@test.com",
            "senha": "Password@12345Beta",
            "empresa": "Empresa Beta",
            "cargo": "Gerente"
        }

        # Cadastra usuários caso não existam
        auth.cadastrar_usuario(**cls.user_a_creds)
        auth.cadastrar_usuario(**cls.user_b_creds)

        # Realiza login para obter tokens
        res_a = client.post("/api/auth/login", json={
            "identificador": cls.user_a_creds["usuario"],
            "senha": cls.user_a_creds["senha"]
        })
        assert res_a.status_code == 200, f"Falha ao logar usuario A: {res_a.text}"
        data_a = res_a.json()
        cls.token_a = data_a["access_token"]
        cls.user_a_id = data_a["user"]["id"]

        res_b = client.post("/api/auth/login", json={
            "identificador": cls.user_b_creds["usuario"],
            "senha": cls.user_b_creds["senha"]
        })
        assert res_b.status_code == 200, f"Falha ao logar usuario B: {res_b.text}"
        data_b = res_b.json()
        cls.token_b = data_b["access_token"]
        cls.user_b_id = data_b["user"]["id"]

    # 1. Login Válido
    def test_01_login_valido(self):
        res = client.post("/api/auth/login", json={
            "identificador": self.user_a_creds["usuario"],
            "senha": self.user_a_creds["senha"]
        })
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn("access_token", body)
        self.assertIn("refresh_token", body)
        self.assertEqual(body["token_type"], "bearer")
        self.assertEqual(body["user"]["usuario"], self.user_a_creds["usuario"])

    # 2. Login Inválido (Mensagem Genérica contra Enumeração de Usuários)
    def test_02_login_invalido_mensagem_generica(self):
        res = client.post("/api/auth/login", json={
            "identificador": "usuario_inexistente_xyz_123",
            "senha": "WrongPassword123!"
        })
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["detail"], "Usuário ou senha inválidos.")

    # 3. Token Inválido / Adulterado
    def test_03_token_invalido(self):
        tampered_token = self.token_a[:-5] + "XXXXX"
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
        self.assertEqual(res.status_code, 401)
        self.assertIn("inválido", res.json()["detail"].lower())

    # 4. Token Expirado
    def test_04_token_expirado(self):
        # Forja token assinado com mesma chave mas expirado no passado
        expired_payload = {
            "sub": str(self.user_a_id),
            "usuario": self.user_a_creds["usuario"],
            "type": "access",
            "exp": time.time() - 3600
        }
        expired_token = jwt.encode(expired_payload, security.SECRET_KEY, algorithm=security.ALGORITHM)
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        self.assertEqual(res.status_code, 401)
        self.assertIn("expirad", res.json()["detail"].lower())

    # 5. Acesso sem Token a Endpoint Protegido
    def test_05_acesso_sem_token(self):
        res = client.get("/api/estoque")
        self.assertEqual(res.status_code, 401)
        self.assertIn("autenticação", res.json()["detail"].lower())

    # 6. BOLA / IDOR: Usuário A tentando acessar/modificar estoque do Usuário B
    def test_06_bola_protecao_estoque(self):
        import time as _time
        codigo_beta = f"SEC-BETA-{int(_time.time())}"
        # Usuário B cadastra um item no seu estoque
        res_create = client.post("/api/estoque/item",
            headers={"Authorization": f"Bearer {self.token_b}"},
            json={
                "codigo": codigo_beta,
                "produto": "Produto Exclusivo Beta",
                "unidade": "UN",
                "quantidade_atual": 100.0,
                "estoque_minimo": 10.0,
                "custo_unitario": 50.0,
                "preco_venda": 100.0,
                "categoria": "Testes"
            }
        )
        self.assertEqual(res_create.status_code, 200, f"Falha ao criar item: {res_create.text}")
        item_b_id = res_create.json()["id"]

        # Usuário A tenta excluir o item de B passando o ID do item
        res_del = client.delete(f"/api/estoque/{item_b_id}", headers={"Authorization": f"Bearer {self.token_a}"})
        self.assertEqual(res_del.status_code, 404)  # Retorna 404 pois item não pertence a A!

        # Usuário A tenta listar estoque: não deve ver o item de B
        res_list = client.get("/api/estoque", headers={"Authorization": f"Bearer {self.token_a}"})
        self.assertEqual(res_list.status_code, 200)
        items_a = [i["codigo"] for i in res_list.json()["produtos"]]
        self.assertNotIn(codigo_beta, items_a)

    # 7. BOLA / IDOR: Usuário A tentando alterar o perfil de B via payload
    def test_07_bola_alteracao_perfil(self):
        # Usuário A envia payload com usuario_id de B
        res = client.put("/api/auth/profile",
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={
                "usuario_id": self.user_b_id, # Tentativa de alterar o usuário B!
                "nome": "Nome Hackeado",
                "email": "hacked@alpha.com"
            }
        )
        self.assertEqual(res.status_code, 200)
        # O backend DEVE ter alterado apenas o usuário A, nunca o usuário B!
        profile_b = auth.obter_usuario_por_id(self.user_b_id)
        self.assertNotEqual(profile_b["nome"], "Nome Hackeado")
        self.assertEqual(profile_b["nome"], self.user_b_creds["nome"])

    # 8. Proteção contra Força Bruta (Rate Limiting e Lockout de Login)
    def test_08_brute_force_lockout(self):
        ip_alvo = "192.168.99.77"
        # Limpa estado anterior se houver
        security.login_rate_limiter._tentativas_ip.pop(ip_alvo, None)
        security.login_rate_limiter._bloqueios_ip.pop(ip_alvo, None)
        # Executa MAX_LOGIN_ATTEMPTS tentativas com senha incorreta
        for i in range(security.MAX_LOGIN_ATTEMPTS):
            res = client.post("/api/auth/login", 
                headers={"X-Forwarded-For": ip_alvo},
                json={"identificador": f"bruteforce_target_{i}", "senha": "WrongPassword123!"}
            )
            self.assertEqual(res.status_code, 401)

        # A tentativa seguinte deve receber HTTP 429 Too Many Requests
        res_lockout = client.post("/api/auth/login",
            headers={"X-Forwarded-For": ip_alvo},
            json={"identificador": "bruteforce_target_test", "senha": "WrongPassword123!"}
        )
        self.assertEqual(res_lockout.status_code, 429)
        self.assertIn("muitas tentativas", res_lockout.json()["detail"].lower())

    # 9. Upload de Arquivo Inválido (Extensão não XML)
    def test_09_upload_arquivo_invalido_extensao(self):
        files = {"files": ("malicious.exe", b"MZ\x90\x00\x03\x00\x00\x00", "application/octet-stream")}
        res = client.post("/api/nfe/upload",
            headers={"Authorization": f"Bearer {self.token_a}"},
            files=files
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("apenas arquivos .xml", res.json()["detail"].lower())

    # 10. Upload Acima do Tamanho Permitido (> MAX_UPLOAD_SIZE_MB)
    def test_10_upload_tamanho_excessivo(self):
        # Cria payload fake excedendo o limite permitido
        excessive_size = (security.MAX_UPLOAD_SIZE_MB * 1024 * 1024) + 1024
        big_content = b"<nfeProc>" + b"A" * 1024 * 1024 * 11 + b"</nfeProc>"
        files = {"files": ("huge.xml", big_content, "text/xml")}
        res = client.post("/api/nfe/upload",
            headers={"Authorization": f"Bearer {self.token_a}"},
            files=files
        )
        self.assertEqual(res.status_code, 413)
        self.assertIn("excede", res.json()["detail"].lower())

    # 11. Tentativa de Path Traversal no Nome do Arquivo
    def test_11_upload_path_traversal_sanitizado(self):
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
        <nfeProc versao="4.00" xmlns="http://www.portalfiscal.inf.br/nfe">
            <NFe><infNFe Id="NFe12345"><ide><nNF>9999</nNF></ide></infNFe></NFe>
        </nfeProc>"""
        traversal_name = "../../../etc/passwd.xml"
        sanitized = security.sanitizar_nome_arquivo(traversal_name)
        self.assertNotIn("/", sanitized)
        self.assertNotIn("..", sanitized)
        self.assertEqual(sanitized, "passwd.xml")

    # 12. Validação Pydantic de Entradas (Markup Negativo / Valores Inválidos)
    def test_12_validacao_pydantic_valores_invalidos(self):
        res = client.post("/api/nfe/calculate",
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={
                "produtos": [],
                "markup": -50.0 # Markup negativo deve ser rejeitado
            }
        )
        self.assertEqual(res.status_code, 422)

    # 13. Resiliência contra SQL Injection em Parâmetros de Consulta
    def test_13_sql_injection_resiliencia(self):
        sqli_payload = "' OR 1=1 --"
        res = client.get(f"/api/estoque?busca={sqli_payload}",
            headers={"Authorization": f"Bearer {self.token_a}"}
        )
        # O sistema deve responder 200 com array vazio ou sem vazar dados de outros usuários
        self.assertEqual(res.status_code, 200)
        produtos = res.json()["produtos"]
        # Garante que dados de outros usuários não foram retornados pela injeção
        for p in produtos:
            self.assertNotEqual(p.get("codigo"), "SEC-BETA-001")

    # 14. Integridade da Trilha de Auditoria (Identidade Real do Token)
    def test_14_auditoria_identidade_protegida(self):
        # Tenta forjar usuario_id de B no log de auditoria
        res = client.post("/api/auditoria/log",
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={
                "usuario_id": self.user_b_id,
                "usuario_nome": "Falso Admin",
                "acao": "TEST_AUDIT",
                "detalhes": "Tentativa de forja de auditoria"
            }
        )
        self.assertEqual(res.status_code, 200)
        # Consulta logs do usuário A
        res_logs = client.get("/api/auditoria?acao=TEST_AUDIT",
            headers={"Authorization": f"Bearer {self.token_a}"}
        )
        self.assertEqual(res_logs.status_code, 200)
        logs = res_logs.json()["logs"]
        self.assertTrue(len(logs) > 0)
        # O log registrado deve conter o ID real de A, nunca o ID forjado de B!
        self.assertEqual(logs[0]["usuario_id"], self.user_a_id)

    # 15. Headers de Segurança HTTP
    def test_15_security_headers_presentes(self):
        res = client.get("/")
        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res.headers.get("X-Frame-Options"), "DENY")
        self.assertIn("Content-Security-Policy", res.headers)
        self.assertIn("Referrer-Policy", res.headers)

if __name__ == "__main__":
    unittest.main(verbosity=2)
