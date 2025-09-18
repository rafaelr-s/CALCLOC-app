from datetime import datetime
import pytz
import streamlit as st
from fpdf import FPDF
from io import BytesIO

def _format_brl(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def gerar_pdf_fpdf(cliente, vendedor, itens_conf, itens_bob, resumo_conf, resumo_bob, observacao, estado, aliquota_icms, aliquota_st):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_auto_page_break(False)

    # cabeçalho
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, "ORÇAMENTO DETALHADO", ln=True, align='C')
    pdf.ln(2)
    pdf.set_font("Arial", size=9)
    pdf.cell(0, 6, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.ln(4)

    # cliente
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, "CLIENTE", ln=True)
    pdf.set_font("Arial", size=9)
    pdf.cell(0, 5, f"Nome/Razão: {cliente.get('nome','')}", ln=True)
    pdf.cell(0, 5, f"CNPJ: {cliente.get('cnpj','')}", ln=True)
    pdf.ln(3)

    # vendedor
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, "VENDEDOR", ln=True)
    pdf.set_font("Arial", size=9)
    pdf.cell(0, 5, f"Nome: {vendedor.get('nome','')}", ln=True)
    pdf.cell(0, 5, f"Tel: {vendedor.get('tel','')}", ln=True)
    pdf.cell(0, 5, f"E-mail: {vendedor.get('email','')}", ln=True)
    pdf.ln(4)

    # itens confeccionados
    if itens_conf:
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 6, "ITENS CONFECCIONADOS", ln=True)
        pdf.set_font("Arial", size=8)
        for item in itens_conf:
            txt = f"{item['quantidade']}x {item['produto']} - {item['comprimento']}m x {item['largura']}m | Cor: {item.get('cor','')}"
            pdf.multi_cell(0, 5, txt)
        if resumo_conf:
            m2, bruto, ipi, final = resumo_conf
            pdf.ln(1)
            pdf.set_font("Arial", size=9)
            pdf.cell(0, 5, f"Área total: {m2:.2f} m²  |  Valor bruto: {_format_brl(bruto)}", ln=True)
            pdf.cell(0, 5, f"IPI (3.25%): {_format_brl(ipi)}  |  Total c/ IPI: {_format_brl(final)}", ln=True)
            if aliquota_icms is not None:
                pdf.cell(0, 5, f"ICMS (incluso): {aliquota_icms}%", ln=True)
            if aliquota_st:
                pdf.cell(0, 5, f"ST aproximada: {aliquota_st}%", ln=True)
            pdf.ln(3)

    # itens bobinas
    if itens_bob:
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 6, "ITENS BOBINAS", ln=True)
        pdf.set_font("Arial", size=8)
        for item in itens_bob:
            txt = f"{item['quantidade']}x {item['produto']} - {item['comprimento']}m | Largura: {item['largura']}m | Cor: {item.get('cor','')}"
            if 'espessura' in item:
                txt += f" | Esp: {item['espessura']}mm"
            pdf.multi_cell(0, 5, txt)
        if resumo_bob:
            m, bruto, ipi, final = resumo_bob
            pdf.ln(1)
            pdf.set_font("Arial", size=9)
            pdf.cell(0, 5, f"Metros totais: {m:.2f} m  |  Valor bruto: {_format_brl(bruto)}", ln=True)
            pdf.cell(0, 5, f"IPI (9.75%): {_format_brl(ipi)}  |  Total c/ IPI: {_format_brl(final)}", ln=True)
            if aliquota_icms is not None:
                pdf.cell(0, 5, f"ICMS (incluso): {aliquota_icms}%", ln=True)
            if aliquota_st:
                pdf.cell(0, 5, f"ST aproximada: {aliquota_st}%", ln=True)
            pdf.ln(3)

    # observações
    if observacao:
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 6, "OBSERVAÇÕES", ln=True)
        pdf.set_font("Arial", size=8)
        pdf.multi_cell(0, 5, observacao)
        pdf.ln(3)

    # Gera bytes e retorna BytesIO
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    buffer = BytesIO(pdf_bytes)
    buffer.seek(0)
    return buffer

# ============================
# Inicialização de listas no session_state
# ============================
if "itens_confeccionados" not in st.session_state:
    st.session_state["itens_confeccionados"] = []
if "bobinas_adicionadas" not in st.session_state:
    st.session_state["bobinas_adicionadas"] = []

# ============================
# Tabelas de ICMS e ST
# ============================
icms_por_estado = {
    "SP": 18,
    "MG": 12, "PR": 12, "RJ": 12, "RS": 12, "SC": 12,
}

# Estados restantes 7%
todos_estados = [
    "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MT","MS",
    "PA","PB","PE","PI","RN","RO","RR","SE","TO"
]
for uf in todos_estados:
    icms_por_estado[uf] = 7

