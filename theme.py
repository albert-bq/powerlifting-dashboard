# theme.py

# 🎨 Paleta personalizada
CUSTOM_COLORS = ["#C6D92D", "#00C2C7", "#6E6E6E", "#2B2B2B"]

# 🎨 Colores por categoría fija (ejemplo atletas M/F)
SEX_COLORS = {
    "M": "#00C2C7",   # Turquesa
    "F": "#C6D92D"    # Verde lima
}

# 🎨 Estilo global Plotly
DEFAULT_LAYOUT = dict(
    plot_bgcolor="#2B2B2B", 
    paper_bgcolor="#121212",
    font=dict(color="#EAEAEA"),
    title_font=dict(size=18, color="#C6D92D"),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(color="#EAEAEA")
    )
)
