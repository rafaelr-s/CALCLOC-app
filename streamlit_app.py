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

    # Cabeçalho
    pdf.cell(0, 10, "Orçamento - Grupo Locomotiva", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=9)
    pdf.cell(0, 6, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.ln(4)

    # Dados do Cliente
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, "CLIENTE", ln=True)
    pdf.set_font("Arial", size=9)
    pdf.multi_cell(0, 5, f"Nome/Razão: {cliente.get('nome','')}")
    cnpj_cliente = str(cliente.get('cnpj','') or '').strip()
    if cnpj_cliente:
        # Formata CNPJ/CPF
        if len(cnpj_cliente) == 11:  # CPF
            cnpj_formatado = f"{cnpj_cliente[:3]}.{cnpj_cliente[3:6]}.{cnpj_cliente[6:9]}-{cnpj_cliente[9:]}"
        elif len(cnpj_cliente) == 14:  # CNPJ
            cnpj_formatado = f"{cnpj_cliente[:2]}.{cnpj_cliente[2:5]}.{cnpj_cliente[5:8]}/{cnpj_cliente[8:12]}-{cnpj_cliente[12:]}"
        else:
            cnpj_formatado = cnpj_cliente
        pdf.cell(0, 5, f"CNPJ/CPF: {cnpj_formatado}", ln=True)
    pdf.ln(3)

    # Itens Confeccionados
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

    # Itens Bobinas
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

    # Observações
    if observacao:
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 6, "OBSERVAÇÕES", ln=True)
        pdf.set_font("Arial", size=8)
        pdf.multi_cell(0, 5, str(observacao))
        pdf.ln(3)

    # Vendedor
    if vendedor:
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 8, f"Vendedor: {vendedor.get('nome','')}\nTelefone: {vendedor.get('tel','')}\nE-mail: {vendedor.get('email','')}")
        pdf.ln(5)

    # Retorno como BytesIO
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

# --- Cliente ---
st.subheader("👤 Dados do Cliente")
col1, col2 = st.columns(2)
with col1:
    Cliente_nome = st.text_input("Razão ou Nome Fantasia", value=st.session_state.get("Cliente_nome",""))
with col2:
    Cliente_CNPJ = st.text_input("CNPJ ou CPF (Opcional)", value=st.session_state.get("Cliente_CNPJ",""))

# --- Data ---
brasilia_tz = pytz.timezone("America/Sao_Paulo")
data_hora_brasilia = datetime.now(brasilia_tz).strftime("%d/%m/%Y %H:%M")
st.markdown(f"🕒 **Data e Hora:** {data_hora_brasilia}")

# ---------------------------
# Lista de produtos e opções
# ---------------------------
produtos_lista = [
    " ","Lonil de PVC","Lonil KP","Lonil Inflável KP","Encerado","Duramax",
    "Lonaleve","Sider Truck Teto","Sider Truck Lateral","Capota Marítima",
    "Night&Day Plus 1,40","Night&Day Plus 2,00","Night&Day Listrado","Vitro 0,40",
    "Vitro 0,50","Vitro 0,60","Vitro 0,80","Vitro 1,00","Durasol","Poli Light",
    "Sunset","Tenda","Tenda 2,3x2,3","Acrylic","Agora","Lona Galpão Teto",
    "Lona Galpão Lateral","Tela de Sombreamento 30%","Tela de Sombreamento 50%",
    "Tela de Sombreamento 80%","Geomembrana RV 0,42","Geomembrana RV 0,80",
    "Geomembrana RV 1,00","Geomembrana ATX 0,80","Geomembrana ATX 1,00",
    "Geomembrana ATX 1,50","Geo Bio s/ reforço 1,00","Geo Bio s/ reforço 1,20",
    "Geo Bio s/ reforço 1,50","Geo Bio c/ reforço 1,20","Cristal com Pó",
    "Cristal com Papel","Cristal Colorido","Filme Liso","Filme Kamurcinha",
    "Filme Verniz","Block Lux","Filme Dimension","Filme Sarja","Filme Emborrachado",
    "Filme Pneumático","Adesivo Branco Brilho 0,08","Adesivo Branco Brilho 0,10",
    "Adesivo Branco Fosco 0,10","Adesivo Preto Brilho 0,08","Adesivo Preto Fosco 0,10",
    "Adesivo Transparente Brilho 0,08","Adesivo Transparente Jateado 0,08",
    "Adesivo Mascara Brilho 0,08","Adesivo Aço Escovado 0,08"
]
prefixos_espessura = ("Geomembrana", "Geo", "Vitro", "Cristal", "Filme", "Adesivo", "Block Lux")

