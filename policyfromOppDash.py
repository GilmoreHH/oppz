import streamlit as st
from simple_salesforce import Salesforce
import os
from dotenv import load_dotenv
import plotly.express as px
import pandas as pd
import pytz
from datetime import datetime, timedelta

# Load environment variables from .env file
load_dotenv()

# Function to calculate date ranges using US/Eastern timezone
def get_date_range(period):
    """Return start and end ISO dates for the selected period (Week, Month, Quarter)."""
    tz = pytz.timezone("US/Eastern")
    today = datetime.now(tz)
    
    if period == "Week":
        # Monday start and Sunday end
        start_of_period = (today - timedelta(days=today.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_period = start_of_period + timedelta(days=6, hours=23, minutes=59, seconds=59)
    elif period == "Month":
        start_of_period = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_of_period = (start_of_period + timedelta(days=31)).replace(day=1) - timedelta(seconds=1)
    elif period == "Quarter":
        quarter = (today.month - 1) // 3 + 1
        start_of_period = datetime(today.year, 3 * quarter - 2, 1, tzinfo=tz)
        if quarter < 4:
            end_of_period = datetime(today.year, 3 * quarter + 1, 1, tzinfo=tz) - timedelta(seconds=1)
        else:
            end_of_period = datetime(today.year, 12, 31, 23, 59, 59, tzinfo=tz)
    else:
        raise ValueError("Invalid period selected")
    
    # Convert to the correct DateTime string format for Salesforce
    return start_of_period.strftime("%Y-%m-%dT%H:%M:%S%z"), end_of_period.strftime("%Y-%m-%dT%H:%M:%S%z")


# Function to connect to Salesforce and execute SOQL query for policies
def connect_to_salesforce_and_run_query(start_date, end_date):
    try:
        # Connect to Salesforce
        sf = Salesforce(
            username=os.getenv("SF_USERNAME_PRO"),
            password=os.getenv("SF_PASSWORD_PRO"),
            security_token=os.getenv("SF_SECURITY_TOKEN_PRO"),
        )
        st.success("Salesforce connection successful!")

        # SOQL query with LIMIT
        soql_query = f"""
            SELECT PolicyType, COUNT(Id) PolicyCount, MIN(CreatedDate) CreatedDate
            FROM InsurancePolicy
            WHERE SourceOpportunityId != NULL
            AND CreatedDate >= {start_date}
            AND CreatedDate <= {end_date}
            GROUP BY SourceOpportunityId, PolicyType
            LIMIT 2000
        """
        
        query_results = sf.query_all(soql_query)
        records = query_results['records']
        
        # Use queryMore to retrieve all pages if there are more records
        while 'nextRecordsUrl' in query_results:
            query_results = sf.query_more(query_results['nextRecordsUrl'], True)
            records.extend(query_results['records'])
        
        # Create DataFrame from records
        df = pd.DataFrame(records)
        
        # Drop 'Attributes' column if it exists
        df = df.drop(columns=['attributes'], errors='ignore')

        # Optional: log dataframe columns for debugging
        st.write("Returned columns:", df.columns.tolist())
        
        df['OpportunityIndex'] = range(1, len(df) + 1)
        df['PolicyCount'] = df['PolicyCount'].astype(int)
        df['CreatedDate'] = pd.to_datetime(df['CreatedDate'])

        return df, soql_query

    except Exception as e:
        st.error(f"Error while querying Salesforce: {str(e)}")
        return None, None


# Streamlit UI - Dashboard Layout
# Streamlit UI - Dashboard Layout
st.title("New Business Binds Dashboard")

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.df = None
    st.session_state.query = None
    st.session_state.force_query = False

st.sidebar.header("Authentication & Filter Options")

# Filter selection for period (Week, Month, Quarter)
selected_period = st.sidebar.selectbox("Select Period", options=["Week", "Month", "Quarter"], index=0)
start_date, end_date = get_date_range(selected_period)
st.sidebar.write(f"**Date Range:**\nFrom: {start_date}\nTo: {end_date}")

# Button to trigger query
run_query_button = st.sidebar.button("Authenticate & Run Query")

if run_query_button:
    # If the button is pressed, authenticate and fetch the data
    st.session_state.force_query = True

# Authenticate and fetch data only when button is pressed or period is changed
if st.session_state.force_query or not st.session_state.authenticated:
    if run_query_button:
        # Authenticate and fetch the query when the button is pressed
        df, query = connect_to_salesforce_and_run_query(start_date, end_date)
        if df is not None:
            st.session_state.authenticated = True
            st.session_state.df = df
            st.session_state.query = query
            st.session_state.force_query = False
            st.sidebar.success("Authentication successful. You can now view and filter the data.")
else:
    st.sidebar.success("Already authenticated. You can view and interact with the data.")

if st.session_state.authenticated:
    # Use the "PolicyType" field for filtering
    unique_policy_types = sorted(st.session_state.df['PolicyType'].dropna().unique())
    selected_policy_types = st.sidebar.multiselect("Select Policy Types", options=unique_policy_types, default=unique_policy_types)

    # Filter the dataframe based on PolicyType selection
    filtered_df = st.session_state.df[st.session_state.df['PolicyType'].isin(selected_policy_types)]

    # Display the summary of filtered data
    st.subheader("Insurance Policies Summary")
    st.metric("Total Policies", filtered_df['PolicyCount'].sum())

    st.subheader("SOQL Query")
    st.code(st.session_state.query)

    st.subheader("Insurance Policies Data")
    st.dataframe(filtered_df)

    st.subheader("Visualizations")
    chart_type = st.sidebar.selectbox(
        "Select Chart Type",
        options=["Bar Chart", "Scatter Plot", "Line Chart", "Histogram", "Box Plot"]
    )

    policies_data = filtered_df[['OpportunityIndex', 'PolicyCount']]

    if chart_type == "Bar Chart":
        fig = px.bar(policies_data, x='OpportunityIndex', y='PolicyCount',
                     title="Policies per Opportunity (Anonymized)",
                     labels={"OpportunityIndex": "Opportunity Index", "PolicyCount": "Policy Count"})
        st.plotly_chart(fig)
    elif chart_type == "Scatter Plot":
        fig = px.scatter(policies_data, x='OpportunityIndex', y='PolicyCount',
                         title="Policies vs Opportunity (Anonymized)")
        st.plotly_chart(fig)
    elif chart_type == "Line Chart":
        fig = px.line(policies_data, x='OpportunityIndex', y='PolicyCount',
                      title="Policies Over Opportunities (Line Chart)")
        st.plotly_chart(fig)
    elif chart_type == "Histogram":
        fig = px.histogram(policies_data, x='PolicyCount',
                           title="Distribution of Policies by Count")
        st.plotly_chart(fig)
    elif chart_type == "Box Plot":
        fig = px.box(policies_data, x='OpportunityIndex', y='PolicyCount',
                     title="Policies by Opportunity (Box Plot)")
        st.plotly_chart(fig)
else:
    st.warning("Authenticate first to view data and charts.")

