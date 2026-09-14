# 📦 Gestão de Produtos • Interface Moderna (React + Tailwind + FastAPI)

Sistema corporativo de alta performance para importação de XMLs de NF-e, rateio inteligente de custos, formação automática de preços de revenda e dashboards interativos com controle de acesso por login e perfis de usuário personalizados.

---

## ✨ Tecnologias de Ponta Utilizadas

- **Frontend**: React 18, Vite, Tailwind CSS, Lucide Icons, Chart.js, Canvas Confetti
- **Backend**: FastAPI (Python), Uvicorn ASGI, Pydantic, Pandas, DefusedXML
- **Banco de Dados**: SQLite com criptografia segura PBKDF2-HMAC-SHA256 e migração automática de esquemas

---

## 🚀 Como Iniciar a Aplicação

### Opção 1: Via Script Python (Recomendado)
Execute no terminal:
```bash
python run_app.py
```
*(O navegador abrirá automaticamente em `http://localhost:8000`)*

### Opção 2: Via Windows Batch
Basta dar um duplo clique no arquivo:
```
iniciar.bat
```

### Opção 3: Modo Desenvolvimento (Hot-Reload)
Se desejar editar o código em tempo real:
1. No terminal 1 (Backend):
   ```bash
   python -m uvicorn server:app --reload --port 8000
   ```
2. No terminal 2 (Frontend):
   ```bash
   cd frontend
   npm run dev
   ```
   Acesse: `http://localhost:5173`

---

## 🌟 Principais Recursos da Nova Interface

1. **🔐 Autenticação & Perfis**:
   - Tela de login e cadastro com glassmorphism e criptografia PBKDF2-HMAC-SHA256.
   - Perfil personalizado com persistência de preferências padrão (Markup %, Impostos e Custos Adicionais).
2. **📦 Precificação Reativa em Tempo Real**:
   - Área de **Drag & Drop** para upload simultâneo de múltiplos XMLs de NF-e.
   - Recálculo instantâneo ao ajustar sliders de markup, custos extras ou impostos sem recarregar a tela.
   - Tabela interativa com busca, ordenação por colunas, edição inline de unidades por embalagem e detalhes fiscais expandíveis por produto.
   - Exportação direta para CSV/Excel com formatação brasileira.
3. **📊 Dashboard Analítico**:
   - Gráfico de rosca para composição dos custos (Produtos vs Impostos vs Frete vs Despesas).
   - Gráfico de barras comparando os produtos mais lucrativos da nota.
4. **📁 Histórico de NF-e**:
   - Consulta e filtragem instantânea de todas as notas fiscais importadas pela sua conta.

### Configuracao de seguranca em producao

Defina estas variaveis de ambiente antes de publicar a aplicacao:

- `AUTH_SECRET_KEY`: chave aleatoria longa e persistente para assinar sessoes.
- `AUTH_COOKIE_SECURE=true`: exige HTTPS para enviar o cookie de sessao.
- `CORS_ORIGINS`: lista separada por virgulas com as origens oficiais do frontend.
- `ADMIN_USER`: nome de usuário que deve receber o nível `admin` ao iniciar a aplicação.

Nunca use uma chave compartilhada ou permita origens desconhecidas em ambiente publico.

### Níveis de acesso

- `admin`: gerencia usuários e níveis de acesso, além de usar todos os recursos.
- `operador`: importa XMLs, recalcula preços, consulta histórico e exporta relatórios.
- `consulta`: consulta histórico e perfil, sem permissão para alterar ou exportar dados.

Novos cadastros começam como `operador`. Para promover o primeiro administrador,
defina `ADMIN_USER` antes de iniciar o backend. O valor deve ser persistente no
ambiente de produção.