produto = st.selectbox("Nome do Produto:", options=produtos_lista)
tipo_produto = st.radio("Tipo do Produto:", ["Confeccionado", "Bobina"])
preco_m2 = st.number_input("Preço por m² ou metro linear (R$):", min_value=0.0, value=0.0, step=0.01)
produto_exige_espessura = produto.startswith(prefixos_espessura)

# ============================
# Seção Confeccionado
# ============================
if tipo_produto == "Confeccionado":
    st.subheader("➕ Adicionar Item Confeccionado")
    col1, col2, col3 = st.columns(3)
    with col1:
        comprimento = st.number_input("Comprimento (m):", min_value=0.01, value=1.0, step=0.1, key="comp_conf")
    with col2:
        largura = st.number_input("Largura (m):", min_value=0.01, value=1.0, step=0.1, key="larg_conf")
    with col3:
        quantidade = st.number_input("Quantidade:", min_value=1, value=1, step=1, key="qtd_conf")

    if st.button("➕ Adicionar Medida"):
        st.session_state['itens_confeccionados'].append({
            'produto': produto,
            'comprimento': comprimento,
            'largura': largura,
            'quantidade': quantidade,
            'cor': ""
        })

    if st.session_state['itens_confeccionados']:
        st.subheader("📋 Itens Adicionados")
        for idx, item in enumerate(st.session_state['itens_confeccionados'][:]):  # cópia da lista
            col1, col2, col3, col4 = st.columns([3,2,2,1])
            with col1:
                st.markdown(f"**{item['produto']}**")
                st.markdown(f"🔹 {item['quantidade']}x {item['comprimento']}m x {item['largura']}m")
            with col2:
                cor = st.text_input("Cor:", value=item['cor'], key=f"cor_conf_{idx}")
                st.session_state['itens_confeccionados'][idx]['cor'] = cor
            with col4:
                remover = st.button("❌", key=f"remover_conf_{idx}")
                if remover:
                    st.session_state['itens_confeccionados'].pop(idx)
                    st.experimental_rerun()
m2_total, valor_bruto, valor_ipi, valor_final = calcular_valores_confeccionados(
        st.session_state['itens_confeccionados'], preco_m2
    )

st.write(f"📏 Área Total: **{m2_total:.2f} m²**".replace(".", ","))
st.write(f"💵 Valor Bruto: **{_format_brl(valor_bruto)}**")
st.write(f"🧾 IPI (3.25%): **{_format_brl(valor_ipi)}**")
st.write(f"💰 Valor Final com IPI (3.25%): **{_format_brl(valor_final)}**")
if aliquota_st:
    valor_com_st = valor_final * (1 + aliquota_st / 100)
    st.error(f"💰 Valor Aproximado com ST: **{_format_brl(valor_com_st)}**")

    if st.button("🧹 Limpar Itens"):
        st.session_state['itens_confeccionados'] = []
        st.experimental_rerun()