# Percentuais de ST (última atualização geral Brasil)
st_por_estado = {
    "SP": 14, "RJ": 27, "MG": 22, "ES": 0, "PR": 22, "RS": 20, "SC": 0,
    "BA": 29, "PE": 29, "CE": 19, "RN": 0, "PB": 29, "SE": 0, "AL": 29,
    "DF": 29, "GO": 0, "MS": 0, "MT": 22,
    "AM": 29, "PA": 26, "RO": 0, "RR": 27, "AC": 27, "AP": 29, "MA": 29, "PI": 22, "TO": 0
}

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
# Lista de Produtos
# ============================
produtos_lista = [
    " ", "Lonil de PVC", "Lonil KP", "Lonil Inflável KP", "Encerado", "Duramax", "Lonaleve",
    "Sider Truck Teto", "Sider Truck Lateral", "Capota Marítima", "Night&Day Plus 1,40",
    "Night&Day Plus 2,00", "Night&Day Listrado", "Vitro 0,40", "Vitro 0,50", "Vitro 0,60",
    "Vitro 0,80", "Vitro 1,00", "Durasol", "Poli Light", "Sunset", "Tenda", "Tenda 2,3x2,3",
    "Acrylic", "Agora", "Lona Galpão Teto", "Lona Galpão Lateral",
    "Tela de Sombreamento 30%", "Tela de Sombreamento 50%", "Tela de Sombreamento 80%",
    "Geomembrana RV 0,42", "Geomembrana RV 0,80", "Geomembrana RV 1,00",
    "Geomembrana ATX 0,80", "Geomembrana ATX 1,00", "Geomembrana ATX 1,50",
    "Geo Bio s/ reforço 1,00", "Geo Bio s/ reforço 1,20", "Geo Bio s/ reforço 1,50",
    "Geo Bio c/ reforço 1,20", "Cristal com Pó", "Cristal com Papel", "Cristal Colorido",
    "Filme Liso", "Filme Kamurcinha", "Filme Verniz", "Block Lux", "Filme Dimension",
    "Filme Sarja", "Filme Emborrachado", "Filme Pneumático", "Adesivo Branco Brilho 0,08",
    "Adesivo Branco Brilho 0,10", "Adesivo Branco Fosco 0,10", "Adesivo Preto Brilho 0,08",
    "Adesivo Preto Fosco 0,10", "Adesivo Transparente Brilho 0,08",
    "Adesivo Transparente Jateado 0,08", "Adesivo Mascara Brilho 0,08",
    "Adesivo Aço Escovado 0,08"
]

prefixos_espessura = ("Geomembrana", "Geo", "Vitro", "Cristal", "Filme", "Adesivo", "Block Lux")

# ============================
# Interface Streamlit
# ============================
st.set_page_config(page_title="Calculadora Grupo Locomotiva", page_icon="📏", layout="centered")
st.title("Orçamento - Grupo Locomotiva")

# ===================================
# Botão para baixar PDF
# ===================================
if st.button("📄 Gerar Orçamento em PDF"):
    resumo_conf = calcular_valores_confeccionados(st.session_state['itens_confeccionados'], preco_m2) if st.session_state['itens_confeccionados'] else None
    resumo_bob  = calcular_valores_bobinas(st.session_state['bobinas_adicionadas'], preco_m2) if st.session_state['bobinas_adicionadas'] else None

    cliente = {"Razão ou Nome Fantasia": Cliente_nome, "CNPJ (opcional)": Cliente_CNPJ}
    vendedor = {"nome": vendedor_nome, "tel": vendedor_tel, "email": vendedor_email}

    # Certifique-se de que Observacao está definido antes de usar
    Observações = st.session_state.get("Observações", "")

    pdf_buffer = gerar_pdf_fpdf(cliente, vendedor,
                               st.session_state['itens_confeccionados'],
                               st.session_state['bobinas_adicionadas'],
                               resumo_conf, resumo_bob,
                               Observações, estado, aliquota_icms, aliquota_st)
    st.download_button(
        label="⬇️ Baixar Orçamento em PDF",
        data=pdf_buffer,
        file_name="orcamento.pdf",
        mime="application/pdf"
    )

# Data e hora
brasilia_tz = pytz.timezone("America/Sao_Paulo")
data_hora_brasilia = datetime.now(brasilia_tz).strftime("%d/%m/%Y %H:%M")
st.markdown(f"🕒 **Data e Hora:** {data_hora_brasilia}")

# Dados principais
produto = st.selectbox("Nome do Produto:", options=produtos_lista)
tipo_cliente = st.selectbox("Tipo do Cliente:", [" ","Consumidor Final", "Revenda"])
estado = st.selectbox("Estado do Cliente:", options=list(icms_por_estado.keys()))

# ICMS automático
aliquota_icms = icms_por_estado[estado]
st.info(f"🔹 Alíquota de ICMS para {estado}: **{aliquota_icms}% (já incluso no preço)**")

