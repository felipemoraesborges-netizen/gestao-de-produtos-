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
3. **📊 Dashboard Analítico & Relatórios**:
   - Gráficos de rosca para composição dos custos e distribuição da saúde do estoque.
   - Gráfico de barras comparando os produtos mais rentáveis e produtos com maior capital imobilizado.
   - Relatórios executivos com projeção de faturamento e lucro potencial em estoque.
   - Relatório de Necessidade de Reposição e Compras com exportação em CSV e visualização para impressão/PDF.
4. **📦 Gestão de Estoque & Alertas de Reposição**:
   - Catálogo de estoque com controle de saldo atual e estoque mínimo de segurança.
   - Alertas dinâmicos e visuais para produtos com estoque baixo ou esgotados.
   - Registro de movimentações (Entrada, Saída e Ajuste de Balanço) com justificativa e histórico por item.
   - Botão **"Incorporar ao Estoque"** com 1 clique diretamente da tabela de precificação de NF-e.
5. **🛡️ Trilha de Auditoria & Compliance**:
   - Monitoramento contínuo de todas as ações de usuários (logins, cadastros, importações, movimentações de estoque, alterações cadastrais e exportações).
   - Registro de endereço IP, timestamp, usuário e detalhes da operação.
   - Filtros instantâneos por categoria de evento e exportação da trilha em formato CSV.
6. **📁 Histórico de NF-e**:
   - Consulta e filtragem instantânea de todas as notas fiscais importadas pela sua conta.
