import streamlit as st
import pandas as pd
from io import BytesIO

st.title("📊 Conciliación Bancaria")

# =========================
# FUNCIONES
# =========================

def transformar_fechas(df_extracto, df_datafono):
    df_datafono["fecha"] = pd.to_datetime(df_datafono["fecha"]).dt.date
    df_extracto["Fecha"] = pd.to_datetime(df_extracto["Fecha"]).dt.date
    return df_extracto, df_datafono


def procesar_datafono(df_datafono):
    df2 = df_datafono[df_datafono["tipoTransaccion"] != "QR"].copy()

    df2["fecha_modificada"] = df2["fecha"]

    mask_visa = df2["franquicia"].isin(["VISA", "VISA DEBIT"])
    df2.loc[mask_visa, "fecha_modificada"] = df2["fecha"] + pd.Timedelta(days=1)

    return df2


def cruzar_datafono_extracto(df_extracto, df_datafono):

    df2_datafono = procesar_datafono(df_datafono)

    df2_extracto = df_extracto[
        df_extracto["Descripción"] == "DEP.COMERCIANTES 000010969954"
    ].copy()

    for fecha in df2_extracto["Fecha"].unique():

        if fecha in df2_datafono["fecha_modificada"].unique():

            valor_extracto = df2_extracto[df2_extracto["Fecha"] == fecha]["Valor"].sum()
            valor_datafono = df2_datafono[df2_datafono["fecha_modificada"] == fecha]["montoTotal"].sum()

            estado = "Cruza" if valor_extracto == valor_datafono else "No Cruza"

            df_datafono.loc[df_datafono["fecha"] == fecha, "Novedad"] = estado

            df_extracto.loc[
                (df_extracto["Fecha"] == fecha) &
                (df_extracto["Descripción"] == "DEP.COMERCIANTES 000010969954"),
                "Novedad"
            ] = estado

        else:
            df_extracto.loc[
                (df_extracto["Fecha"] == fecha) &
                (df_extracto["Descripción"] == "DEP.COMERCIANTES 000010969954"),
                "Novedad"
            ] = "No Cruza"

    # QR
    df_datafono.loc[df_datafono["tipoTransaccion"] == "QR", "Novedad"] = "No Cruza"

    return df_datafono, df_extracto


def procesar_pse(df_pse):

    cols = ["FECHA_PAGO", "FECHA_COMPENSACION", "FECHA_TRANSACCION"]

    for col in cols:
        df_pse[col] = df_pse[col].str.replace(",000000000", "")
        df_pse[col] = pd.to_datetime(df_pse[col], format="%d/%m/%y %I:%M:%S %p").dt.date

    df_pse["NUMERO_APROBACION_CUS"] = df_pse["NUMERO_APROBACION_CUS"].astype(str)

    df2 = df_pse[df_pse["MEDIO_PAGO_DS"] == "TC"].copy()

    df2["fecha_modificada"] = df2["FECHA_PAGO"] + pd.Timedelta(days=1)

    df2 = df2.drop_duplicates(
        subset=["NUMERO_APROBACION_CUS", "TIPO_DOCUMENTO", "NUMERO_DOCUMENTO"]
    )

    return df2


def cruzar_pse_extracto(df_extracto, df_pse):

    df2_extracto = df_extracto[
        df_extracto["Descripción"] == "DEP.COMERCIANTES 000018082388"
    ].copy()

    for fecha in df2_extracto["Fecha"].unique():

        if fecha in df_pse["fecha_modificada"].unique():

            valor_extracto = df2_extracto[df2_extracto["Fecha"] == fecha]["Valor"].sum()
            valor_pse = df_pse[df_pse["fecha_modificada"] == fecha]["VALOR_TOTAL"].sum()

            estado = "Cruza" if valor_extracto == valor_pse else "No Cruza"

            df_pse.loc[df_pse["fecha_modificada"] == fecha, "Novedad"] = estado

            df_extracto.loc[
                (df_extracto["Fecha"] == fecha) &
                (df_extracto["Descripción"] == "DEP.COMERCIANTES 000018082388"),
                "Novedad"
            ] = estado

        else:
            df_extracto.loc[
                (df_extracto["Fecha"] == fecha) &
                (df_extracto["Descripción"] == "DEP.COMERCIANTES 000018082388"),
                "Novedad"
            ] = "No Cruza"

    df_pse["Novedad"] = df_pse["Novedad"].fillna("No Cruza")

    return df_pse, df_extracto


# =========================
# FUNCIONES EXCEL (OPENPYXL)
# =========================

def convertir_a_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Datos')
    return output.getvalue()


def convertir_todo_a_excel(df1, df2, df3):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df1.to_excel(writer, index=False, sheet_name='Extracto')
        df2.to_excel(writer, index=False, sheet_name='Datafono')
        df3.to_excel(writer, index=False, sheet_name='PSE')
    return output.getvalue()


# =========================
# UI
# =========================

df_extracto_file = st.file_uploader("📂 Extracto", type="xlsx")
df_datafono_file = st.file_uploader("📂 Datafono", type="xlsx")
df_pse_file = st.file_uploader("📂 PSE", type="xlsx")

if st.button("🚀 Procesar"):

    if df_extracto_file and df_datafono_file and df_pse_file:

        df_extracto = pd.read_excel(df_extracto_file)
        df_datafono = pd.read_excel(df_datafono_file)
        df_pse = pd.read_excel(df_pse_file)

        # Transformaciones
        df_extracto, df_datafono = transformar_fechas(df_extracto, df_datafono)

        # Cruces
        df_datafono, df_extracto = cruzar_datafono_extracto(df_extracto, df_datafono)

        df2_pse = procesar_pse(df_pse)
        df2_pse, df_extracto = cruzar_pse_extracto(df_extracto, df2_pse)

        st.success("✅ Proceso terminado")

        st.subheader("Extracto")
        st.dataframe(df_extracto)

        st.subheader("Datafono")
        st.dataframe(df_datafono)

        st.subheader("PSE")
        st.dataframe(df2_pse)

        # =========================
        # DESCARGAS EN EXCEL
        # =========================

        st.download_button(
            "⬇️ Descargar Extracto",
            convertir_a_excel(df_extracto),
            "extracto.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.download_button(
            "⬇️ Descargar Datafono",
            convertir_a_excel(df_datafono),
            "datafono.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.download_button(
            "⬇️ Descargar PSE",
            convertir_a_excel(df2_pse),
            "pse.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.download_button(
            "⬇️ Descargar Todo en un solo Excel",
            convertir_todo_a_excel(df_extracto, df_datafono, df2_pse),
            "conciliacion.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:
        st.warning("⚠️ Carga todos los archivos")