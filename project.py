#imported libraries
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import altair as alt
from fpdf import FPDF
from io import BytesIO

#pozadavky: tlacitko na export v pdf, anglictina vs cestina
#######################
# Page configuration
st.set_page_config(
    page_title="AWS Cost Optimization Report",
    page_icon="🏂",
    layout="wide",
    initial_sidebar_state="expanded")

st.title("AWS Cost Optimization Report")

######################
# Dashboard style
def local_css(file_name):
    with open(file_name) as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# Inject custom CSS
local_css("styles.css")

#######################
# Load data
df = pd.read_csv('rfe-cost-opt-hub-export-00001.csv')
df_reshaped = df[["account_id", "action_type", "currency_code", "current_resource_summary", "current_resource_type", "estimated_monthly_cost_before_discount",
                 "estimated_monthly_savings_before_discount", "estimated_savings_percentage_before_discount", "recommended_resource_summary", "region", 
                 "resource_arn"]]
df_reshaped["estimated_monthly_cost_after_optimalization"] = round((df["estimated_monthly_cost_before_discount"] - df["estimated_monthly_savings_before_discount"]).astype(float), 3)
df_reshaped["estimated_savings_percentage_before_discount"] = (df["estimated_savings_percentage_before_discount"]/100).astype(float)
df_reshaped["resource_arn"] = df["resource_arn"].str.split("/").str[1]

#######################
# Sidebar function 
def sidebar(df_reshaped, column_name, slicer_name, placeholder_name):
    #Get unique accounts types
    df_values = df_reshaped[column_name].unique().tolist()
    df_values_all = ["All selected"] + df_values

    selected_values = st.multiselect(
        slicer_name, 
        options = df_values_all, 
        default = ["All selected"],
        placeholder= f"Select {placeholder_name} ...", 

    )

    #filter main df
    if "All selected" in selected_values or not selected_values:
        df_reshaped = df_reshaped
        
    else:
        df_reshaped = df_reshaped[df_reshaped[column_name].isin(selected_values)]

    return df_reshaped
        


with st.sidebar:

########################
    #title of the slicer bar
    st.title('Report slicers')

    #account_id slicer
    df_selected_account = sidebar(df_reshaped, "account_id", "Account ID", "account id")

    #account type slicer
    df_selected_account = sidebar(df_selected_account, "action_type", "Action types", "action type")

    #region slicer
    df_selected_account = sidebar(df_selected_account, "region", "Region", "region")
    

#################   
# Dashboard Main Panel
row1 = st.columns((1, 1, 1), gap='medium')



with row1[0]:

    cost_before = df_selected_account["estimated_monthly_cost_before_discount"].sum()
    formatted_cost_before = f"${cost_before:,.2f}"  # Adds $ and comma formatting, no decimals
    st.metric("Before optimization", formatted_cost_before)

with row1[1]:
    cost_after = df_selected_account["estimated_monthly_cost_after_optimalization"].sum()
    formated_cost_after = f"${cost_after:,.2f}"
    st.metric("After optimalization", formated_cost_after)

with row1[2]:
    savings = df_selected_account["estimated_monthly_savings_before_discount"].sum()
    formated_savings = f"${savings:,.2f}"
    percent_savings = (savings / cost_before) * 100 if cost_before else 0
    formatted_percent = f"{percent_savings:.2f}%"
    st.metric("Savings", value = formated_savings, delta = formatted_percent)

##########
# Table
row_height = 36
table_height = (1 + len(df_selected_account)) * row_height

with st.container():
    st.markdown('Account information')

    st.dataframe(df_selected_account,
                 column_order=(
                    "account_id", 
                    "estimated_monthly_cost_before_discount", 
                    "estimated_monthly_cost_after_optimalization", 
                    "estimated_monthly_savings_before_discount", 
                    "estimated_savings_percentage_before_discount", 
                    "action_type",
                    "current_resource_summary",
                    "current_resource_type",
                    "recommended_resource_summary",
                    "resource_arn"
                ),
                 hide_index=True,
                 width=None,
                 height=table_height,
                 column_config={
                    "account_id": st.column_config.TextColumn(
                        "Account id",
                    ),
                    "estimated_monthly_cost_before_discount": st.column_config.NumberColumn(
                        "Cost before",
                        format = "$%.2f"
                    ),
                    "estimated_monthly_cost_after_optimalization": st.column_config.NumberColumn(
                        "Cost after",
                        format = "$%.2f"
                    ),
                    "estimated_monthly_savings_before_discount": st.column_config.NumberColumn(
                        "Savings",
                        format = "$%.2f"
                    ),
                    "estimated_savings_percentage_before_discount":  st.column_config.NumberColumn(
                        "% Saved",
                        format = "percent",
                    ),
                    "action_type": st.column_config.TextColumn(
                        "Action type"
                    ),
                    "current_resource_summary":st.column_config.TextColumn(
                        "Current resource"
                    ),
                    "current_resource_type":st.column_config.TextColumn(
                        "Current resource type"
                    ),
                    "recommended_resource_summary": st.column_config.TextColumn(
                        "Recommended resource"
                    ),
                    "resource_arn":st.column_config.TextColumn(
                        "Resource ARN"
                    )

                    }
                 )

