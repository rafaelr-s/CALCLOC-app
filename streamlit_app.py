import streamlit as st
from datetime import datetime
import pytz
from fpdf import FPDF
from io import BytesIO

# ============================
# Função de formatação R$
# ============================
def _format_brl(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ============================
# Função para gerar PDF
# ============================


# ============================
# Tabelas ICMS e ST
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

# ============================
# Função utilitária rerun
# ============================
def _try_rerun():
    try:
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
    except Exception:
        pass

# ============================
# Funções de cálculo
# ============================
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
    produtos_isentos = ["Encerado", "Acrylic", "Agora"]
    if all(item['produto'] in produtos_isentos for item in itens):
        valor_ipi = 0
        valor_final = valor_bruto
    else:
        valor_ipi = valor_bruto * 0.0975
        valor_final = valor_bruto + valor_ipi
    return m_total, valor_bruto, valor_ipi, valor_final

# ============================
# Função para gerar PDF
# ============================
def gerar_pdf(cliente, vendedor, itens_confeccionados, itens_bobinas, resumo_conf, resumo_bob, observacao, tipo_cliente="", estado=""):
    pdf = FPDF('P','mm','A4')
    pdf.add_page()
    pdf.set_auto_page_break(auto=False)
    
    page_height = 297
    margin = 10
    usable_width = 210 - 2 * margin  # largura A4 menos margens
    current_height = margin

    def add_line(h):
        nonlocal current_height
        current_height += h
        if current_height > page_height - margin:
            pdf.add_page()
            current_height = margin

    # Cabeçalho
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, "Orçamento - Grupo Locomotiva", ln=True, align="C")
    add_line(8)
    pdf.ln(2)
    pdf.set_font("Arial", "", 9)
    brasilia_tz = pytz.timezone("America/Sao_Paulo")
    pdf.cell(0, 5, f"Data: {datetime.now(brasilia_tz).strftime('%d/%m/%Y %H:%M')}", ln=True)
    add_line(7)
    pdf.ln(1)

    # Cliente
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 5, "Cliente", ln=True)
    add_line(5)
    pdf.set_font("Arial", "", 8)
    pdf.multi_cell(usable_width, 5, f"Nome/Razão: {cliente.get('nome','')}")
    add_line(5)
    if cliente.get('cnpj','').strip():
        pdf.multi_cell(usable_width, 5, f"CNPJ/CPF: {cliente.get('cnpj','')}")
        add_line(5)
    if tipo_cliente.strip():
        pdf.multi_cell(usable_width, 5, f"Tipo de Cliente: {tipo_cliente}")
        add_line(5)
    if estado.strip():
        pdf.multi_cell(usable_width, 5, f"Estado: {estado}")
        add_line(5)
    pdf.ln(1)

    # Ajusta tamanho da fonte conforme quantidade de itens
    total_itens = len(itens_confeccionados) + len(itens_bobinas)
    font_size = 10
    if total_itens > 20:
        font_size = 7
    elif total_itens > 10:
        font_size = 8

    # Itens Confeccionados
    if itens_confeccionados:
        pdf.set_font("Arial", "B", font_size)
        pdf.cell(0, 5, "ITENS CONFECCIONADOS", ln=True)
        add_line(5)
        pdf.set_font("Arial", "", font_size-1)
        for item in itens_confeccionados:
            txt = f"{item['quantidade']}x {item['produto']} - {item['comprimento']}m x {item['largura']}m | Cor: {item.get('cor','')}"
            pdf.multi_cell(usable_width, 4, txt)
            add_line(4)
        if resumo_conf:
            m2_total, valor_bruto, valor_ipi, valor_final, valor_st, aliquota_st = resumo_conf
            pdf.ln(1)
            add_line(2)
            pdf.set_font("Arial", "B", font_size)
            pdf.cell(0, 5, "Resumo - Confeccionados", ln=True)
            add_line(5)
            pdf.set_font("Arial", "", font_size-1)
            pdf.cell(0, 4, f"Área Total: {m2_total:.2f} m²".replace(".", ","), ln=True)
            add_line(4)
            pdf.cell(0, 4, f"Valor Bruto: {_format_brl(valor_bruto)}", ln=True)
            add_line(4)
            pdf.cell(0, 4, f"IPI (3,25%): {_format_brl(valor_ipi)}", ln=True)
            add_line(4)
            if valor_st > 0:
                pdf.cell(0, 4, f"ST ({aliquota_st}%): {_format_brl(valor_st)}", ln=True)
                add_line(4)
            pdf.set_font("Arial", "B", font_size)
            pdf.cell(0, 5, f"Valor Final com IPI{(' + ST' if valor_st>0 else '')}: {_format_brl(valor_final)}", ln=True)
            add_line(5)
            pdf.ln(1)
            add_line(2)

    # Itens Bobinas
    if itens_bobinas:
        pdf.set_font("Arial", "B", font_size)
        pdf.cell(0, 5, "ITENS BOBINAS", ln=True)
        add_line(5)
        pdf.set_font("Arial", "", font_size-1)
        for item in itens_bobinas:
            txt = f"{item['quantidade']}x {item['produto']} - {item['comprimento']}m | Largura: {item['largura']}m | Cor: {item.get('cor','')}"
            if "espessura" in item:
                txt += f" | Esp: {item['espessura']}mm"
            pdf.multi_cell(usable_width, 4, txt)
            add_line(4)
        if resumo_bob:
            m_total, valor_bruto, valor_ipi, valor_final = resumo_bob
            pdf.ln(1)
            add_line(2)
            pdf.set_font("Arial", "B", font_size)
            pdf.cell(0, 5, "Resumo - Bobinas", ln=True)
            add_line(5)
            pdf.set_font("Arial", "", font_size-1)
            pdf.cell(0, 4, f"Total de Metros Lineares: {m_total:.2f} m".replace(".", ","), ln=True)
            add_line(4)
            pdf.cell(0, 4, f"Valor Bruto: {_format_brl(valor_bruto)}", ln=True)
            add_line(4)
            pdf.cell(0, 4, f"IPI: {_format_brl(valor_ipi)}", ln=True)
            add_line(4)
            pdf.set_font("Arial", "B", font_size)
            pdf.cell(0, 5, f"Valor Final: {_format_brl(valor_final)}", ln=True)
            add_line(5)
            pdf.ln(1)
            add_line(2)

    # Observações
    if observacao:
        pdf.set_font("Arial", "B", font_size)
        pdf.cell(0, 5, "OBSERVAÇÕES", ln=True)
        add_line(5)
        pdf.set_font("Arial", "", font_size-1)
        pdf.multi_cell(usable_width, 4, str(observacao))
        add_line(4*len(str(observacao).split("\n")))
        pdf.ln(1)
        add_line(2)

    # Vendedor
    if vendedor:
        pdf.set_font("Arial", "", font_size-1)
        pdf.multi_cell(usable_width, 4, f"Vendedor: {vendedor.get('nome','')} | Telefone: {vendedor.get('tel','')} | E-mail: {vendedor.get('email','')}")
        add_line(4)
        pdf.ln(1)
        add_line(2)

    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer
    
