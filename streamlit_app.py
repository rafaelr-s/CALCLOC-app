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
def gerar_pdf(cliente, vendedor, itens_confeccionados, itens_bobinas, resumo_conf, resumo_bob, observacao):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)

    # -------------------------
    # Cabeçalho
    # -------------------------
    pdf.cell(0, 10, "Orçamento - Grupo Locomotiva", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=9)
    pdf.cell(0, 6, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.ln(4)

    # -------------------------
    # Dados do Cliente
    # -------------------------
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, "CLIENTE", ln=True)
    pdf.set_font("Arial", size=9)
    pdf.multi_cell(0, 5, f"Nome/Razão: {cliente.get('nome','')}")
    if cliente.get("cnpj"):
        pdf.multi_cell(0, 5, f"CNPJ/CPF: {cliente['cnpj']}")
    pdf.ln(3)

    # -------------------------
    # Itens Confeccionados
    # -------------------------
    if itens_confeccionados:
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 6, "ITENS CONFECCIONADOS", ln=True)
        pdf.set_font("Arial", size=8)
        for item in itens_confeccionados:
            txt = f"{item['quantidade']}x {item['produto']} - {item['comprimento']}m x {item['largura']}m | Cor: {item.get('cor','')}"
            pdf.multi_cell(0, 5, txt)

        if resumo_conf:
            m2_total, valor_bruto, valor_ipi, valor_final = resumo_conf
            pdf.ln(3)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, "Resumo - Confeccionados", ln=True)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 8, f"📏 Área Total: {str(f'{m2_total:.2f}'.replace('.', ','))} m²", ln=True)
            pdf.cell(0, 8, f"💵 Valor Bruto: {_format_brl(valor_bruto)}", ln=True)
            pdf.cell(0, 8, f"🧾 IPI (3,25%): {_format_brl(valor_ipi)}", ln=True)
            pdf.cell(0, 8, f"💰 Valor Final com IPI: {_format_brl(valor_final)}", ln=True)
            pdf.ln(10)

    # -------------------------
    # Itens Bobinas
    # -------------------------
    if itens_bobinas:
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 6, "ITENS BOBINAS", ln=True)
        pdf.set_font("Arial", size=8)
        for item in itens_bobinas:
            txt = f"{item['quantidade']}x {item['produto']} - {item['comprimento']}m | Largura: {item['largura']}m | Cor: {item.get('cor','')}"
            if "espessura" in item:
                txt += f" | Esp: {item['espessura']}mm"
            pdf.multi_cell(0, 5, txt)

        if resumo_bob:
            m_total, valor_bruto, valor_ipi, valor_final = resumo_bob
            pdf.ln(3)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, "Resumo - Bobinas", ln=True)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 8, f"📏 Total de Metros Lineares: {str(f'{m_total:.2f}'.replace('.', ','))} m", ln=True)
            pdf.cell(0, 8, f"💵 Valor Bruto: {_format_brl(valor_bruto)}", ln=True)
            pdf.cell(0, 8, f"🧾 IPI (9,75%): {_format_brl(valor_ipi)}", ln=True)
            pdf.cell(0, 8, f"💰 Valor Final com IPI: {_format_brl(valor_final)}", ln=True)
            pdf.ln(10)

    # -------------------------
    # Observações
    # -------------------------
    if observacao:
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 6, "OBSERVAÇÕES", ln=True)
        pdf.set_font("Arial", size=8)
        pdf.multi_cell(0, 5, str(observacao))
        pdf.ln(3)

    # -------------------------
    # Vendedor
    # -------------------------
    if vendedor:
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 8, f"Vendedor: {vendedor.get('nome','')}\nTelefone: {vendedor.get('tel','')}\nE-mail: {vendedor.get('email','')}")
        pdf.ln(5)

    # -------------------------
    # Retorno como BytesIO
    # -------------------------
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
# Funções de cálculo
# ============================
def calcular_valores_confeccionados(itens, preco_m2):
    m2_total = sum(item['comprimento'] * item['largura'] * item['quantidade'] for item in itens)
    valor_bruto = m2_total * preco_m2
    valor_ipi = valor_bruto * 0.0325
    valor_final = valor_bruto + valor_ipi
    return m2_total, valor_bruto, valor_ipi, valor_final

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

# Dados do Cliente
st.subheader("👤 Dados do Cliente")
col1, col2 = st.columns(2)
with col1:
    Cliente_nome = st.text_input("Razão ou Nome Fantasia", value=st.session_state.get("Cliente_nome",""))
with col2:
    Cliente_CNPJ = st.text_input("CNPJ ou CPF (Opcional)", value=st.session_state.get("Cliente_CNPJ",""))

# Observações
st.subheader("🔎 Observações")
Observacao = st.text_area("Insira aqui alguma observação sobre o orçamento (opcional)")

# Vendedor
st.subheader("🗣️ Vendedor(a)")
col1, col2 = st.columns(2)
with col1:
    vendedor_nome = st.text_input("Nome")
    vendedor_tel = st.text_input("Telefone")
with col2:
    vendedor_email = st.text_input("E-mail")

# Botão PDF
if st.button("📄 Gerar Orçamento em PDF"):
    cliente = {"nome": Cliente_nome, "cnpj": Cliente_CNPJ}
    vendedor = {"nome": vendedor_nome, "tel": vendedor_tel, "email": vendedor_email}
    resumo_conf = calcular_valores_confeccionados(st.session_state['itens_confeccionados'], 10) if st.session_state['itens_confeccionados'] else None
    resumo_bob = calcular_valores_bobinas(st.session_state['bobinas_adicionadas'], 10) if st.session_state['bobinas_adicionadas'] else None
    pdf_buffer = gerar_pdf(cliente, vendedor, st.session_state['itens_confeccionados'], st.session_state['bobinas_adicionadas'], resumo_conf, resumo_bob, Observacao)

    st.download_button(
        label="⬇️ Baixar Orçamento em PDF",
        data=pdf_buffer,
        file_name="orcamento.pdf",
        mime="application/pdf"
    )