# ============================
# Seção Bobina
# ============================
if tipo_produto == "Bobina":
    st.subheader("➕ Adicionar Bobina")
    col1, col2, col3 = st.columns(3)
    with col1:
        comprimento = st.number_input("Comprimento (m):", min_value=0.01, value=50.0, step=0.1, key="comp_bob")
    with col2:
        largura_bobina = st.number_input("Largura da Bobina (m):", min_value=0.01, value=1.4, step=0.01, key="larg_bob")
    with col3:
        quantidade = st.number_input("Quantidade:", min_value=0, value=0, step=1, key="qtd_bob")

    espessura_bobina = None
    if produto_exige_espessura:
        espessura_bobina = st.number_input("Espessura da Bobina (mm):", min_value=0.01, value=0.10, step=0.01, key="esp_bob")

    if st.button("➕ Adicionar Bobina"):
        item_bobina = {
            'produto': produto,
            'comprimento': comprimento,
            'largura': largura_bobina,
            'quantidade': quantidade,
            'cor': ""
        }
        if produto_exige_espessura:
            item_bobina['espessura'] = espessura_bobina
        st.session_state['bobinas_adicionadas'].append(item_bobina)

    if st.session_state['bobinas_adicionadas']:
        st.subheader("📋 Bobinas Adicionadas")
        for idx, item in enumerate(st.session_state['bobinas_adicionadas'][:]):  # cópia da lista
            col1, col2, col3, col4 = st.columns([4,2,2,1])
            with col1:
                detalhes = (f"🔹 {item['quantidade']}x {item['comprimento']}m | Largura: {item['largura']}m")
                if 'espessura' in item:
                    detalhes += f" | Esp: {item['espessura']}mm"
                st.markdown(f"**{item['produto']}**")
                st.markdown(detalhes)
            with col2:
                cor = st.text_input("Cor:", value=item['cor'], key=f"cor_bob_{idx}")
                st.session_state['bobinas_adicionadas'][idx]['cor'] = cor
            with col4:
                remover = st.button("❌", key=f"remover_bob_{idx}")
                if remover:
                    st.session_state['bobinas_adicionadas'].pop(idx)
                    st.experimental_rerun()
    st.write(f"📏 Total de Metros Lineares: **{m_total:.2f} m**".replace(".", ","))
    st.write(f"💵 Valor Bruto: **{_format_brl(valor_bruto)}**")
    st.write(f"🧾 IPI (9.75%): **{_format_brl(valor_ipi)}**")
    st.write(f"💰 Valor Final com IPI (9.75%): **{_format_brl(valor_final)}**")  
    
    if st.button("🧹 Limpar Itens"):
        st.session_state['itens_confeccionados'] = []
        st.experimental_rerun()

# ============================
# Observações
# ============================
st.subheader("🔎 Observações")
Observacao = st.text_area("Insira aqui alguma observação sobre o orçamento (opcional)")

# ============================
# Vendedor
# ============================
st.subheader("🗣️ Vendedor(a)")
col1, col2 = st.columns(2)
with col1:
    vendedor_nome = st.text_input("Nome")
    vendedor_tel = st.text_input("Telefone")
with col2:
    vendedor_email = st.text_input("E-mail")

# ============================
# Botão Gerar PDF
# ============================
if st.button("📄 Gerar Orçamento em PDF"):
    cliente = {"nome": Cliente_nome, "cnpj": Cliente_CNPJ}
    vendedor = {"nome": vendedor_nome, "tel": vendedor_tel, "email": vendedor_email}
    resumo_conf = calcular_valores_confeccionados(st.session_state['itens_confeccionados'], preco_m2) if st.session_state['itens_confeccionados'] else None
    resumo_bob = calcular_valores_bobinas(st.session_state['bobinas_adicionadas'], preco_m2) if st.session_state['bobinas_adicionadas'] else None

    pdf_buffer = gerar_pdf(cliente, vendedor,
                           st.session_state['itens_confeccionados'],
                           st.session_state['bobinas_adicionadas'],
                           resumo_conf,
                           resumo_bob,
                           Observacao)

    st.download_button(
        label="⬇️ Baixar Orçamento em PDF",
        data=pdf_buffer,
        file_name="orcamento.pdf",
        mime="application/pdf"
    )

st.markdown("🔒 Os dados acima são apenas para inclusão no orçamento (PDF ou impressão futura).")