# ============================
# Inicialização de itens Confeccionados e Bobinas
# ============================
if "itens_confeccionados" not in st.session_state:
    st.session_state["itens_confeccionados"] = []
if "bobinas_adicionadas" not in st.session_state:
    st.session_state["bobinas_adicionadas"] = []

# ============================
# Interface Streamlit
# ============================
st.set_page_config(page_title="Calculadora Grupo Locomotiva", page_icon="📏", layout="centered")
st.title("Orçamento - Grupo Locomotiva")

# Data
brasilia_tz = pytz.timezone("America/Sao_Paulo")
data_hora_brasilia = datetime.now(brasilia_tz).strftime("%d/%m/%Y %H:%M")
st.markdown(f"🕒 **Data e Hora:** {data_hora_brasilia}")

# Cliente
st.subheader("👤 Dados do Cliente")
col1, col2 = st.columns(2)
with col1:
    Cliente_nome = st.text_input("Razão ou Nome Fantasia", value=st.session_state.get("Cliente_nome",""))
with col2:
    Cliente_CNPJ = st.text_input("CNPJ ou CPF (Opcional)", value=st.session_state.get("Cliente_CNPJ",""))

# Produtos
produtos_lista = [" ","Lonil de PVC","Lonil KP","Lonil Inflável KP","Encerado","Duramax",
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
                  "Adesivo Mascara Brilho 0,08","Adesivo Aço Escovado 0,08"]

prefixos_espessura = ("Geomembrana", "Geo", "Vitro", "Cristal", "Filme", "Adesivo", "Block Lux")

produto = st.selectbox("Nome do Produto:", options=produtos_lista)
tipo_produto = st.radio("Tipo do Produto:", ["Confeccionado", "Bobina"])
preco_m2 = st.number_input("Preço por m² ou metro linear (R$):", min_value=0.0, value=0.0, step=0.01)

tipo_cliente = st.selectbox("Tipo do Cliente:", [" ","Consumidor Final", "Revenda"])
estado = st.selectbox("Estado do Cliente:", options=list(icms_por_estado.keys()))

# ICMS e ST
aliquota_icms = icms_por_estado.get(estado, 7)
st.info(f"🔹 Alíquota de ICMS para {estado}: **{aliquota_icms}% (já incluso no preço)**")

