import streamlit as st
from datetime import datetime
import pytz

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
    "SP": 13.87, "RJ": 27.02, "MG": 22.26, "ES": 0.0, "PR": 22.26, "RS": 19.97, "SC": 0.0,
    "BA": 29.21, "PE": 29.21, "CE": 19.02, "RN": 0.0, "PB": 29.21, "SE": 0.0, "AL": 29.21,
    "DF": 29.21, "GO": 0.0, "MS": 0.0, "MT": 22.01,
    "AM": 29.21, "PA": 26.79, "RO": 0.0, "RR": 26.79, "AC": 26.79, "AP": 29.21, "MA": 29.21, "PI": 22.51, "TO": 0.0
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
    st.warning(f"⚠️ Este produto possui ST no estado {estado}: **{aliquota_st}%**")

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
        st.success("💰 **Resumo do Confeccionado**")
        st.write(f"📏 Área Total: **{m2_total:.2f} m²**".replace(",", "X").replace(".", ",").replace("X", "."))
        st.write(f"💵 Valor Bruto: **R$ {valor_bruto:,.2f}**". replace(",", "X").replace(".", ",").replace("X", "."))
        st.write(f"🧾 IPI (3.25%): **R$ {valor_ipi:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))
        st.write(f"💰 Valor Final: **R$ {valor_final:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))

        if aliquota_st:
            valor_com_st = valor_final * (1 + aliquota_st / 100)
            st.error(f"💰 Valor Final com ST: **R$ {valor_com_st:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))
       
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
        st.success("💰 **Resumo das Bobinas**")
        st.write(f"📏 Total de Metros Lineares: **{m_total:.2f} m**".replace(",", "X").replace(".", ",").replace("X", "."))
        st.write(f"💵 Valor Bruto: **R$ {valor_bruto:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))
        st.write(f"🧾 IPI (9.75%): **R$ {valor_ipi:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))
        st.write(f"💰 Valor Final: **R$ {valor_final:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))

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