#rename the headers for pdf
df_selected_account.rename(columns={
    "account_id": "Account ID", 
    "action_type": "Action type",
    "currency_code": "Currency", 
    "current_resource_summary": "Current resource", 
    "current_resource_type": "Current resource type", 
    "estimated_monthly_cost_before_discount": "Cost before",
    "estimated_monthly_cost_after_optimalization": "Cost after",
    "estimated_monthly_savings_before_discount": "Savings", 
    "estimated_savings_percentage_before_discount": "% Saved", 
    "recommended_resource_summary": "Recommended resource", 
    "region": "Region", 
    "resource_arn": "Resource ARN"
    }, inplace=True)  

#select columns in pdf
df_pdf = df_selected_account[[
    "Account ID", 
    "Cost before",
    "Cost after",
    "Savings", 
    "% Saved", 
    "Action type",
    "Current resource", 
    "Current resource type", 
    "Recommended resource", 
    "Resource ARN"
]]

#format columns
df_pdf["% Saved"] = df_pdf['% Saved'].apply(lambda x: f"{x:.0%}")
df_pdf["Cost before"] = df_pdf["Cost before"].apply(lambda x: f"${x:,.2f}")
df_pdf["Cost after"] = df_pdf["Cost after"].apply(lambda x: f"${x:,.2f}")
df_pdf["Savings"] = df_pdf["Savings"].apply(lambda x: f"${x:,.2f}")


####pdf button
# PDF generation function
class PDF(FPDF):
    def add_table(self, df):
        self.set_font("Arial", "B", 8)
        row_height = 8

        # Calculate dynamic column widths based on header text
        col_widths = []
        padding = 1  # Padding on each side

        for col in df.columns:
            header_width = self.get_string_width(str(col)) + 2 * padding
            max_cell_width = header_width

            # Optionally, check the data for wider content
   
            for val in df[col].astype(str):
                val_width = self.get_string_width(val) + 2 * padding
                if val_width > max_cell_width:
                    max_cell_width = val_width

            col_widths.append(max_cell_width)

        # Draw header row
        self.set_font("Arial", "B", 8)
        for i, col in enumerate(df.columns):
            self.cell(col_widths[i], row_height, str(col), border=1)
        self.ln(row_height)

        # Draw data rows
        self.set_font("Arial", size=8)
        for _, row in df.iterrows():
            for i, item in enumerate(row):
                self.cell(col_widths[i], row_height, str(item), border=1)
            self.ln(row_height)

    def add_summary(self, cost_before, cost_after, savings):
        self.set_font("Arial", size=10)
        self.cell(200, 10, txt=f"Cost before: {cost_before}", ln=True)
        self.cell(200, 10, txt=f"Cost after: {cost_after}", ln=True)
        self.cell(200, 10, txt=f"Savings: {savings}", ln=True)


###
def generate_pdf_with_table(df, cost_before, cost_after, savings, title = "AWS Cost Optimization Report"):
    pdf = PDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
     # Title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, title, ln=True, align="C")

    # Space after title
    pdf.ln(10)
    pdf.add_summary(cost_before, cost_after, savings)
    pdf.add_table(df)

    pdf_bytes = pdf.output(dest='S').encode('latin1')  # 'S' returns as string
    pdf_buffer = BytesIO(pdf_bytes)
    return pdf_buffer


pdf_file = generate_pdf_with_table(df_pdf, formatted_cost_before, formated_cost_after, formated_savings)
st.download_button(
        label= "Download PDF",
        data=pdf_file,
        file_name="AWS Cost Optimization Report.pdf",
        mime="application/pdf"
)