# ST aparece só se Encerado + Revenda
aliquota_st = None
if produto == "Encerado" and tipo_cliente == "Revenda":
    aliquota_st = st_por_estado.get(estado, 0)
    st.warning(f"⚠️ Este produto possui ST no estado {estado} aproximado a: **{aliquota_st}%**")

preco_m2 = st.number_input("Preço por m² ou metro linear (R$):", min_value=0.0, value=0.0, step=0.01)
tipo_produto = st.radio("Tipo do Produto:", ["Confeccionado", "Bobina"])

produto_exige_espessura = produto.startswith(prefixos_espessura)

# ============================
# Produtos Confeccionados
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
        for idx, item in enumerate(st.session_state['itens_confeccionados']):
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            with col1:
                st.markdown(f"**{item['produto']}**")
                st.markdown(f"🔹 {item['quantidade']}x {item['comprimento']}m x {item['largura']}m")
            with col2:
                cor = st.text_input("Cor:", value=item['cor'], key=f"cor_conf_{idx}")
                st.session_state['itens_confeccionados'][idx]['cor'] = cor
            with col4:
                if st.button("❌", key=f"remover_conf_{idx}"):
                    st.session_state['itens_confeccionados'].pop(idx)
                    st.experimental_rerun()

        m2_total, valor_bruto, valor_ipi, valor_final = calcular_valores_confeccionados(
            st.session_state['itens_confeccionados'], preco_m2
        )

        st.markdown("---")
        st.success("💰 **Resumo do Pedido - Confeccionado**")
        st.write(f"📏 Área Total: **{m2_total:.2f} m²**".replace(",", "X").replace(".", ",").replace("X", "."))
        st.write(f"💵 Valor Bruto: **R$ {valor_bruto:,.2f}**". replace(",", "X").replace(".", ",").replace("X", "."))
        st.write(f"🧾 IPI (3.25%): **R$ {valor_ipi:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))
        st.write(f"💰 Valor Final com IPI (3.25%): **R$ {valor_final:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))

        if aliquota_st:
            valor_com_st = valor_final * (1 + aliquota_st / 100)
            st.error(f"💰 Valor Aproximado com ST: **R$ {valor_com_st:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))
       
    if st.button("🧹 Limpar Itens"):
        st.session_state['itens_confeccionados'] = []
        st.experimental_rerun()

# ============================
# Produtos Bobina
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

    # Campo de espessura para bobinas (se aplicável)
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
        for idx, item in enumerate(st.session_state['bobinas_adicionadas']):
            col1, col2, col3, col4 = st.columns([4, 2, 2, 1])
            with col1:
                detalhes = (
                    f"🔹 {item['quantidade']}x {item['comprimento']}m"
                    f" | **Largura:** {item['largura']}m"
                )
                if 'espessura' in item:
                    detalhes += f" | **Esp:** {item['espessura']}mm"
                st.markdown(f"**{item['produto']}**")
                st.markdown(detalhes)
            with col2:
                cor = st.text_input("Cor:", value=item['cor'], key=f"cor_bob_{idx}")
                st.session_state['bobinas_adicionadas'][idx]['cor'] = cor
            with col4:
                if st.button("❌", key=f"remover_bob_{idx}"):
                    st.session_state['bobinas_adicionadas'].pop(idx)
                    st.experimental_rerun()

        m_total, valor_bruto, valor_ipi, valor_final = calcular_valores_bobinas(
            st.session_state['bobinas_adicionadas'], preco_m2
        )

        st.markdown("---")
        st.success("💰 **Resumo do Pedido - Bobinas**")
        st.write(f"📏 Total de Metros Lineares: **{m_total:.2f} m**".replace(",", "X").replace(".", ",").replace("X", "."))
        st.write(f"💵 Valor Bruto: **R$ {valor_bruto:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))
        st.write(f"🧾 IPI (9.75%): **R$ {valor_ipi:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))
        st.write(f"💰 Valor Final com IPI (9.75%): **R$ {valor_final:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))

        if st.button("🧹 Limpar Bobinas"):
            st.session_state['bobinas_adicionadas'] = []
            st.experimental_rerun()

# ============================
# Observações
# ============================
st.markdown("---")
st.subheader("🔎 Observações")
Observacao = st.text_input("Insira aqui alguma observação sobre o orçamento (opcional)")


# ============================
# Cliente
# ============================
st.markdown("---")
st.subheader("👤 Dados do Cliente")
col1, col2 = st.columns(2)
with col1:
    Cliente_nome = st.text_input("Razão ou Nome Fantasia")
    Cliente_CNPJ = st.text_input("CNPJ (opcional)")

# ============================
# Vendedor (opcional)
# ============================
st.markdown("---")
st.subheader("🗣️ Vendedor(a)")
col1, col2 = st.columns(2)
with col1:
    vendedor_nome = st.text_input("Nome")
    vendedor_tel = st.text_input("Telefone")
with col2:
    vendedor_email = st.text_input("E-mail")

st.markdown("🔒 Os dados acima são apenas para inclusão no orçamento (PDF ou impressão futura).")




