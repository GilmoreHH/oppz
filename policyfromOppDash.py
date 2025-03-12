import streamlit as st
from simple_salesforce import Salesforce
import os
from dotenv import load_dotenv
import plotly.express as px
import pandas as pd

# Load environment variables from .env file
load_dotenv()

# Function to connect to Salesforce and execute SOQL query
def connect_to_salesforce_and_run_query(source_opportunity_filter=None):
    """Connect to Salesforce and execute SOQL query for insurance policies."""
    try:
        # Connect to Salesforce using environment variables
        sf = Salesforce(
            username=os.getenv("SF_USERNAME_PRO"),
            password=os.getenv("SF_PASSWORD_PRO"),
            security_token=os.getenv("SF_SECURITY_TOKEN_PRO"),
        )
        st.success("Salesforce connection successful!")

        # Define the SOQL query with optional filter for SourceOpportunityId
        soql_query = """
            SELECT SourceOpportunityId, COUNT(Id) 
            FROM InsurancePolicy
            WHERE CreatedDate = LAST_N_DAYS:7 AND SourceOpportunityId != NULL
            GROUP BY SourceOpportunityId
        """
        
        # Apply SourceOpportunityId filter if provided
        if source_opportunity_filter:
            soql_query += f" AND SourceOpportunityId = '{source_opportunity_filter}'"
        
        # Execute the SOQL query
        query_results = sf.query_all(soql_query)
        
        # Extract and prepare data for visualization
        records = query_results['records']
        df = pd.DataFrame(records)
        
        # Convert fields to the correct types
        df['SourceOpportunityId'] = df['SourceOpportunityId'].astype(str)
        df['expr0'] = df['expr0'].astype(int)  # 'expr0' holds the COUNT(Id) result
        
        # Return the dataframe and query used
        return df, soql_query, source_opportunity_filter
        
    except Exception as e:
        st.error(f"Error while querying Salesforce: {str(e)}")
        return None, None, None


# Streamlit UI - Dashboard Layout
st.title("Salesforce Insurance Policies Dashboard")

# Session state for persistent variables
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.df = None
    st.session_state.query = None
    st.session_state.source_opportunity_filter = None
    st.session_state.total_count = 0

# Sidebar for filters and authentication
st.sidebar.header("Authentication & Filter Options")

# Authenticate only once
if not st.session_state.authenticated:
    if st.sidebar.button("Authenticate & Run Query"):
        # Try connecting to Salesforce (authentication check)
        df, query, source_opportunity_filter = connect_to_salesforce_and_run_query()
        if df is not None:
            st.session_state.authenticated = True
            st.session_state.df = df
            st.session_state.query = query
            st.session_state.source_opportunity_filter = source_opportunity_filter
            st.session_state.total_count = len(df)
            st.sidebar.success("Authentication successful. You can now view and filter the data.")
else:
    st.sidebar.success("Already authenticated. You can view and interact with the data.")

# Main content area
if st.session_state.authenticated:
    # Display the total number of policies
    st.subheader("Insurance Policies Summary")
    st.metric("Total Policies", st.session_state.total_count)

    # Display SOQL query used
    st.subheader("SOQL Query")
    st.code(st.session_state.query)

    # Display filters applied in the query
    st.subheader("Filters Applied")
    st.write(f"Source Opportunity Filter: {st.session_state.source_opportunity_filter if st.session_state.source_opportunity_filter else 'None'}")

    # Sidebar Filter Options for SourceOpportunityId
    st.sidebar.header("Apply Filters")
    source_opportunity_filter_input = st.sidebar.text_input("Source Opportunity Id", value=st.session_state.source_opportunity_filter if st.session_state.source_opportunity_filter else "")

    # Update data with the selected filter
    if source_opportunity_filter_input:
        df, query, source_opportunity_filter_input = connect_to_salesforce_and_run_query(source_opportunity_filter_input)
        if df is not None:
            st.session_state.df = df
            st.session_state.query = query
            st.session_state.source_opportunity_filter = source_opportunity_filter_input
            st.session_state.total_count = len(df)

    # Visualization Section
    st.subheader("Visualizations")
    
    # Chart Type Selection in Sidebar
    chart_type = st.sidebar.selectbox(
        "Select Chart Type", 
        options=["Bar Chart", "Pie Chart", "Scatter Plot", "Line Chart", "Histogram", "Box Plot"]
    )

    # Display the appropriate chart based on user selection
    if chart_type == "Bar Chart":
        policies_per_opportunity = st.session_state.df.groupby('SourceOpportunityId').agg({'expr0': 'sum'}).reset_index()
        fig1 = px.bar(policies_per_opportunity, x='SourceOpportunityId', y='expr0', title="Insurance Policies Per Opportunity")
        st.plotly_chart(fig1)

    elif chart_type == "Pie Chart":
        policies_per_opportunity = st.session_state.df.groupby('SourceOpportunityId').agg({'expr0': 'sum'}).reset_index()
        fig2 = px.pie(policies_per_opportunity, names='SourceOpportunityId', values='expr0', title="Insurance Policies Distribution by Opportunity")
        st.plotly_chart(fig2)

    elif chart_type == "Scatter Plot":
        fig3 = px.scatter(st.session_state.df, x='SourceOpportunityId', y='expr0', title="Policies vs Opportunity")
        st.plotly_chart(fig3)

    elif chart_type == "Line Chart":
        policies_per_opportunity = st.session_state.df.groupby('SourceOpportunityId').agg({'expr0': 'sum'}).reset_index()
        fig4 = px.line(policies_per_opportunity, x='SourceOpportunityId', y='expr0', title="Insurance Policies Over Opportunities (Line Chart)")
        st.plotly_chart(fig4)

    elif chart_type == "Histogram":
        fig5 = px.histogram(st.session_state.df, x='expr0', title="Distribution of Policies by Count")
        st.plotly_chart(fig5)

    elif chart_type == "Box Plot":
        fig6 = px.box(st.session_state.df, x='SourceOpportunityId', y='expr0', title="Policies by Opportunity (Box Plot)")
        st.plotly_chart(fig6)

else:
    st.warning("Authenticate first to view data and charts.")
