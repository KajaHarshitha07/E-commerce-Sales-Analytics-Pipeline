import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="Olist E-Commerce Analytics Dashboard",
    page_icon="📦",
    layout="wide"
)

st.title("📦 Olist E-Commerce Analytics Dashboard")
st.markdown("**Dataset:** Brazilian E-Commerce (Olist) | 96K+ delivered orders")
st.markdown("---")

@st.cache_data
def load_data():
    df = pd.read_csv('master_table.csv')
    rfm = pd.read_csv('rfm_segments.csv')

    df['payment_value'] = pd.to_numeric(df.get('payment_value', 0), errors='coerce').fillna(0.0)
    df['delivery_delay_days'] = pd.to_numeric(df.get('delivery_delay_days', 0), errors='coerce')
    df['review_score'] = pd.to_numeric(df.get('review_score', 0), errors='coerce').fillna(0)
    df['is_late'] = pd.to_numeric(df.get('is_late', 0), errors='coerce').fillna(0).astype(int)
    df['customer_state'] = df.get('customer_state', '').astype(str).fillna('Unknown')
    if 'order_month' not in df.columns:
        if 'order_purchase_timestamp' in df.columns:
            df['order_month'] = pd.to_datetime(df['order_purchase_timestamp'], errors='coerce').dt.to_period('M').astype(str)
        else:
            df['order_month'] = ''

    rfm['Segment_Name'] = rfm.get('Segment_Name', '').astype(str).fillna('Unknown')

    return df, rfm


def format_currency(value: float) -> str:
    if pd.isna(value):
        return 'R$0'
    return f"R${value:,.0f}"


def display_html_table(df: pd.DataFrame, max_rows: int = 200) -> None:
    html = df.head(max_rows).to_html(index=False, border=0)
    st.markdown(html, unsafe_allow_html=True)

try:
    df, rfm = load_data()
except FileNotFoundError:
    st.error("CSV files not found. Make sure master_table.csv and rfm_segments.csv are in the same folder as app.py")
    st.stop()

# ── KPI Cards ──────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Revenue",    format_currency(df['payment_value'].sum()))
col2.metric("Total Orders",     f"{df['order_id'].nunique():,}")
col3.metric("Avg Order Value",  format_currency(df['payment_value'].mean()))
col4.metric("Late Deliveries",  f"{df['is_late'].mean()*100:.1f}%")

st.markdown("---")

# ── Row 1: Revenue Trend + Top Categories ──────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Monthly Revenue Trend")
    monthly = (
        df.groupby('order_month')['payment_value']
        .sum()
        .reset_index()
        .sort_values('order_month')
    )
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.plot(monthly['order_month'], monthly['payment_value'], color='#378ADD', linewidth=2, marker='o', markersize=4)
    ax.fill_between(monthly['order_month'], monthly['payment_value'], alpha=0.1, color='#378ADD')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'R${x/1000:.0f}K'))
    plt.xticks(rotation=45, fontsize=8)
    ax.set_xlabel('')
    ax.spines[['top','right']].set_visible(False)
    st.pyplot(fig)

with col_right:
    st.subheader("Top 10 Categories by Revenue")
    top_cat = (
        df.groupby('product_category_name_english')['payment_value']
        .sum()
        .nlargest(10)
        .sort_values()
    )
    fig2, ax2 = plt.subplots(figsize=(7, 3.5))
    bars = ax2.barh(top_cat.index, top_cat.values, color='#534AB7')
    ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'R${x/1000:.0f}K'))
    ax2.spines[['top','right']].set_visible(False)
    st.pyplot(fig2)

st.markdown("---")

# ── Row 2: Customer Segments + Delivery by State ───────────
col_left2, col_right2 = st.columns(2)

with col_left2:
    st.subheader("Customer Segments (RFM)")
    seg = rfm['Segment_Name'].value_counts()
    colors_map = {
        'Champions': '#378ADD',
        'Loyal Customers': '#639922',
        'At Risk': '#BA7517',
        'Lost Customers': '#E24B4A',
        'Potential': '#7F77DD'
    }
    colors_list = [colors_map.get(s, '#888780') for s in seg.index]
    fig3, ax3 = plt.subplots(figsize=(6, 3.5))
    ax3.pie(seg.values, labels=seg.index, autopct='%1.0f%%',
            colors=colors_list, startangle=90,
            textprops={'fontsize': 9})
    st.pyplot(fig3)

with col_right2:
    st.subheader("Late Delivery Rate by State (Top 10)")
    state_delay = (
        df.groupby('customer_state')
        .agg(late_pct=('is_late', lambda x: x.mean() * 100))
        .sort_values('late_pct', ascending=False)
        .head(10)
        .sort_values('late_pct')
    )
    fig4, ax4 = plt.subplots(figsize=(7, 3.5))
    ax4.barh(state_delay.index, state_delay['late_pct'], color='#E24B4A')
    ax4.set_xlabel('Late Delivery %')
    ax4.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:.0f}%'))
    ax4.spines[['top','right']].set_visible(False)
    st.pyplot(fig4)

st.markdown("---")

# ── Filters + Data Explorer ────────────────────────────────
st.subheader("Explore the Data")

fcol1, fcol2 = st.columns(2)
with fcol1:
    state_filter = st.selectbox(
        "Filter by customer state",
        ['All'] + sorted(df['customer_state'].dropna().unique().tolist())
    )
with fcol2:
    delivery_filter = st.selectbox(
        "Delivery status",
        ['All', 'On Time', 'Late']
    )

filtered = df.copy()
if state_filter != 'All':
    filtered = filtered[filtered['customer_state'] == state_filter]
if delivery_filter == 'Late':
    filtered = filtered[filtered['is_late'] == 1]
elif delivery_filter == 'On Time':
    filtered = filtered[filtered['is_late'] == 0]

if filtered.empty:
    st.info("No rows match the current filters.")
else:
    display_html_table(filtered[[
        'order_id', 'customer_state', 'payment_value',
        'delivery_delay_days', 'review_score', 'is_late',
        'product_category_name_english'
    ]])

st.caption(f"Showing {min(200, len(filtered))} of {len(filtered):,} filtered rows")

st.markdown("---")
st.markdown(
    "📊 **Insights:**\n"
    "- Revenue has a clear seasonal pattern, peaking in December.\n"
    "- Top categories include electronics and home appliances.\n"
    "- Majority of customers are 'Loyal Customers' and 'Champions'.\n"
    "- Some states have significantly higher late delivery rates."
)
