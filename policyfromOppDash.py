import streamlit as st
from simple_salesforce import Salesforce
import os
from dotenv import load_dotenv
import plotly.express as px
import pandas as pd

# Load environment variables from .env file
load_dotenv()

# Function to connect to Salesforce and execute SOQL query
def connect_to_salesforce_and_run_query():
    """Connect to Salesforce and execute SOQL query for insurance policies."""
    try:
        # Connect to Salesforce using environment variables
        sf = Salesforce(
            username=os.getenv("SF_USERNAME_PRO"),
            password=os.getenv("SF_PASSWORD_PRO"),
            security_token=os.getenv("SF_SECURITY_TOKEN_PRO"),
        )
        st.success("Salesforce connection successful!")

        # Define the SOQL query without filters for SourceOpportunityId
        soql_query = """
            SELECT SourceOpportunityId, COUNT(Id) 
            FROM InsurancePolicy
            WHERE CreatedDate = LAST_N_DAYS:7 AND SourceOpportunityId != NULL
            GROUP BY SourceOpportunityId
        """
        
        # Execute the SOQL query
        query_results = sf.query_all(soql_query)
        
        # Extract and prepare data for visualization
        records = query_results['records']
        df = pd.DataFrame(records)
        
        # Convert fields to the correct types
        df['SourceOpportunityId'] = df['SourceOpportunityId'].astype(str)
        df['expr0'] = df['expr0'].astype(int)  # 'expr0' holds the COUNT(Id) result
        
        # Return the dataframe and query used
        return df, soql_query
        
    except Exception as e:
        st.error(f"Error while querying Salesforce: {str(e)}")
        return None, None


# Streamlit UI - Dashboard Layout
st.title("New Business Binds")

# Session state for persistent variables
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.df = None
    st.session_state.query = None
    st.session_state.total_count = 0

# Sidebar for filters and authentication
st.sidebar.header("Authentication & Filter Options")

# Authenticate only once
if not st.session_state.authenticated:
    if st.sidebar.button("Authenticate & Run Query"):
        # Try connecting to Salesforce (authentication check)
        df, query = connect_to_salesforce_and_run_query()
        if df is not None:
            st.session_state.authenticated = True
            st.session_state.df = df
            st.session_state.query = query
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

    # Visualization Section
    st.subheader("Visualizations")
    
    # Chart Type Selection in Sidebar
    chart_type = st.sidebar.selectbox(
        "Select Chart Type", 
        options=["Bar Chart", "Pie Chart", "Scatter Plot", "Line Chart", "Histogram", "Box Plot"]
    )

    # Process data without displaying SourceOpportunityId in any chart
    policies_per_opportunity = st.session_state.df.groupby('SourceOpportunityId').agg({'expr0': 'sum'}).reset_index()

    # Remove SourceOpportunityId from visualization; we will display only the aggregated counts
    policies_per_opportunity['Policy Count'] = policies_per_opportunity['expr0']

    # Display the appropriate chart based on user selection
    if chart_type == "Bar Chart":
        fig1 = px.bar(policies_per_opportunity, x=policies_per_opportunity.index, y='Policy Count', title="Insurance Policies Per Opportunity")
        fig1.update_layout(xaxis_title="Policy Index", yaxis_title="Policy Count")
        st.plotly_chart(fig1)

    elif chart_type == "Pie Chart":
        fig2 = px.pie(policies_per_opportunity, names=policies_per_opportunity.index, values='Policy Count', title="Insurance Policies Distribution by Opportunity")
        fig2.update_traces(textinfo='percent+label')
        st.plotly_chart(fig2)

    elif chart_type == "Scatter Plot":
        fig3 = px.scatter(policies_per_opportunity, x=policies_per_opportunity.index, y='Policy Count', title="Policies vs Opportunity")
        fig3.update_traces(mode='markers', marker=dict(size=12))
        st.plotly_chart(fig3)

    elif chart_type == "Line Chart":
        fig4 = px.line(policies_per_opportunity, x=policies_per_opportunity.index, y='Policy Count', title="Insurance Policies Over Opportunities (Line Chart)")
        fig4.update_layout(xaxis_title="Policy Index", yaxis_title="Policy Count")
        st.plotly_chart(fig4)

    elif chart_type == "Histogram":
        fig5 = px.histogram(policies_per_opportunity, x='Policy Count', title="Distribution of Policies by Count")
        st.plotly_chart(fig5)

    elif chart_type == "Box Plot":
        fig6 = px.box(policies_per_opportunity, x=policies_per_opportunity.index, y='Policy Count', title="Policies by Opportunity (Box Plot)")
        st.plotly_chart(fig6)

else:
    st.warning("Authenticate first to view data and charts.")
