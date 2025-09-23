import streamlit as st
from datetime import datetime
import pytz
from fpdf import FPDF
from io import BytesIO

# ============================
# Função para formatar valores em R$
# ============================
def _format_brl(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ============================
# Função para gerar PDF
# ============================
def gerar_pdf(cliente, vendedor, itens_confeccionados, itens_bobinas, resumo_conf, resumo_bob, observacao, preco_m2, tipo_cliente="", estado=""):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", "B", 14)

    # Cabeçalho
    pdf.cell(0, 12, "Orçamento - Grupo Locomotiva", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=9)
    brasilia_tz = pytz.timezone("America/Sao_Paulo")
    pdf.cell(0, 6, f"Data: {datetime.now(brasilia_tz).strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.ln(4)

    # Dados do Cliente
    pdf.set_font("Arial", "B", 11)
    pdf.cell(200, 6, "Cliente", ln=True)
    pdf.set_font("Arial", size=9)
    pdf.multi_cell(200, 5, f"Nome/Razão: {cliente.get('nome','')}")    

    cnpj_cpf = cliente.get("cnpj", "").strip()
    if cnpj_cpf:
        pdf.multi_cell(200, 5, f"CNPJ/CPF: {cnpj_cpf}")
    
    if cliente.get("tipo_cliente"):
        pdf.multi_cell(200, 5, f"Tipo do Cliente: {cliente['tipo_cliente']}")
    if cliente.get("estado"):
        pdf.multi_cell(200, 5, f"Estado: {cliente['estado']}")
    pdf.ln(2)
        
    # Itens Confeccionados
    if itens_confeccionados:
        pdf.set_font("Arial", "B", 11)
        pdf.cell(200, 6, "Itens Confeccionados", ln=True)
        pdf.set_font("Arial", size=8)
        for item in list(itens_confeccionados):
            area_item = item['comprimento'] * item['largura'] * item['quantidade']
            valor_item = area_item * preco_m2
            txt = (
                f"{item['quantidade']}x {item['produto']} - {item['comprimento']}m x {item['largura']}m "
                f"| Cor: {item.get('cor','')} | Valor Bruto: {_format_brl(valor_item)}"
            )
            pdf.multi_cell(200, 5, txt)
            pdf.ln(1)

        if resumo_conf:
            m2_total, valor_bruto, valor_ipi, valor_final, valor_st, aliquota_st = resumo_conf
            pdf.ln(3)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(200, 10, "Resumo - Confeccionados", ln=True)
            pdf.set_font("Arial", "", 10)
            pdf.cell(200, 8, f"Preço por m² utilizado: {_format_brl(preco_m2)}", ln=True)
            pdf.cell(200, 8, f"Área Total: {str(f'{m2_total:.2f}'.replace('.', ','))} m²", ln=True)
            pdf.cell(200, 8, f"Valor Bruto: {_format_brl(valor_bruto)}", ln=True)
            pdf.cell(200, 8, f"IPI (3,25%): {_format_brl(valor_ipi)}", ln=True)
            if valor_st > 0:
                pdf.cell(200, 8, f"ST ({aliquota_st}%): {_format_brl(valor_st)}", ln=True)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(200, 10, f"Valor Final com IPI{(' + ST' if valor_st>0 else '')}: {_format_brl(valor_final)}", ln=True)
            pdf.ln(10)

    # Itens Bobinas
    if itens_bobinas:
        pdf.set_font("Arial", "B", 11)
        pdf.cell(200, 6, "Itens Bobina", ln=True)
        pdf.set_font("Arial", size=8)
        for item in list(itens_bobinas):
            metros_item = item['comprimento'] * item['quantidade']
            valor_item = metros_item * preco_m2
            txt = (
                f"{item['quantidade']}x {item['produto']} - {item['comprimento']}m | Largura: {item['largura']}m "
                f"| Cor: {item.get('cor','')} | Valor Bruto: {_format_brl(valor_item)}"
            )
            if "espessura" in item:
                txt += f" | Esp: {item['espessura']}mm"
            pdf.multi_cell(200, 5, txt)
            pdf.ln(1)

        if resumo_bob:
            m_total, valor_bruto, valor_ipi, valor_final = resumo_bob
            pdf.ln(3)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(200, 10, "Resumo - Bobinas", ln=True)
            pdf.set_font("Arial", "", 10)
            pdf.cell(200, 8, f"Preço por metro linear utilizado: {_format_brl(preco_m2)}", ln=True)
            pdf.cell(200, 8, f"Total de Metros Lineares: {str(f'{m_total:.2f}'.replace('.', ','))} m", ln=True)
            pdf.cell(200, 8, f"Valor Bruto: {_format_brl(valor_bruto)}", ln=True)
            pdf.cell(200, 8, f"IPI (9,75%): {_format_brl(valor_ipi)}", ln=True)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(200, 10, f"Valor Final com IPI: {_format_brl(valor_final)}", ln=True)
            pdf.ln(10)

    # Observações
    if observacao:
        pdf.set_font("Arial", "B", 11)
        pdf.cell(200, 11, "Observações", ln=True)
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(200, 11, str(observacao))
        pdf.ln(4)

    # Vendedor
    if vendedor:
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(200, 8, f"Vendedor: {vendedor.get('nome','')}\nTelefone: {vendedor.get('tel','')}\nE-mail: {vendedor.get('email','')}")
        pdf.ln(5)

    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

# ============================
# Inicialização de listas
# ============================
if "itens_confeccionados" not in st.session_state:
    st.session_state["itens_confeccionados"] = []
if "bobinas_adicionadas" not in st.session_state:
    st.session_state["bobinas_adicionadas"] = []

# ============================
# Tabelas de ICMS e ST
# ============================
icms_por_estado = {
    "SP": 18, "MG": 12, "PR": 12, "RJ": 12, "RS": 12, "SC": 12
}
todos_estados = [
    "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MT","MS",
    "PA","PB","PE","PI","RN","RO","RR","SE","TO"
]
for uf in todos_estados:
    if uf not in icms_por_estado:
        icms_por_estado[uf] = 7

st_por_estado = {
    "SP": 14, "RJ": 27, "MG": 22, "ES": 0, "PR": 22, "RS": 20, "SC": 0,
    "BA": 29, "PE": 29, "CE": 19, "RN": 0, "PB": 29, "SE": 0, "AL": 29,
    "DF": 29, "GO": 0, "MS": 0, "MT": 22, "AM": 29, "PA": 26, "RO": 0,
    "RR": 27, "AC": 27, "AP": 29, "MA": 29, "PI": 22, "TO": 0
}

def calcular_valores_confeccionados(itens, preco_m2, tipo_cliente="", estado=""):
    m2_total = sum(item['comprimento'] * item['largura'] * item['quantidade'] for item in itens)
    valor_bruto = m2_total * preco_m2
    valor_ipi = valor_bruto * 0.0325
    valor_final = valor_bruto + valor_ipi
    valor_st = 0
    aliquota_st = 0
    if any(item.get('produto') == "Encerado" for item in itens) and tipo_cliente == "Revenda":
        aliquota_st = st_por_estado.get(estado, 0)
        valor_st = valor_final * aliquota_st / 100
        valor_final += valor_st
    return m2_total, valor_bruto, valor_ipi, valor_final, valor_st, aliquota_st

def calcular_valores_bobinas(itens, preco_m2):
    m_total = sum(item['comprimento'] * item['quantidade'] for item in itens)
    valor_bruto = m_total * preco_m2
    valor_ipi = valor_bruto * 0.0975
    valor_final = valor_bruto + valor_ipi
    return m_total, valor_bruto, valor_ipi, valor_final

# ============================
# Interface Streamlit
# ============================
st.set_page_config(page_title="Calculadora Grupo Locomotiva", page_icon="📏", layout="centered")
st.title("Orçamento - Grupo Locomotiva")

brasilia_tz = pytz.timezone("America/Sao_Paulo")
data_hora_brasilia = datetime.now(brasilia_tz).strftime("%d/%m/%Y %H:%M")
st.markdown(f"🕒 **Data e Hora:** {data_hora_brasilia}")

# --- Cliente ---
st.subheader("👤 Dados do Cliente")
col1, col2 = st.columns(2)
with col1:
    Cliente_nome = st.text_input("Razão ou Nome Fantasia", value=st.session_state.get("Cliente_nome",""))
with col2:
    Cliente_CNPJ = st.text_input("CNPJ ou CPF (Opcional)", value=st.session_state.get("Cliente_CNPJ",""))

tipo_cliente = st.selectbox("Tipo do Cliente:", [" ","Consumidor Final", "Revenda"])
estado = st.selectbox("Estado do Cliente:", options=list(icms_por_estado.keys()))

# --- Produto (lista completa) ---
produtos_lista = [
    " ","Lonil de PVC","Lonil KP","KP Inflável","Encerado","Duramax","Lonaleve",
    "Lona Sunset Galpão","Lona Sunset Leve","Lona ATX","Lona Transparente",
    "Filme Stretch","Tatame EVA","Geomembrana ATX","Cristal","Block Lux","Adesivo Vinílico"
]

produto = st.selectbox("Nome do Produto:", options=produtos_lista)
tipo_produto = st.radio("Tipo do Produto:", ["Confeccionado", "Bobina"])
preco_m2 = st.number_input("Preço por m² ou metro linear (R$):", min_value=0.0, value=0.0, step=0.01)

aliquota_icms = icms_por_estado.get(estado, 7)
st.info(f"🔹 Alíquota de ICMS para {estado}: **{aliquota_icms}% (já incluso no preço)**")

if produto == "Encerado" and tipo_cliente == "Revenda":
    aliquota_st = st_por_estado.get(estado, 0)
    st.warning(f"⚠️ Este produto possui ST no estado {estado} aproximado a: **{aliquota_st}%**")

# ============================
# Observações e Vendedor
# ============================
st.subheader("🔎 Observações")
Observacao = st.text_area("Insira aqui alguma observação sobre o orçamento (opcional)")

st.subheader("🗣️ Vendedor(a)")
col1, col2 = st.columns(2)
with col1:
    vendedor_nome = st.text_input("Nome")
    vendedor_tel = st.text_input("Telefone")
with col2:
    vendedor_email = st.text_input("E-mail")

# --- Botão Gerar PDF ---
if st.button("📄 Gerar Orçamento em PDF"):
    cliente = {
        "nome": Cliente_nome,
        "cnpj": Cliente_CNPJ,
        "tipo_cliente": tipo_cliente,
        "estado": estado
    }
    vendedor = {"nome": vendedor_nome, "tel": vendedor_tel, "email": vendedor_email}

    resumo_conf = calcular_valores_confeccionados(
        st.session_state['itens_confeccionados'],
        preco_m2,
        tipo_cliente,
        estado
    ) if st.session_state['itens_confeccionados'] else None

    resumo_bob = calcular_valores_bobinas(
        st.session_state['bobinas_adicionadas'],
        preco_m2
    ) if st.session_state['bobinas_adicionadas'] else None

    pdf_buffer = gerar_pdf(
        cliente,
        vendedor,
        st.session_state['itens_confeccionados'],
        st.session_state['bobinas_adicionadas'],
        resumo_conf,
        resumo_bob,
        Observacao,
        preco_m2,
        tipo_cliente=tipo_cliente,
        estado=estado
    )

    st.download_button(
        label="⬇️ Baixar Orçamento em PDF",
        data=pdf_buffer,
        file_name="orcamento.pdf",
        mime="application/pdf"
    )

st.markdown("🔒 Os dados acima são apenas para inclusão no orçamento (PDF ou impressão futura).")
