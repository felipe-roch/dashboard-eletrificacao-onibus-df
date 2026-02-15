# 🚀 TUTORIAL COMPLETO - DEPLOY DO DASHBOARD NO STREAMLIT CLOUD

## 📋 PRÉ-REQUISITOS

Você vai precisar de:
1. ✅ Conta no GitHub (gratuita)
2. ✅ Conta no Streamlit Cloud (gratuita)
3. ✅ Arquivos do projeto prontos

---

## 📁 PASSO 1: ORGANIZE OS ARQUIVOS

Crie a seguinte estrutura de pastas no seu projeto:

```
Trabalho_de_Logistica/
├── dashboard_data/          ← Dados gerados pelo NB6
│   ├── dados_dashboard_master.json
│   ├── dados_kpis.json
│   ├── config_dashboard.json
│   └── dados_paradas.parquet
│
├── app.py                   ← Dashboard principal
├── requirements.txt         ← Dependências
└── README.md               ← Descrição (opcional)
```

**IMPORTANTE:** Todos os arquivos em `dashboard_data/` são necessários!

---

## 🐙 PASSO 2: CRIAR REPOSITÓRIO NO GITHUB

### 2.1. Criar conta GitHub (se não tiver)
1. Acesse: https://github.com
2. Clique em "Sign up"
3. Siga os passos (use seu email institucional se quiser)

### 2.2. Criar repositório
1. Faça login no GitHub
2. Clique no **"+"** (canto superior direito) → **"New repository"**
3. Configure:
   - **Repository name:** `dashboard-eletrificacao-onibus-df`
   - **Description:** "Dashboard interativo - Análise de viabilidade da eletrificação da frota de ônibus do DF"
   - **Public** (marque esta opção)
   - **Initialize this repository with:** Marque "Add a README file"
4. Clique em **"Create repository"**

### 2.3. Upload dos arquivos

**OPÇÃO A: Via Interface Web (Mais Fácil)**

1. No repositório criado, clique em **"Add file"** → **"Upload files"**
2. Arraste TODOS os arquivos:
   - `app.py`
   - `requirements.txt`
   - Pasta `dashboard_data/` (com todos os arquivos dentro)
3. Na caixa "Commit changes", escreva: "Upload inicial do dashboard"
4. Clique em **"Commit changes"**

**OPÇÃO B: Via Git (Avançado)**

```bash
# 1. Instale o Git: https://git-scm.com/downloads

# 2. No terminal/CMD, navegue até a pasta do projeto:
cd C:\Users\Felipe\Documents\Trabalho_de_Logistica

# 3. Inicialize o repositório:
git init
git add app.py requirements.txt dashboard_data/
git commit -m "Upload inicial do dashboard"

# 4. Conecte ao GitHub (substitua SEU_USUARIO):
git remote add origin https://github.com/SEU_USUARIO/dashboard-eletrificacao-onibus-df.git
git branch -M main
git push -u origin main
```

---

## ☁️ PASSO 3: DEPLOY NO STREAMLIT CLOUD

### 3.1. Criar conta Streamlit Cloud
1. Acesse: https://streamlit.io/cloud
2. Clique em **"Sign up"**
3. **IMPORTANTE:** Faça login com a **mesma conta do GitHub**
4. Autorize a conexão entre Streamlit e GitHub

### 3.2. Deploy do App

1. No Streamlit Cloud, clique em **"New app"**

2. Preencha os campos:
   - **Repository:** Selecione `SEU_USUARIO/dashboard-eletrificacao-onibus-df`
   - **Branch:** `main`
   - **Main file path:** `app.py`

3. **CONFIGURAÇÕES AVANÇADAS** (clique em "Advanced settings"):
   
   **Python version:** 3.11
   
   **Secrets (opcional):** Deixe em branco
   
4. Clique em **"Deploy!"**

5. **AGUARDE** ~3-5 minutos (primeira vez demora mais)

### 3.3. Acompanhe o Deploy

Você verá um log em tempo real. Espere até aparecer:

```
✅ Your app is live at: https://seu-app.streamlit.app
```

---

## 🔗 PASSO 4: COMPARTILHE COM O PROFESSOR

### 4.1. Copie o link

