import streamlit as st
import pandas as pd
import zipfile
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
import matplotlib.pyplot as plt
import folium
import json
import requests
from folium.plugins import FastMarkerCluster
from streamlit_folium import folium_static

# Reading and Cleaning Data
@st.cache_data
def load_data():
    # Read zip and extract
    # zip_file = zipfile.ZipFile('archive.zip', 'r')
    # zip_file.extractall('datasets/')
    # zip_file.close()

    # Read the datasets
    df_customer = pd.read_csv('../datasets/olist_customers_dataset.csv')
    df_geolocation = pd.read_csv('../datasets/olist_geolocation_dataset.csv')
    df_order_items = pd.read_csv('../datasets/olist_order_items_dataset.csv')
    df_order_payments = pd.read_csv('../datasets/olist_order_payments_dataset.csv')
    df_order_reviews = pd.read_csv('../datasets/olist_order_reviews_dataset.csv')
    df_orders_dataset = pd.read_csv('../datasets/olist_orders_dataset.csv')
    df_products_dataset = pd.read_csv('../datasets/olist_products_dataset.csv')
    df_sellers_dataset = pd.read_csv('../datasets/olist_sellers_dataset.csv')
    df_product_name = pd.read_csv('../datasets/product_category_name_translation.csv')

    # Data Cleaning
    df_geolocation.drop_duplicates(inplace=True)
    df_order_reviews["review_comment_message"].fillna("No Message", inplace=True)
    df_order_reviews["review_comment_title"].fillna("No Title", inplace=True)
    df_order_items['shipping_limit_date'] = pd.to_datetime(df_order_items['shipping_limit_date'])
    orders_column = [
        'order_delivered_carrier_date', 
        'order_delivered_customer_date', 
        'order_estimated_delivery_date', 
        'order_purchase_timestamp', 
        'order_approved_at'
    ]

    for column in orders_column:
        df_orders_dataset[column] = pd.to_datetime(df_orders_dataset[column])
    col123 = ['review_creation_date', 'review_answer_timestamp']
    df_order_reviews[col123] = df_order_reviews[col123].apply(pd.to_datetime)

    # Merging Datasets
    df_train = df_orders_dataset.merge(df_order_items, on='order_id', how='left')
    df_train = df_train.merge(df_order_payments, on='order_id', how='outer', validate='m:m')
    df_train = df_train.merge(df_order_reviews, on='order_id', how='outer')
    df_train = df_train.merge(df_products_dataset, on='product_id', how='outer')
    df_train = df_train.merge(df_customer, on='customer_id', how='outer')
    df_train = df_train.merge(df_sellers_dataset, on='seller_id', how='outer')

    df_train['day_of_week_name'] = df_train['order_purchase_timestamp'].dt.strftime('%A')
    df_train['hour'] = df_train['order_purchase_timestamp'].dt.hour
    df_train['year'] = df_train['order_purchase_timestamp'].dt.year
    df_train['delivery_time'] = (df_train['order_delivered_customer_date'] - df_train['order_purchase_timestamp']).dt.days
    df_train['day_month_year'] = df_train['order_purchase_timestamp'].dt.strftime('%Y-%m-%d')

    return df_train, df_order_payments, df_geolocation

df_train, df_order_payments, df_geolocation = load_data()

# Streamlit Sidebar
st.sidebar.title("Olist E-commerce Analysis")
st.sidebar.header("Select Visualization")
visualization_option = st.sidebar.selectbox(
    "Choose a visualization", 
    ["Payment Method Distribution", "Peak Shopping Time", "Average Delivery Time", "Geospatial Analysis"]
)

# 1. Payment Method Distribution
if visualization_option == "Payment Method Distribution":
    st.title("Percentage of Each Payment Method Used")

    # Calculate payment percentages
    payment_counts = df_order_payments['payment_type'].value_counts()
    payment_percentages = (payment_counts / payment_counts.sum()) * 100

    # Plotly bar chart
    fig = px.bar(
        x=payment_percentages.index,
        y=payment_percentages.values,
        labels={'x': 'Payment Method', 'y': 'Percentage (%)'},
        title='Percentage of Each Payment Method Used',
        color=payment_percentages.index,
        color_continuous_scale='Viridis'
    )
    st.plotly_chart(fig)

