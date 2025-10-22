import os
import streamlit as st
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import sqlite3
import pandas as pd
from io import BytesIO

# ============================
# Banco SQLite
# ============================
DB_NAME = "orcamentos.db" 

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    
    # 1. Cria ou verifica a tabela orcamentos (com a coluna preco_m2)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orcamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT,
            cliente_nome TEXT,
            cliente_cnpj TEXT,
            tipo_cliente TEXT,
            estado TEXT,
            frete TEXT,
            tipo_pedido TEXT,
            vendedor_nome TEXT,
            vendedor_tel TEXT,
            vendedor_email TEXT,
            observacao TEXT,
            preco_m2 REAL
        )
    """)
    
    # 2. Migração de Schema: Adiciona a coluna preco_m2 se ela não existir
    try:
        cur.execute("SELECT preco_m2 FROM orcamentos LIMIT 1")
    except sqlite3.OperationalError:
        cur.execute("ALTER TABLE orcamentos ADD COLUMN preco_m2 REAL")
        print("Migração de DB: Coluna 'preco_m2' adicionada à tabela 'orcamentos'.")


    # 3. CRIAÇÃO/MIGRAÇÃO DE TABELA: itens_confeccionados (AGORA COM preco_unitario)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS itens_confeccionados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            orcamento_id INTEGER,
            produto TEXT,
            comprimento REAL,
            largura REAL,
            quantidade INTEGER,
            cor TEXT,
            preco_unitario REAL, -- <<-- NOVO CAMPO DE PREÇO TRAVADO
            FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id)
        )
    """)
    # 4. Migração de Schema: Adiciona a coluna preco_unitario se ela não existir (para conf.)
    try:
        cur.execute("SELECT preco_unitario FROM itens_confeccionados LIMIT 1")
    except sqlite3.OperationalError:
        cur.execute("ALTER TABLE itens_confeccionados ADD COLUMN preco_unitario REAL")
        print("Migração de DB: Coluna 'preco_unitario' adicionada à tabela 'itens_confeccionados'.")
    

    # 5. Criação de tabela itens_bobinas (AGORA COM preco_unitario)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS itens_bobinas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            orcamento_id INTEGER,
            produto TEXT,
            comprimento REAL,
            largura REAL,
            quantidade INTEGER,
            cor TEXT,
            espessura REAL,
            preco_unitario REAL, -- <<-- NOVO CAMPO DE PREÇO TRAVADO
            FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id)
        )
    """)
    # 6. Migração de Schema: Adiciona a coluna preco_unitario se ela não existir (para bobinas)
    try:
        cur.execute("SELECT preco_unitario FROM itens_bobinas LIMIT 1")
    except sqlite3.OperationalError:
        cur.execute("ALTER TABLE itens_bobinas ADD COLUMN preco_unitario REAL")
        print("Migração de DB: Coluna 'preco_unitario' adicionada à tabela 'itens_bobinas'.")
        
    conn.commit()
    conn.close()

def salvar_orcamento(cliente, vendedor, itens_confeccionados, itens_bobinas, observacao, preco_m2):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO orcamentos (data_hora, cliente_nome, cliente_cnpj, tipo_cliente, estado, frete, tipo_pedido, vendedor_nome, vendedor_tel, vendedor_email, observacao, preco_m2)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now(pytz.timezone("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M"),
        cliente.get("nome",""),
        cliente.get("cnpj",""),
        cliente.get("tipo_cliente",""),
        cliente.get("estado",""),
        cliente.get("frete",""),
        cliente.get("tipo_pedido",""),
        vendedor.get("nome",""),
        vendedor.get("tel",""),
        vendedor.get("email",""),
        observacao,
        preco_m2 # Preço base da sessão (o último digitado)
    ))
    orcamento_id = cur.lastrowid

    # NOVO INSERT: Inclui preco_unitario (travado)
    for item in itens_confeccionados:
        cur.execute("""
            INSERT INTO itens_confeccionados (orcamento_id, produto, comprimento, largura, quantidade, cor, preco_unitario)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (orcamento_id, item['produto'], item['comprimento'], item['largura'], item['quantidade'], item.get('cor',''), item.get('preco_unitario')))

    # NOVO INSERT: Inclui preco_unitario (travado)
    for item in itens_bobinas:
        cur.execute("""
            INSERT INTO itens_bobinas (orcamento_id, produto, comprimento, largura, quantidade, cor, espessura, preco_unitario)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (orcamento_id, item['produto'], item['comprimento'], item['largura'], item['quantidade'], item.get('cor',''), item.get('espessura'), item.get('preco_unitario')))

    conn.commit()
    conn.close()
    return orcamento_id

def buscar_orcamentos():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, data_hora, cliente_nome, cliente_cnpj, vendedor_nome FROM orcamentos ORDER BY id DESC") 
    rows = cur.fetchall()
    conn.close()
    return rows

def carregar_orcamento_por_id(orcamento_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    orc_cols = ['id','data_hora','cliente_nome','cliente_cnpj','tipo_cliente','estado','frete','tipo_pedido','vendedor_nome','vendedor_tel','vendedor_email','observacao', 'preco_m2']
    cur.execute("SELECT * FROM orcamentos WHERE id=?", (orcamento_id,))
    orc = cur.fetchone()
    
    # NOVO SELECT: Inclui preco_unitario (para confeccionados)
    cur.execute("SELECT produto, comprimento, largura, quantidade, cor, preco_unitario FROM itens_confeccionados WHERE orcamento_id=?", (orcamento_id,))
    confecc = cur.fetchall()
    
    # NOVO SELECT: Inclui preco_unitario (para bobinas)
    cur.execute("SELECT produto, comprimento, largura, quantidade, cor, espessura, preco_unitario FROM itens_bobinas WHERE orcamento_id=?", (orcamento_id,))
    bob = cur.fetchall()
    conn.close()
    return orc, confecc, bob

# ============================
# Formatação R$
# ============================
def _format_brl(v):
    try:
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return f"R$ {v}"

# ============================
# Cálculos (AGORA USANDO O PREÇO TRAVADO DO ITEM)
# ============================
st_por_estado = {
    # Alíquotas fictícias para exemplo
    "SP": 0.0,
    "MG": 12.0,
    "RJ": 18.0,
    "RS": 15.0,
    "PR": 17.0
} 

# MUDANÇA: Função calcular_valores_confeccionados usa o preço travado de cada item
def calcular_valores_confeccionados(itens, preco_m2_base, tipo_cliente="", estado="", tipo_pedido="Direta"):
    if not itens:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0

    IPI_CONFECCIONADO_DEFAULT = 0.0325
    IPI_ZERO_PRODS = ["Acrylic", "Agora"]
    IPI_ZERO_PREFIXES = ["Tela de Sombreamento"]

    m2_total = 0.0
    valor_bruto_acumulado = 0.0
    valor_ipi_acumulado = 0.0

    # 1. Calcula Bruto e IPI item por item usando o preço travado
    for item in itens:
        area_item = item['comprimento'] * item['largura'] * item['quantidade']
        # MUDANÇA CRÍTICA: Usa o preco_unitario (travado) do item se existir, senão usa o preço base.
        preco_item = item.get('preco_unitario') if item.get('preco_unitario') is not None else preco_m2_base 
        
        m2_total += area_item
        valor_item_bruto = area_item * preco_item
        valor_bruto_acumulado += valor_item_bruto

        if tipo_pedido != "Industrialização":
            produto = item.get('produto', '')
            ipi_rate = IPI_CONFECCIONADO_DEFAULT

            if produto in IPI_ZERO_PRODS or any(produto.startswith(prefix) for prefix in IPI_ZERO_PREFIXES):
                ipi_rate = 0.0
            
            valor_ipi_acumulado += valor_item_bruto * ipi_rate

    valor_bruto = valor_bruto_acumulado
    
    # 2. Finaliza cálculo
    if tipo_pedido == "Industrialização":
        valor_ipi = 0
        valor_st = 0
        aliquota_st = 0
        valor_final = valor_bruto
    else:
        valor_ipi = valor_ipi_acumulado
        valor_final = valor_bruto + valor_ipi
        
        valor_st = 0
        aliquota_st = 0
        if any(item.get('produto') == "Encerado" for item in itens) and tipo_cliente == "Revenda":
            aliquota_st = st_por_estado.get(estado, 0)
            valor_st = valor_final * aliquota_st / 100
            valor_final += valor_st

    return m2_total, valor_bruto, valor_ipi, valor_final, valor_st, aliquota_st

# MUDANÇA: A função Bobinas também garante usar o preço travado do item
def calcular_valores_bobinas(itens, preco_m2_base, tipo_pedido="Direta"):
    IPI_RATE_DEFAULT = 0.0975 # 9.75%
    
    if not itens:
        return 0.0, 0.0, 0.0, 0.0, IPI_RATE_DEFAULT

    m_total = sum(item['comprimento'] * item['quantidade'] for item in itens)
    
    # MUDANÇA CRÍTICA: Usa o preco_unitario (travado) do item se existir, senão usa o preço base.
    def preco_item_of(item):
        pu = item.get('preco_unitario') 
        return pu if (pu is not None) else preco_m2_base 

    valor_bruto = sum((item['comprimento'] * item['quantidade']) * preco_item_of(item) for item in itens)

    if tipo_pedido == "Industrialização":
        return m_total, valor_bruto, 0.0, valor_bruto, 0.0 # Retorna 0.0 como taxa de IPI
    else:
        IPI_RATE_CAPOTA = 0.0325 # 3.25%
        
        has_capota_maritima = any(item.get('produto') == "Capota Marítima" for item in itens)
        
        ipi_rate_to_use = IPI_RATE_CAPOTA if has_capota_maritima else IPI_RATE_DEFAULT
        
        valor_ipi = valor_bruto * ipi_rate_to_use
        valor_final = valor_bruto + valor_ipi

        return m_total, valor_bruto, valor_ipi, valor_final, ipi_rate_to_use

# ============================
# Função para gerar PDF 
# ============================
def gerar_pdf(orcamento_id, cliente, vendedor, itens_confeccionados, itens_bobinas, resumo_conf, resumo_bob, observacao, preco_m2, tipo_cliente="", estado=""):
    
    class PDF(FPDF):
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')

    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    largura_util = pdf.w - 2 * pdf.l_margin

    # Cabeçalho principal
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"ORÇAMENTO LOC ID: {orcamento_id}", 0, 1, "C")
    pdf.ln(5)
    
    # Dados do Cliente
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "Dados do Cliente", ln=True)
    pdf.set_font("Arial", size=9)
    pdf.cell(largura_util/2, 6, f"Cliente: {cliente.get('nome','')} - CNPJ: {cliente.get('cnpj','')}", 0, 0)
    pdf.cell(largura_util/2, 6, f"Vendedor: {vendedor.get('nome','')}", 0, 1)
    pdf.cell(largura_util, 6, f"Observação: {observacao}", 0, 1)
    pdf.ln(2)

    # Itens Confeccionados
    if itens_confeccionados:
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "Itens Confeccionados", ln=True)
        pdf.set_font("Arial", size=8)
        for item in itens_confeccionados:
            area_item = item['comprimento'] * item['largura'] * item['quantidade']
            # NOVO: Usa o preço travado do item
            preco_item_travado = item.get('preco_unitario') if item.get('preco_unitario') is not None else preco_m2 
            valor_item = area_item * preco_item_travado
            
            txt = (
                f"{item['quantidade']}x {item['produto']} - {item['comprimento']}m x {item['largura']}m "
                f"| Cor: {item.get('cor','')} | Preco Unitario: {_format_brl(preco_item_travado)} | Valor Bruto: {_format_brl(valor_item)}"
            )
            pdf.multi_cell(largura_util, 6, txt)
            pdf.ln(1)

    # Resumo Confeccionados
    if resumo_conf:
        m2_total, valor_bruto, valor_ipi, valor_final, valor_st, aliquota_st = resumo_conf
        pdf.ln(3)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 10, "Resumo - Confeccionados", ln=True)
        pdf.set_font("Arial", "", 10)
        # Exibe o preco_m2 que foi o último digitado na sessão.
        pdf.cell(0, 6, f"M2 Total: {m2_total:,.2f} m2", ln=True)
        pdf.cell(0, 6, f"Preco base da sessao: {_format_brl(preco_m2)}", ln=True) 
        pdf.cell(0, 6, f"Valor Bruto: {_format_brl(valor_bruto)}", ln=True)
        pdf.cell(0, 6, f"Valor IPI ({IPI_CONFECCIONADO_DEFAULT*100:.2f}%): {_format_brl(valor_ipi)}", ln=True)
        if valor_st > 0:
            pdf.cell(0, 6, f"Valor ST ({aliquota_st:.2f}%): {_format_brl(valor_st)}", ln=True)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, f"Valor Final: {_format_brl(valor_final)}", ln=True)
        pdf.set_font("Arial", "", 10)

    # Itens Bobinas
    if itens_bobinas:
        pdf.ln(3)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "Itens Bobinas", ln=True)
        pdf.set_font("Arial", size=8)
        for item in itens_bobinas:
            metros_item = item['comprimento'] * item['quantidade']
            # Usa o preço travado do item
            preco_item = item.get('preco_unitario') if item.get('preco_unitario') is not None else preco_m2
            valor_item = metros_item * preco_item
            
            esp = f" | Esp: {item['espessura']:.2f}mm" if 'espessura' in item and item.get('espessura') is not None else ""
            
            txt = (
                f"{item['quantidade']}x {item['produto']} - {item['comprimento']}m | Largura: {item['largura']}m {esp} "
                f"| Cor: {item.get('cor','')} | Preco Unitario: {_format_brl(preco_item)} | Valor Bruto: {_format_brl(valor_item)}"
            )
            pdf.multi_cell(largura_util, 6, txt)
            pdf.ln(1)
            
        if resumo_bob:
            m_total, valor_bruto_bob, valor_ipi_bob, valor_final_bob, ipi_rate_bob = resumo_bob
            pdf.ln(3)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, "Resumo - Bobinas", ln=True)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 6, f"Metros Total: {m_total:,.2f} m", ln=True)
            pdf.cell(0, 6, f"Valor Bruto: {_format_brl(valor_bruto_bob)}", ln=True)
            pdf.cell(0, 6, f"Valor IPI ({ipi_rate_bob*100:.2f}%): {_format_brl(valor_ipi_bob)}", ln=True)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 6, f"Valor Final: {_format_brl(valor_final_bob)}", ln=True)
            pdf.set_font("Arial", "", 10)

    # Nota de rodapé
    pdf.set_y(-25)
    pdf.set_font("Arial", "I", 9)
    pdf.multi_cell(0, 5, f"Orçamento gerado em: {datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M')}", 0, "C")

    # Retorna bytes binários, o Streamlit saberá lidar.
    return pdf.output(dest='S') 


# ============================
# Constantes
# ============================
PRODUTOS_FABRICADOS = [
    "Lona para Caminhão", "Capota Marítima", "Cortina para Caminhão", "Encerado"
]
PRODUTOS_BOBINA = [
    "Lona Bobina", "PVC Bobina", "Filme Stretch"
]
PRODUTOS_TIPO_PEDIDO = ["Direta", "Industrialização"]


# ============================
# NOVO: Função de Callback para resetar o preço
# ============================
def reset_price_on_product_change():
    """Zera o campo de preço ao mudar o produto para evitar a reutilização acidental do preço anterior."""
    st.session_state['preco_m2'] = 0.0


def reset_session():
    # Inicialização de Session State
    if 'itens_confeccionados' not in st.session_state:
        st.session_state['itens_confeccionados'] = []
    if 'bobinas_adicionadas' not in st.session_state:
        st.session_state['bobinas_adicionadas'] = []
    if 'preco_m2' not in st.session_state:
        st.session_state['preco_m2'] = 0.0
    if 'obs' not in st.session_state:
        st.session_state['obs'] = ""
    if 'cliente_nome' not in st.session_state:
        st.session_state['cliente_nome'] = ""
    if 'cliente_cnpj' not in st.session_state:
        st.session_state['cliente_cnpj'] = ""
    if 'vendedor_nome' not in st.session_state:
        st.session_state['vendedor_nome'] = "Vendedor Padrão"
    if 'vendedor_tel' not in st.session_state:
        st.session_state['vendedor_tel'] = ""
    if 'vendedor_email' not in st.session_state:
        st.session_state['vendedor_email'] = ""
    if 'estado' not in st.session_state:
        st.session_state['estado'] = "SP"
    if 'tipo_cliente' not in st.session_state:
        st.session_state['tipo_cliente'] = "Consumidor Final"
    if 'frete' not in st.session_state:
        st.session_state['frete'] = "CIF"
    if 'tipo_pedido' not in st.session_state:
        st.session_state['tipo_pedido'] = "Direta"
    if 'menu_index' not in st.session_state:
        st.session_state['menu_index'] = 0

# ============================
# Interface - Novo Orçamento
# ============================
init_db()
reset_session()

st.set_page_config(layout="wide", page_title="Calculadora de Orçamentos")

menu = st.sidebar.radio("Navegação", ["Novo Orçamento", "Histórico de Orçamentos"], index=st.session_state['menu_index'])

st.title("Calculadora de Orçamentos Locomotiva")

if menu == "Novo Orçamento":
    st.session_state['menu_index'] = 0
    st.subheader("Dados do Cliente")
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_input("Nome do Cliente:", key="cliente_nome")
        st.text_input("CNPJ/CPF:", key="cliente_cnpj")
        st.selectbox("Tipo de Cliente:", ["Consumidor Final", "Revenda"], key="tipo_cliente")
    
    with col2:
        st.selectbox("Estado:", list(st_por_estado.keys()), key="estado")
        st.selectbox("Frete:", ["CIF", "FOB"], key="frete")
        st.selectbox("Tipo de Pedido:", PRODUTOS_TIPO_PEDIDO, key="tipo_pedido")
        
    st.markdown("---")
    
    st.subheader("Configuração de Preço e Produto")
    
    tipo_produto_options = ["Confeccionado", "Bobina"]
    tipo_produto = st.radio("Tipo do Produto:", tipo_produto_options, key="tipo_prod_sel", horizontal=True)
    
    # Lista de produtos com base na seleção
    produtos_lista = PRODUTOS_FABRICADOS if tipo_produto == "Confeccionado" else PRODUTOS_BOBINA
    
    col3, col4 = st.columns(2)
    with col3:
        # CORREÇÃO CRÍTICA: Adiciona o on_change para resetar o preço.
        produto = st.selectbox(
            "Nome do Produto:", 
            options=produtos_lista, 
            key="produto_sel",
            on_change=reset_price_on_product_change # <<-- FIX APLICADO AQUI
        )
    with col4:
        # Mantemos preco_m2 como a chave da sessão para o input
        preco_m2 = st.number_input("Preço por m² ou metro linear (R$):", min_value=0.0, value=st.session_state.get("preco_m2", 0.0), step=0.01, key="preco_m2")

    # Avisos de ICMS e ST
    st_aliquota = st_por_estado.get(st.session_state['estado'], 0)
    if st.session_state['tipo_cliente'] == "Revenda" and st_aliquota > 0:
        st.warning(f"⚠️ Atenção! Cliente Revenda em {st.session_state['estado']}. Pode haver incidência de ST conforme o produto (alíquota: {st_aliquota}%%).")

    if st.session_state['tipo_pedido'] == "Industrialização":
        st.info("ℹ️ Pedido de Industrialização: IPI e ST serão zerados no cálculo.")

    st.markdown("---")

    # Confeccionado
    if tipo_produto == "Confeccionado":
        st.subheader("Itens Confeccionados (m²)")
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        
        with col_c1:
            comprimento = st.text_input("Comprimento (m):", value="0.00", key="comp_conf")
        with col_c2:
            largura = st.text_input("Largura (m):", value="0.00", key="larg_conf")
        with col_c3:
            quantidade = st.text_input("Quantidade (un):", value="1", key="qtd_conf")
        with col_c4:
            cor_conf = st.text_input("Cor (Opcional):", key="cor_conf_input")


        if st.button("➕ Adicionar Medida", key="add_conf"):
            try:
                comp = float(comprimento.replace(",", "."))
                larg = float(largura.replace(",", "."))
                qtd = int(quantidade)
                
                if comp <= 0 or larg <= 0 or qtd <= 0:
                     st.error("Comprimento, Largura e Quantidade devem ser maiores que zero.")
                else:
                    # AÇÃO CRÍTICA: Trava o preço digitado no campo de input.
                    preco_travado = float(preco_m2) 
                    
                    st.session_state['itens_confeccionados'].append({
                        'produto': produto,
                        'comprimento': comp,
                        'largura': larg,
                        'quantidade': qtd,
                        'cor': cor_conf,
                        'preco_unitario': preco_travado # <<-- PREÇO TRAVADO (Individual por item)
                    })
                    st.success(f"Item {produto} adicionado com R$/m² travado em {_format_brl(preco_travado)}.")
                    st.session_state['comp_conf'] = "0.00"
                    st.session_state['larg_conf'] = "0.00"
                    st.session_state['qtd_conf'] = "1"
                    st.session_state['cor_conf_input'] = ""
                    st.rerun()

            except ValueError:
                st.error("Por favor, insira valores numéricos válidos.")

        if st.session_state['itens_confeccionados']:
            st.subheader("📋 Itens Adicionados")
            total_m2 = 0
            for idx, item in enumerate(st.session_state['itens_confeccionados'][:] ):
                col_i1, col_i2, col_i3, col_i4 = st.columns([3,2,2,1])
                with col_i1:
                    area_item = item['comprimento'] * item['largura'] * item['quantidade']
                    total_m2 += area_item
                    
                    # CÁLCULO DE EXIBIÇÃO: Usa o preço travado do item
                    preco_item_travado = item.get('preco_unitario') if item.get('preco_unitario') is not None else preco_m2
                    valor_item = area_item * preco_item_travado

                    st.markdown(f"**{item['produto']}**")
                    st.markdown(
                        f"🔹 {item['quantidade']}x {item['comprimento']:.2f}m x {item['largura']:.2f}m "
                        f"= {area_item:.2f} m² | R$/m²: {_format_brl(preco_item_travado)} → {_format_brl(valor_item)}"
                    )
                with col_i2:
                    # Edição de Cor
                    cor = st.text_input("Cor:", value=item.get('cor', ''), key=f"cor_conf_{idx}")
                    st.session_state['itens_confeccionados'][idx]['cor'] = cor
                
                with col_i4:
                    remover = st.button("❌", key=f"remover_conf_{idx}")
                    if remover:
                        st.session_state['itens_confeccionados'].pop(idx)
                        st.rerun()
            
            if st.button("🗑️ Limpar Lista Confeccionados", key="limpar_conf"):
                st.session_state['itens_confeccionados'] = []
                st.rerun()

            st.markdown("---")
            st.subheader("Resumo do Pedido")

            # CÁLCULO: Manda o preço base (para fallback de orçamentos antigos)
            m2_total, valor_bruto, valor_ipi, valor_final, valor_st, aliquota_st = calcular_valores_confeccionados(
                st.session_state['itens_confeccionados'], preco_m2, st.session_state['tipo_cliente'], st.session_state['estado'], st.session_state['tipo_pedido']
            )

            st.markdown(f"**Total m²:** `{m2_total:,.2f} m²`")
            st.markdown(f"**Valor Bruto:** `{_format_brl(valor_bruto)}`")
            if st.session_state['tipo_pedido'] != "Industrialização":
                 st.markdown(f"**Valor IPI:** `{_format_brl(valor_ipi)}`")
                 if valor_st > 0:
                     st.markdown(f"**Valor ST:** `{_format_brl(valor_st)}`") # Alíquota é exibida no PDF
            st.markdown(f"## **Valor Final:** `{_format_brl(valor_final)}`")


    # Bobina
    if tipo_produto == "Bobina":
        st.subheader("Itens Bobinas (metro linear)")
        col_b1, col_b2, col_b3, col_b4 = st.columns(4)
        
        with col_b1:
            comprimento_bobina = st.text_input("Comprimento (m):", value="0.00", key="comp_bob")
        with col_b2:
            largura_bobina = st.text_input("Largura (m):", value="0.00", key="larg_bob")
        with col_b3:
            quantidade_bobina = st.text_input("Quantidade (un):", value="1", key="qtd_bob")
        with col_b4:
             espessura_bobina = st.text_input("Espessura (mm - Opcional):", key="esp_bob")

        if st.button("➕ Adicionar Bobina", key="add_bob"):
            try:
                comp_bob = float(comprimento_bobina.replace(",", "."))
                larg_bob = float(largura_bobina.replace(",", "."))
                qtd_bob = int(quantidade_bobina)
                esp_bob = float(espessura_bobina.replace(",", ".")) if espessura_bobina else None
                
                if comp_bob <= 0 or larg_bob <= 0 or qtd_bob <= 0:
                     st.error("Comprimento, Largura e Quantidade devem ser maiores que zero.")
                else:
                    # AÇÃO CRÍTICA: Trava o preço digitado no campo de input.
                    preco_travado = float(preco_m2) 
                    
                    item_bobina = {
                        'produto': produto,
                        'comprimento': comp_bob,
                        'largura': larg_bob,
                        'quantidade': qtd_bob,
                        'cor': "", # Cor não é inputada aqui, mas é mantida
                        'preco_unitario': preco_travado # <<-- PREÇO TRAVADO (Individual por item)
                    }
                    if esp_bob is not None:
                        item_bobina['espessura'] = esp_bob
                    
                    st.session_state['bobinas_adicionadas'].append(item_bobina)
                    st.success(f"Bobina {produto} adicionada com R$/metro travado em {_format_brl(preco_travado)}.")
                    st.session_state['comp_bob'] = "0.00"
                    st.session_state['larg_bob'] = "0.00"
                    st.session_state['qtd_bob'] = "1"
                    st.session_state['esp_bob'] = ""
                    st.rerun()

            except ValueError:
                st.error("Por favor, insira valores numéricos válidos.")
        
        if st.session_state['bobinas_adicionadas']:
            st.subheader("📋 Bobinas Adicionadas")
            total_m = 0
            for idx, item in enumerate(st.session_state['bobinas_adicionadas'][:] ):
                col_i1, col_i2, col_i3, col_i4 = st.columns([3,2,2,1])
                with col_i1:
                    metros_item = item['comprimento'] * item['quantidade']
                    total_m += metros_item
                    
                    # CÁLCULO DE EXIBIÇÃO: Usa o preço travado do item
                    preco_item_travado = item.get('preco_unitario') if item.get('preco_unitario') is not None else preco_m2
                    valor_item = metros_item * preco_item_travado

                    detalhes = (
                        f"🔹 {item['quantidade']}x {item['comprimento']:.2f}m | Largura: {item['largura']:.2f}m "
                        f"= {metros_item:.2f} m | R$/m: {_format_brl(preco_item_travado)} → {_format_brl(valor_item)}"
                    )
                    if 'espessura' in item and item.get('espessura') is not None:
                        detalhes += f" | Esp: {item['espessura']:.2f}mm"
                    
                    st.markdown(f"**{item['produto']}**")
                    st.markdown(detalhes)
                
                with col_i2:
                    # Edição de Cor
                    cor = st.text_input("Cor:", value=item.get('cor', ''), key=f"cor_bob_{idx}")
                    st.session_state['bobinas_adicionadas'][idx]['cor'] = cor
                
                with col_i4:
                    remover = st.button("❌", key=f"remover_bob_{idx}")
                    if remover:
                        st.session_state['bobinas_adicionadas'].pop(idx)
                        st.rerun()

            if st.button("🗑️ Limpar Lista Bobinas", key="limpar_bob"):
                st.session_state['bobinas_adicionadas'] = []
                st.rerun()

            st.markdown("---")
            st.subheader("Resumo do Pedido")

            # CÁLCULO: Manda o preço base (para fallback de orçamentos antigos)
            m_total, valor_bruto_bob, valor_ipi_bob, valor_final_bob, ipi_rate_bob = calcular_valores_bobinas(
                st.session_state['bobinas_adicionadas'], preco_m2, st.session_state['tipo_pedido']
            )

            st.markdown(f"**Total m:** `{m_total:,.2f} m`")
            st.markdown(f"**Valor Bruto:** `{_format_brl(valor_bruto_bob)}`")
            if st.session_state['tipo_pedido'] != "Industrialização":
                st.markdown(f"**Valor IPI ({ipi_rate_bob*100:.2f}%):** `{_format_brl(valor_ipi_bob)}`")
            st.markdown(f"## **Valor Final:** `{_format_brl(valor_final_bob)}`")


    st.markdown("---")
    st.subheader("Detalhes Finais")
    
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.text_input("Nome Vendedor:", key="vendedor_nome")
        st.text_input("Telefone Vendedor:", key="vendedor_tel")
        st.text_input("Email Vendedor:", key="vendedor_email")
    with col_v2:
        st.text_area("Observações do Orçamento:", height=150, key="obs")

    st.markdown("---")
    
    # Botão gerar e salvar
    if st.button("📄 Gerar PDF e Salvar Orçamento", key="gerar_e_salvar"):
        if not st.session_state["itens_confeccionados"] and not st.session_state["bobinas_adicionadas"]:
             st.error("Adicione pelo menos um item ao orçamento para salvar.")
        else:
            cliente = {
                "nome": st.session_state.get("cliente_nome", ""),
                "cnpj": st.session_state.get("cliente_cnpj", ""),
                "tipo_cliente": st.session_state.get("tipo_cliente", ""),
                "estado": st.session_state.get("estado", ""),
                "frete": st.session_state.get("frete", ""),
                "tipo_pedido": st.session_state.get("tipo_pedido", ""),
            }
            vendedor = {
                "nome": st.session_state.get("vendedor_nome", ""),
                "tel": st.session_state.get("vendedor_tel", ""),
                "email": st.session_state.get("vendedor_email", ""),
            }

            # Salvar
            orcamento_id = salvar_orcamento(
                cliente,
                vendedor,
                st.session_state["itens_confeccionados"],
                st.session_state["bobinas_adicionadas"],
                st.session_state.get("obs",""),
                st.session_state.get("preco_m2",0.0) 
            )
            st.success(f"✅ Orçamento salvo com ID {orcamento_id}")

            # Resumos para PDF e Download
            resumo_conf = calcular_valores_confeccionados(
                st.session_state["itens_confeccionados"], 
                st.session_state.get("preco_m2",0.0), 
                st.session_state.get("tipo_cliente"," "), 
                st.session_state.get("estado",""), 
                st.session_state.get("tipo_pedido","Direta")
            ) if st.session_state["itens_confeccionados"] else None
            
            resumo_bob = calcular_valores_bobinas(
                st.session_state["bobinas_adicionadas"], 
                st.session_state.get("preco_m2",0.0), 
                st.session_state.get("tipo_pedido","Direta")
            ) if st.session_state["bobinas_adicionadas"] else None

            # Gerar PDF bytes (Passando orcamento_id)
            pdf_bytes = gerar_pdf(
                orcamento_id, 
                cliente,
                vendedor,
                st.session_state["itens_confeccionados"],
                st.session_state["bobinas_adicionadas"],
                resumo_conf,
                resumo_bob,
                st.session_state.get("obs",""),
                st.session_state.get("preco_m2",0.0), 
                tipo_cliente=st.session_state.get("tipo_cliente"," "),
                estado=st.session_state.get("estado","")
            )

            col_down1, col_down2 = st.columns(2)
            with col_down1:
                st.download_button(
                    "📄 Baixar PDF",
                    data=pdf_bytes,
                    file_name=f"orcamento_{orcamento_id}.pdf",
                    mime="application/pdf"
                )

# ============================
# Menu: Histórico de Orçamentos
# ============================
if menu == "Histórico de Orçamentos":
    st.session_state['menu_index'] = 1
    st.subheader("Histórico de Orçamentos Salvos")

    orcamentos = buscar_orcamentos()
    
    if not orcamentos:
        st.info("Nenhum orçamento encontrado no banco de dados.")
        st.stop()

    df_orcamentos = pd.DataFrame(orcamentos, columns=['ID', 'Data/Hora', 'Cliente', 'CNPJ/CPF', 'Vendedor'])
    
    # Filtros
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filtro_cliente = st.text_input("Filtrar por Nome do Cliente:")
    with col_f2:
        filtro_vendedor = st.selectbox("Filtrar por Vendedor:", ["Todos"] + sorted(df_orcamentos['Vendedor'].unique()))
    with col_f3:
        filtro_id = st.text_input("Filtrar por ID:")

    orcamentos_filtrados = orcamentos
    
    # Aplicar filtros
    if filtro_cliente:
        orcamentos_filtrados = [o for o in orcamentos_filtrados if filtro_cliente.lower() in o[2].lower()]
    
    if filtro_vendedor != "Todos":
        orcamentos_filtrados = [o for o in orcamentos_filtrados if o[4] == filtro_vendedor]
        
    if filtro_id:
        try:
            id_int = int(filtro_id)
            orcamentos_filtrados = [o for o in orcamentos_filtrados if o[0] == id_int]
        except ValueError:
            st.error("ID deve ser um número inteiro.")
            orcamentos_filtrados = []

    
    if not orcamentos_filtrados:
        st.warning("Nenhum orçamento corresponde aos filtros.")
        st.stop()
        
    for o in orcamentos_filtrados:
        orc_id, data_hora, cliente_nome, cliente_cnpj, vendedor_nome = o
        orc, confecc, bob = carregar_orcamento_por_id(orc_id)
        
        if not orc:
             st.error(f"Dados do orçamento {orc_id} incompletos.")
             continue

        # Mapeamento do orçamento principal
        orc_data = {
            'tipo_cliente': orc[4],
            'estado': orc[5],
            'frete': orc[6],
            'tipo_pedido': orc[7],
            'vendedor_tel': orc[9],
            'vendedor_email': orc[10],
            'observacao': orc[11],
        }
        # orc[12] é o preco_m2 base (o último digitado naquela sessão)
        preco_m2_base = orc[12] if orc[12] is not None else 0.0 

        with st.expander(f"📝 ID {orc_id} - {cliente_nome} ({data_hora})"):
            st.markdown(f"**Cliente:** {cliente_nome} ({cliente_cnpj}) | **Vendedor:** {vendedor_nome}")
            st.markdown(f"**Detalhes:** {orc_data['tipo_cliente']} | {orc_data['estado']} | Frete: {orc_data['frete']} | Tipo Pedido: {orc_data['tipo_pedido']}")
            st.markdown(f"**Preço Base do Orçamento:** {_format_brl(preco_m2_base)}")
            if orc_data['observacao']:
                 st.info(f"Obs: {orc_data['observacao']}")

            if confecc:
                st.markdown("### ⬛ Itens Confeccionados")
                for c in confecc:
                    # c[5] é o preco_unitario (travado)
                    preco_unit = c[5] if c[5] is not None else preco_m2_base
                    st.markdown(f"- **{c[0]}**: {c[3]}x {c[1]:.2f}m x {c[2]:.2f}m | Cor: {c[4]} | R$/m²: {_format_brl(preco_unit)}")

            if bob:
                st.markdown("### 🔘 Itens Bobinas")
                for b in bob:
                    # b[6] é o preco_unitario (travado)
                    esp = f" | Esp: {b[5]:.2f}mm" if b[5] is not None else ""
                    preco_unit = b[6] if b[6] is not None else preco_m2_base
                    st.markdown(f"- **{b[0]}**: {b[3]}x {b[1]:.2f}m | Largura: {b[2]:.2f}m{esp} | Cor: {b[4]} | R$/m: {_format_brl(preco_unit)}")

            st.markdown("---")
            col1, col2, col3 = st.columns([1,1,1])
            with col1:
                # Reabrir
                if st.button("🔄 Reabrir", key=f"reabrir_{orc_id}"):
                    
                    # Mapeia itens incluindo o preco_unitario para o session state
                    itens_confecc_reabrir = [dict(zip(['produto','comprimento','largura','quantidade','cor','preco_unitario'],c)) for c in confecc]
                    itens_bob_reabrir = [dict(zip(['produto','comprimento','largura','quantidade','cor','espessura','preco_unitario'],b)) for b in bob]

                    st.session_state.update({
                        "cliente_nome": orc[2],
                        "cliente_cnpj": orc[3],
                        "tipo_cliente": orc[4],
                        "estado": orc[5],
                        "frete": orc[6],
                        "tipo_pedido": orc[7],
                        "vendedor_nome": orc[8],
                        "vendedor_tel": orc[9],
                        "vendedor_email": orc[10],
                        "obs": orc[11],
                        "preco_m2": preco_m2_base, 
                        # PASSA OS ITENS COM O PREÇO TRAVADO
                        "itens_confeccionados": itens_confecc_reabrir,
                        "bobinas_adicionadas": itens_bob_reabrir,
                        "menu_index": 0 
                    })
                    st.success(f"Orçamento ID {orc_id} carregado no formulário.")
                    st.rerun()

            with col2:
                # Baixar PDF
                # Mapeia itens para dicionário antes de passar para o PDF (necessário para a função)
                itens_conf_pdf = [dict(zip(['produto','comprimento','largura','quantidade','cor','preco_unitario'], c)) for c in confecc]
                itens_bob_pdf = [dict(zip(['produto','comprimento','largura','quantidade','cor','espessura','preco_unitario'], b)) for b in bob]

                resumo_conf_calc = calcular_valores_confeccionados(
                    itens_conf_pdf, preco_m2_base, orc_data['tipo_cliente'], orc_data['estado'], orc_data['tipo_pedido']
                ) if itens_conf_pdf else None

                resumo_bob_calc = calcular_valores_bobinas(
                    itens_bob_pdf, preco_m2_base, orc_data['tipo_pedido']
                ) if itens_bob_pdf else None
                
                pdf_bytes = gerar_pdf(
                    orc_id, 
                    cliente={
                        "nome": orc[2],
                        "cnpj": orc[3],
                        "tipo_cliente": orc[4],
                        "estado": orc[5],
                        "frete": orc[6],
                        "tipo_pedido": orc[7]
                    },
                    vendedor={
                        "nome": orc[8],
                        "tel": orc[9],
                        "email": orc[10]
                    },
                    itens_confeccionados=itens_conf_pdf,
                    itens_bobinas=itens_bob_pdf,
                    resumo_conf=resumo_conf_calc, 
                    resumo_bob=resumo_bob_calc,
                    observacao=orc[11],
                    preco_m2=preco_m2_base, # Passa o preco_m2_base como fallback
                    tipo_cliente=orc_data['tipo_cliente'],
                    estado=orc_data['estado']
                ) 
                st.download_button(
                    "📄 Baixar PDF",
                    data=pdf_bytes,
                    file_name=f"orcamento_{orc_id}.pdf",
                    mime="application/pdf",
                    key=f"download_historico_{orc_id}"
                )