O link será algo como:
```
https://dashboard-eletrificacao-onibus-df-XXXXX.streamlit.app
```

### 4.2. Envie para o professor

**Email modelo:**

```
Assunto: Dashboard Interativo - TCC Eletrificação Ônibus DF

Prezado Professor [Nome],

Segue o link do dashboard interativo desenvolvido como parte do TCC:

🔗 Link: https://seu-dashboard.streamlit.app

O dashboard permite:
✅ Visualização interativa de rotas, garagens e terminais
✅ Análise de viabilidade econômica com diferentes cenários
✅ Simulador para testar variações de parâmetros
✅ KPIs operacionais e financeiros

O sistema está online 24/7 e pode ser acessado de qualquer dispositivo.

Atenciosamente,
[Seu Nome]
```

---

## 🛠️ PASSO 5: ATUALIZAÇÕES (SE NECESSÁRIO)

Se precisar atualizar o dashboard:

### Via GitHub Web:
1. Vá no repositório GitHub
2. Clique no arquivo que quer editar (ex: `app.py`)
3. Clique no ícone de lápis (editar)
4. Faça as mudanças
5. Clique em "Commit changes"
6. **O Streamlit atualiza AUTOMATICAMENTE em ~1 minuto!**

### Via Git:
```bash
# Faça suas mudanças nos arquivos locais, depois:
git add .
git commit -m "Descrição da mudança"
git push
```

---

## ❗ SOLUÇÃO DE PROBLEMAS

### Problema: "ModuleNotFoundError"
**Solução:** Verifique se o `requirements.txt` está correto e no repositório

### Problema: "FileNotFoundError: dashboard_data/..."
**Solução:** 
1. Certifique-se que a pasta `dashboard_data/` foi enviada ao GitHub
2. Verifique se o caminho em `app.py` está correto:
   ```python
   DATA_DIR = Path("dashboard_data")  # Sem barra no início!
   ```

### Problema: Dashboard muito lento
**Solução:** 
1. Use `@st.cache_data` nas funções de carregamento
2. Reduza o número de paradas no mapa (já implementado no código)

### Problema: Conta Streamlit atingiu limite
**Solução:** Streamlit Cloud tem limite de 1 app gratuito. Apague apps antigos se necessário.

---

## 📊 RECURSOS DO DASHBOARD

Seu professor poderá:

✅ **Filtrar** dados por operadora, tipo de linha, período
✅ **Visualizar** rotas no mapa interativo com heatmap
✅ **Analisar** viabilidade econômica (VPL, TIR, Payback)
✅ **Simular** diferentes cenários tarifários
✅ **Explorar** KPIs operacionais e financeiros
✅ **Comparar** com outras capitais brasileiras

---

## 🎯 DICAS EXTRAS

1. **Teste local primeiro:**
   ```bash
   cd C:\Users\Felipe\Documents\Trabalho_de_Logistica
   streamlit run app.py
   ```
   Abre em: http://localhost:8501

2. **Mantenha o repositório organizado:**
   - Use nomes de commit descritivos
   - Não suba arquivos desnecessários (.xlsx grandes, etc)

3. **Monitore o uso:**
   - Streamlit Cloud mostra estatísticas de acesso
   - Veja quantas pessoas acessaram

4. **Privacidade:**
   - O app é público por padrão
   - Se quiser privado, precisa do plano pago

---

## 🆘 PRECISA DE AJUDA?

### Documentação Oficial:
- Streamlit: https://docs.streamlit.io
- Streamlit Cloud: https://docs.streamlit.io/streamlit-community-cloud

### Comunidade:
- Forum: https://discuss.streamlit.io
- Discord: https://discord.gg/streamlit

---

## ✅ CHECKLIST FINAL

Antes de enviar para o professor:

- [ ] Dashboard abre sem erros
- [ ] Todos os filtros funcionam
- [ ] Mapa carrega corretamente
- [ ] Gráficos aparecem
- [ ] KPIs estão corretos
- [ ] Link funciona em navegador anônimo (teste em aba anônima!)
- [ ] Testei em celular (responsivo?)

---

**BOA SORTE! 🚀**

Se tudo deu certo, seu professor vai ficar IMPRESSIONADO com o dashboard interativo!