# 2. Peak Shopping Time
elif visualization_option == "Peak Shopping Time":
    st.title("Peak Shopping Time (Day of Week & Hour)")

    # Create a count table by grouping the data by day of the week and hour
    g5 = df_train.groupby(['day_of_week_name', 'hour']).size().reset_index(name='count')

    # Create a pivot table for heatmap
    tabela_pivot = g5.pivot(index='day_of_week_name', columns='hour', values='count')
    g6 = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    tabela_pivot = tabela_pivot.reindex(g6)

    # Create heatmap with Seaborn
    plt.figure(figsize=(20, 8))
    ax = sns.heatmap(tabela_pivot, cmap="Blues", annot=True, fmt='d', cbar=True)
    ax.set_xlabel('Hour') 
    ax.set_ylabel('Day of Week')
    ax.set_title('Total orders by day and hour')  
    plt.xticks(ticks=range(24), labels=[str(i) for i in range(24)])

    st.pyplot(plt)

# 3. Average Delivery Time
elif visualization_option == "Average Delivery Time":
    st.title("Average Delivery Time Over Time")

    # Group by day_month_year and aggregate data
    df_grouped = df_train.groupby('day_month_year').agg(
        total_orders=('order_id', 'count'),
        avg_delivery_time=('delivery_time', 'mean')
    ).reset_index()

    # Filter data within a specific date range
    start_date = '2017-06-01'
    end_date = '2018-06-30'
    filtered_df = df_grouped[(df_grouped['day_month_year'] >= start_date) & (df_grouped['day_month_year'] <= end_date)]

    # Calculate yearly average
    yearly_avg = filtered_df['avg_delivery_time'].mean()

    # Plot with Plotly
    fig = px.line(
        filtered_df,
        x='day_month_year',
        y='avg_delivery_time',
        title='Average Delivery Time Over Time',
        labels={'day_month_year': 'Date', 'avg_delivery_time': 'Days'},
        template='plotly_white'
    )
    fig.add_trace(
        go.Scatter(
            x=filtered_df['day_month_year'],
            y=[yearly_avg] * len(filtered_df),
            mode='lines',
            line=dict(dash='dash', color='red'),
            name='Yearly average'
        )
    )
    st.plotly_chart(fig)

# 4. Geospatial Analysis
elif visualization_option == "Geospatial Analysis":
    # Judul Aplikasi Streamlit
    st.title("Analisis Geolokasi di Brasil")

    # Menggunakan API untuk mengambil data wilayah
    r = requests.get('https://servicodados.ibge.gov.br/api/v1/localidades/mesorregioes')
    content = [c['UF'] for c in json.loads(r.text)]
    br_info = pd.DataFrame(content)
    br_info['nome_regiao'] = br_info['regiao'].apply(lambda x: x['nome'])
    br_info.drop(columns=['regiao'], inplace=True)
    br_info.drop_duplicates(inplace=True)

    # Filtering geolocations di luar peta Brasil
    geo_prep = df_geolocation[(df_geolocation.geolocation_lat <= 5.27438888) & 
                            (df_geolocation.geolocation_lng >= -73.98283055) & 
                            (df_geolocation.geolocation_lat >= -33.75116944) & 
                            (df_geolocation.geolocation_lng <= -34.79314722)]
    geo_group = geo_prep.groupby('geolocation_zip_code_prefix', as_index=False).min()

    # Menggabungkan semua informasi
    df_train = df_train.merge(br_info, how='left', left_on='customer_state', right_on='sigla')
    df_train = df_train.merge(geo_group, how='left', left_on='customer_zip_code_prefix', 
                                            right_on='geolocation_zip_code_prefix')

    # Menyiapkan lokasi
    lats = list(df_train.query('year == 2018')['geolocation_lat'].dropna().values)[:30000]
    longs = list(df_train.query('year == 2018')['geolocation_lng'].dropna().values)[:30000]
    locations = list(zip(lats, longs))

    # Membuat peta menggunakan folium
    map1 = folium.Map(location=[-15, -50], zoom_start=4.0)

    # Plugin: FastMarkerCluster
    FastMarkerCluster(data=locations).add_to(map1)

    # Menampilkan peta dalam Streamlit
    folium_static(map1)