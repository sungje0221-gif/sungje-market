import pandas as pd


POSITIVE_COLOR = "#4DA3FF"
NEGATIVE_COLOR = "#FF6474"
NEUTRAL_COLOR = "#A9B4C4"


def color_signed(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    if pd.isna(number):
        return ""
    if number > 0:
        return f"color: {POSITIVE_COLOR}; font-weight: 750"
    if number < 0:
        return f"color: {NEGATIVE_COLOR}; font-weight: 750"
    return f"color: {NEUTRAL_COLOR}; font-weight: 650"


def style_signed_columns(df, columns):
    styler = df.style
    for column in columns:
        if column in df.columns:
            styler = styler.map(color_signed, subset=[column])
    return styler
