diff --git a/app.py b/app.py
index 6aa08cc818087825bcbbe745bbcbf3cd182f944e..a0e71e88d51688942b3b99db305d306a9ce8e806 100644
--- a/app.py
+++ b/app.py
@@ -1,83 +1,271 @@
-import streamlit as st
-import pandas as pd
+from io import BytesIO
 from pathlib import Path
 
-st.set_page_config(page_title="Gestão de Usinas & UCs", page_icon="⚡", layout="wide")
+import pandas as pd
+import streamlit as st
+
+
+st.set_page_config(
+    page_title="Gestão de Usinas & UCs",
+    page_icon="⚡",
+    layout="wide",
+    initial_sidebar_state="expanded",
+)
+
 
 # =========================
-# 1. Encontrar automaticamente o arquivo Excel
+# 1. Utilidades para leitura e exportação da planilha
 # =========================
 
-def encontrar_excel():
-    """
-    Procura arquivos .xlsx na pasta do app.
-    Se houver mais de um, dá preferência a nomes que contenham 'Gest' ou 'Usina'.
+
+def encontrar_excel() -> Path | None:
+    """Procura um arquivo Excel na pasta do app.
+
+    A prioridade é para arquivos cujo nome contenha "gest", "usina" ou "uc".
     """
+
     arquivos = list(Path(".").glob("*.xlsx"))
     if not arquivos:
         return None
 
     preferidos = [
-        f for f in arquivos
+        f
+        for f in arquivos
         if "gest" in f.name.lower() or "usina" in f.name.lower() or "uc" in f.name.lower()
     ]
-    if preferidos:
-        return preferidos[0]
+    return preferidos[0] if preferidos else arquivos[0]
 
-    return arquivos[0]
 
+@st.cache_data(show_spinner=False)
+def carregar_planilhas(path: Path) -> dict[str, pd.DataFrame]:
+    """Lê todas as abas do Excel em um dicionário."""
 
-EXCEL_PATH = encontrar_excel()
+    return pd.read_excel(path, sheet_name=None, engine="openpyxl")
 
-if EXCEL_PATH is None:
-    st.error(
-        "Nenhum arquivo .xlsx foi encontrado na pasta do app.\n\n"
-        "Suba um arquivo Excel no repositório (por exemplo: Gestao_de_Usinas_e_UCs.xlsx)."
-    )
-    st.stop()
 
-st.sidebar.success(f"Arquivo Excel encontrado: {EXCEL_PATH.name}")
+def exportar_excel(planilhas: dict[str, pd.DataFrame], aba_atual: str, df_editado: pd.DataFrame) -> bytes:
+    """Recria o Excel combinando as abas originais com a aba editada."""
+
+    buffer = BytesIO()
+    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
+        for nome, dados in planilhas.items():
+            if nome == aba_atual:
+                df_editado.to_excel(writer, sheet_name=nome, index=False)
+            else:
+                dados.to_excel(writer, sheet_name=nome, index=False)
+    buffer.seek(0)
+    return buffer.getvalue()
+
 
 # =========================
-# 2. Carregar todas as abas da planilha
+# 2. Escolha de arquivo (upload ou arquivo local)
+# =========================
+
+
+st.sidebar.title("Gestão de Usinas & UCs")
+st.sidebar.caption(
+    "Portal dinâmico para acompanhar e editar a planilha de planejamento "
+    "estratégico das usinas e unidades consumidoras."
+)
+
+arquivo_padrao = encontrar_excel()
+upload = st.sidebar.file_uploader("Carregar uma planilha Excel", type=["xlsx"])
+
+if upload:
+    arquivo_origem = upload
+    st.sidebar.success(f"Excel enviado: {upload.name}")
+else:
+    if arquivo_padrao is None:
+        st.error(
+            "Nenhum arquivo .xlsx foi encontrado na pasta do app. "
+            "Envie um arquivo pelo uploader ao lado."
+        )
+        st.stop()
+    arquivo_origem = arquivo_padrao
+    st.sidebar.info(f"Usando arquivo padrão: {arquivo_padrao.name}")
+
+
+# =========================
+# 3. Carregar abas e preparar seleção
 # =========================
 
-@st.cache_data
-def carregar_planilhas(path: Path):
-    """
-    Lê todas as abas do Excel em um dict: {nome_aba: DataFrame}.
-    """
-    return pd.read_excel(path, sheet_name=None, engine="openpyxl")
 
 try:
-    sheets = carregar_planilhas(EXCEL_PATH)
-except Exception as e:
-    st.error(f"Erro ao ler o arquivo Excel: {e}")
+    planilhas = carregar_planilhas(arquivo_origem)
+except Exception as exc:  # pragma: no cover - Streamlit feedback
+    st.error(f"Erro ao ler o arquivo Excel: {exc}")
     st.stop()
 
-nomes_abas = list(sheets.keys())
+abas_disponiveis = list(planilhas.keys())
+aba_escolhida = st.sidebar.selectbox("Escolha a aba da planilha", abas_disponiveis)
+
 
 # =========================
-# 3. Interface básica
+# 4. Cabeçalho e visão geral
+# =========================
+
+
+st.title("Painel de Planejamento – Usinas & UCs")
+st.markdown(
+    "Visualização interativa e editável baseada na planilha compartilhada. "
+    "Use os filtros, cartões de métricas e gráficos para explorar rapidamente os dados."
+)
+
+df_original = planilhas[aba_escolhida]
+df = df_original.copy()
+colunas_numericas = list(df.select_dtypes(include="number").columns)
+colunas_texto = list(df.select_dtypes(exclude="number").columns)
+
+
+# =========================
+# 5. Barra de filtros
+# =========================
+
+
+with st.expander("🔍 Filtros avançados", expanded=True):
+    col_filtros = st.columns(2)
+    filtro_busca = col_filtros[0].text_input(
+        "Busca textual (aplica em todas as colunas de texto)",
+        help="Digite parte do valor que deseja encontrar.",
+    )
+
+    if colunas_texto:
+        col_texto = col_filtros[1].selectbox(
+            "Coluna categórica para filtrar",
+            options=["Nenhum"] + colunas_texto,
+            index=0,
+        )
+        valores_texto = []
+        if col_texto != "Nenhum":
+            valores_texto = st.multiselect(
+                f"Valores de {col_texto}", sorted(df[col_texto].dropna().unique()),
+                placeholder="Selecione um ou mais valores",
+            )
+    else:
+        col_texto = "Nenhum"
+        valores_texto = []
+
+    if colunas_numericas:
+        col_metricas = st.columns(len(colunas_numericas))
+        intervalos = {}
+        for idx, col in enumerate(colunas_numericas):
+            min_val, max_val = float(df[col].min()), float(df[col].max())
+            intervalo = col_metricas[idx].slider(
+                f"Intervalo para {col}",
+                min_val,
+                max_val,
+                (min_val, max_val),
+                step=(max_val - min_val) / 100 if max_val != min_val else 1.0,
+            )
+            intervalos[col] = intervalo
+    else:
+        intervalos = {}
+
+
+# =========================
+# 6. Aplicar filtros
+# =========================
+
+
+if filtro_busca:
+    mask_busca = pd.Series(False, index=df.index)
+    for col in colunas_texto:
+        mask_busca |= df[col].astype(str).str.contains(filtro_busca, case=False, na=False)
+    df = df[mask_busca]
+
+if col_texto != "Nenhum" and valores_texto:
+    df = df[df[col_texto].isin(valores_texto)]
+
+for col, intervalo in intervalos.items():
+    minimo, maximo = intervalo
+    df = df[df[col].between(minimo, maximo)]
+
+
+# =========================
+# 7. Cartões de métricas
 # =========================
 
-st.sidebar.title("Gestão de Usinas & UCs")
 
-aba_escolhida = st.sidebar.selectbox("Escolha a aba da planilha:", nomes_abas)
+with st.container():
+    st.subheader("Visão geral da aba")
+    col1, col2, col3, col4 = st.columns(4)
+    col1.metric("Linhas filtradas", len(df))
+    col2.metric("Colunas", len(df.columns))
+    col3.metric("Colunas numéricas", len(colunas_numericas))
+    col4.metric("Valores ausentes", int(df.isna().sum().sum()))
 
-st.title("Gestão de Usinas & UCs – Visualização da planilha")
-st.markdown(f"### Aba selecionada: **{aba_escolhida}**")
 
-df = sheets[aba_escolhida]
+# =========================
+# 8. Visualização e edição
+# =========================
+
+
+st.subheader("Dados da aba")
+habilitar_edicao = st.checkbox("Habilitar edição da tabela", value=False)
+
+if habilitar_edicao:
+    st.caption("Use o editor abaixo para ajustar valores. Depois faça o download da planilha atualizada.")
+    df_editado = st.data_editor(df, use_container_width=True, num_rows="dynamic")
+else:
+    df_editado = df
+    st.dataframe(df, use_container_width=True)
+
+
+# =========================
+# 9. Gráficos rápidos
+# =========================
+
+
+if colunas_numericas:
+    st.subheader("Visualizações")
+    col_viz1, col_viz2 = st.columns(2)
+
+    with col_viz1:
+        dimensao = st.selectbox(
+            "Dimensão para o gráfico de barras",
+            options=colunas_texto if colunas_texto else df.columns,
+        )
+        metrica = st.selectbox("Métrica numérica", options=colunas_numericas)
+        agregador = st.radio("Agregação", ["Soma", "Média"], horizontal=True)
+        if agregador == "Soma":
+            df_bar = df_editado.groupby(dimensao)[metrica].sum().reset_index()
+        else:
+            df_bar = df_editado.groupby(dimensao)[metrica].mean().reset_index()
+        st.bar_chart(df_bar, x=dimensao, y=metrica, use_container_width=True)
+
+    with col_viz2:
+        st.write("Série temporal / tendência")
+        colunas_datas = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
+        if not colunas_datas:
+            st.info("Nenhuma coluna de data foi detectada nesta aba.")
+        else:
+            coluna_data = st.selectbox("Coluna de data", options=colunas_datas)
+            metrica_linha = st.selectbox("Métrica", options=colunas_numericas, key="metrica_linha")
+            df_linha = (
+                df_editado.sort_values(coluna_data)
+                .groupby(coluna_data)[metrica_linha]
+                .sum()
+                .reset_index()
+            )
+            st.line_chart(df_linha, x=coluna_data, y=metrica_linha, use_container_width=True)
+
+
+# =========================
+# 10. Download da planilha atualizada
+# =========================
 
-st.dataframe(df, use_container_width=True)
 
 st.markdown("---")
-st.write("Colunas numéricas detectadas:")
-st.write(df.select_dtypes("number").head())
+st.subheader("Exportar")
+st.caption(
+    "Faça o download da planilha Excel já com os filtros aplicados e, se habilitado, com as edições realizadas nesta aba."
+)
 
-st.info(
-    "✅ App básico funcionando. Agora que a leitura da planilha está OK, "
-    "podemos evoluir para dashboards (cards, gráficos e lógicas específicas) "
-    "por usina / UC."
+excel_atualizado = exportar_excel(planilhas, aba_escolhida, df_editado)
+st.download_button(
+    "📥 Baixar Excel atualizado",
+    data=excel_atualizado,
+    file_name=f"{aba_escolhida}_atualizado.xlsx",
+    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
 )
+