if produto == "Encerado" and tipo_cliente == "Revenda":
    aliquota_st = st_por_estado.get(estado, 0)
    st.warning(f"⚠️ Este produto possui ST no estado {estado} aproximado a: **{aliquota_st}%**")
    
# ============================
# Confeccionado
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
        for idx, item in enumerate(st.session_state['itens_confeccionados'][:]):
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
                    _try_rerun()

    if st.button("🧹 Limpar Itens"):
        st.session_state['itens_confeccionados'] = []
        _try_rerun()

    # --- Só calcula e mostra resumo se tiver itens ---
    if st.session_state['itens_confeccionados']:
        m2_total, valor_bruto, valor_ipi, valor_final, valor_st, aliquota_st = calcular_valores_confeccionados(
            st.session_state['itens_confeccionados'], preco_m2, tipo_cliente, estado
        )

        st.markdown("---")
        st.success("💰 **Resumo do Pedido - Confeccionado**")
        st.write(f"📏 Área Total: **{m2_total:.2f} m²**".replace(".", ","))
        st.write(f"💵 Valor Bruto: **{_format_brl(valor_bruto)}**")
        st.write(f"🧾 IPI (3,25%): **{_format_brl(valor_ipi)}**")
        if valor_st > 0:
            st.write(f"📌 ST ({aliquota_st}%): **{_format_brl(valor_st)}**")
        st.write(f"💰 Valor Final Aproximado com IPI{(' + ST' if valor_st>0 else '')}: **{_format_brl(valor_final)}**")

# ============================
# Bobina
# ============================
if tipo_produto == "Bobina":
    st.subheader("➕ Adicionar Item Bobina")
    col1, col2, col3 = st.columns(3)
    with col1:
        comprimento_bob = st.number_input("Comprimento (m):", min_value=0.01, value=50.0, step=0.1, key="comp_bob")
    with col2:
        largura_bobina = st.number_input("Largura da Bobina (m):", min_value=0.01, value=1.4, step=0.01, key="larg_bob")
    with col3:
        quantidade_bob = st.number_input("Quantidade:", min_value=0, value=0, step=1, key="qtd_bob")

    espessura_bobina = None
    if produto.startswith(prefixos_espessura):
        espessura_bobina = st.number_input("Espessura da Bobina (mm):", min_value=0.01, value=0.10, step=0.01, key="esp_bob")

    if st.button("➕ Adicionar Bobina"):
        item_bobina = {
            'produto': produto,
            'comprimento': comprimento_bob,
            'largura': largura_bobina,
            'quantidade': quantidade_bob,
            'cor': ""
        }
        if espessura_bobina:
            item_bobina['espessura'] = espessura_bobina
        st.session_state['bobinas_adicionadas'].append(item_bobina)

    if st.session_state['bobinas_adicionadas']:
        st.subheader("📋 Bobinas Adicionadas")
        for idx, item in enumerate(st.session_state['bobinas_adicionadas'][:]):
            col1, col2, col3, col4 = st.columns([4,2,1,1])
            with col1:
                detalhes = f"🔹 {item['quantidade']}x {item['comprimento']}m | Largura: {item['largura']}m"
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
                    _try_rerun()

    if st.button("🧹 Limpar Bobinas"):
        st.session_state['bobinas_adicionadas'] = []
        _try_rerun()

    # --- Resumo (sem ST para bobina) ---
    if st.session_state['bobinas_adicionadas']:
        m_total, valor_bruto, valor_ipi, valor_final = calcular_valores_bobinas(
            st.session_state['bobinas_adicionadas'], preco_m2
        )

        st.markdown("---")
        st.success("💰 **Resumo do Pedido - Bobinas**")
        st.write(f"📏 Total de Metros Lineares: **{m_total:.2f} m**".replace(".", ","))
        st.write(f"💵 Valor Bruto: **{_format_brl(valor_bruto)}**")
        st.write(f"🧾 IPI (9,75%): **{_format_brl(valor_ipi)}**")
        st.write(f"💰 Valor Final com IPI (9,75%): **{_format_brl(valor_final)}**")

# ============================
# Observações
# ============================
st.subheader("🔎 Observações")
Observacao = st.text_area("Insira aqui alguma observação sobre o orçamento (opcional)")

# ============================
# Campos Vendedor
# ============================
st.subheader("🗣️ Vendedor(a)")
col1, col2 = st.columns(2)
with col1:
    vendedor_nome = st.text_input("Nome Vendedor")
    vendedor_tel = st.text_input("Telefone")
with col2:
    vendedor_email = st.text_input("E-mail")

# ============================
# Botão para gerar PDF
# ============================
if st.button("📄 Gerar Orçamento em PDF"):
    cliente = {"nome": Cliente_nome, "cnpj": Cliente_CNPJ}
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
        st.text_area("Observações"),
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
