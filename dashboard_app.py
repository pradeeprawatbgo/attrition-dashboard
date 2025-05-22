import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import time

# Set page config
st.set_page_config(
    page_title="Attrition Tracking Dashboard",
    page_icon="📊",
    layout="wide"
    
)
# Add refresh button next to the page title
col1, col2 = st.columns([0.9, 0.1])
with col1:
    st.subheader("📊 Attrition Tracking Dashboard")
with col2:
    if st.button("🔄 Refresh",key="refresh_button", use_container_width=True):
        st.session_state.last_refresh = datetime.now()
        st.rerun()



# Initialize session state for auto-refresh
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.now()

# Auto-refresh every 30 seconds
if (datetime.now() - st.session_state.last_refresh).seconds > 30:
    st.session_state.last_refresh = datetime.now()
    st.rerun()

# Sidebar
with st.sidebar:
    st.title("📊 Attrition Tracking Dashboard")
    st.markdown("---")
    st.markdown("### About")
    st.markdown("""
    This dashboard provides insights into employee attrition predictions:
    - Total inactive employee count
    - Risk level distribution
    - Detailed employee list
    - Historical trends
    """)
    
    # # Add refresh button
    # if st.button("🔄 Refresh Data"):
    #     st.session_state.last_refresh = datetime.now()
    #     st.rerun()

# Main content
# st.title("📊 Attrition Tracking Dashboard")

# Function to load and process data
@st.cache_data(ttl=30)  # Cache for 30 seconds
def load_data():
    try:
        df = pd.read_excel('false_positives_tracking.xlsx')
        df['Prediction_Date'] = pd.to_datetime(df['Prediction_Date'])
        # Convert comment columns to string type
        df['HR_Comments'] = df['HR_Comments'].astype(str)
        df['OPS_comments'] = df['OPS_comments'].astype(str)
        # Replace 'nan' with empty string
        df['HR_Comments'] = df['HR_Comments'].replace('nan', '')
        df['OPS_comments'] = df['OPS_comments'].replace('nan', '')
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

# Load data
df = load_data()

if df is not None:
    # Date filter
    # st.subheader("📅 Date Range Filter")
    col1, col2 = st.columns(2)
    
    with col1:
        min_date = df['Prediction_Date'].min().date()
        max_date = df['Prediction_Date'].max().date()
        start_date = st.date_input("Start Date", min_date, key="start_date")
    
    with col2:
        end_date = st.date_input("End Date", max_date, key="end_date")
    
    # Filter data based on date range
    mask = (df['Prediction_Date'].dt.date >= start_date) & (df['Prediction_Date'].dt.date <= end_date)
    filtered_df = df[mask]
    
    # Top metrics
    st.subheader("📈 Key Metrics")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_inactive = (filtered_df['Attrition Prediction'] == 'Possible Attrition').sum()
        st.metric("Total Inactive Employees", total_inactive)
    
    with col2:
        severe_count = filtered_df[filtered_df['Risk Level'] == 'Severe'].shape[0]
        st.metric("Severe Risk", severe_count, delta_color="off")
    
    with col3:
        more_likely_count = filtered_df[filtered_df['Risk Level'] == 'More Likely'].shape[0]
        st.metric("More Likely", more_likely_count, delta_color="off")
    
    with col4:
        intermediate_count = filtered_df[filtered_df['Risk Level'] == 'Intermediate Risk'].shape[0]
        st.metric("Intermediate Risk", intermediate_count, delta_color="off")
    
    with col5:
        mild_count = filtered_df[filtered_df['Risk Level'] == 'Mild Risk'].shape[0]
        st.metric("Mild Risk", mild_count, delta_color="off")
    
    # Risk Level Distribution
    st.subheader("⚠️ Risk Level Distribution")
    
    # Create two columns for charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Create ordered risk levels
        risk_order = ['Severe', 'More Likely', 'Intermediate Risk', 'Mild Risk']
        risk_counts = filtered_df['Risk Level'].value_counts().reindex(risk_order)
        
        # Create horizontal bar chart
        fig_risk = px.bar(
            x=risk_counts.index,
            y=risk_counts.values,
            orientation='v',
            title="Distribution of Risk Levels",
            color=risk_counts.index,
            color_discrete_map={
                'Severe': '#ff4d4d',
                'More Likely': '#ff944d',
                'Intermediate Risk': '#ffc04d',
                'Mild Risk': '#ffe04d'
            }
        )
        
        # Update layout
        fig_risk.update_layout(
            xaxis_title="Risk Level",
            yaxis_title="Number of Employees",
            showlegend=False,
            bargap=0.6,
            height=400,
            width=200
        )
        
        st.plotly_chart(fig_risk, use_container_width=True)
    
    with col2:
        try:
            # Get cost center distribution for inactive employees
            if 'Cost Center' in filtered_df.columns:
                cost_center_counts = filtered_df[filtered_df['Attrition Prediction'] == 'Possible Attrition']['Cost Center'].value_counts()
            elif 'Cost Center Encoded' in filtered_df.columns:
                cost_center_counts = filtered_df[filtered_df['Attrition Prediction'] == 'Possible Attrition']['Cost Center Encoded'].value_counts()
            else:
                st.warning("Cost Center information not available in the data")
                cost_center_counts = pd.Series()
            
            if not cost_center_counts.empty:
                # Get top 5 cost centers
                top_5_centers = cost_center_counts.head(5)
                
                # # Create bar chart for top 5 cost centers
                # fig_top5 = px.bar(
                #     x=top_5_centers.values,
                #     y=top_5_centers.index,
                #     orientation='h',
                #     title="Top 5 Cost Centers by Attrition Count",
                #     color=top_5_centers.values,
                #     color_continuous_scale='Reds'
                # )
                
                # # Update layout
                # fig_top5.update_layout(
                #     xaxis_title="Number of Employees",
                #     yaxis_title="Cost Center",
                #     showlegend=False,
                #     height=400
                # )
                
                # st.plotly_chart(fig_top5, use_container_width=True)
                
                # Create pie chart for all cost centers
                fig_cost = px.pie(
                    values=top_5_centers.values,
                    names=top_5_centers.index,
                    title="Distribution by Cost Center (Top 5)",
                    hole=0.5  # Creates a donut chart
                )
                
                # Update layout
                fig_cost.update_layout(
                    height=400,
                    showlegend=True,
                    legend=dict(
                        orientation="v",
                        yanchor="top",
                        y=-0.2,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=10)
                    ),
                    margin=dict(l=10, r=20, t=40, b=20)
                )
                
                st.plotly_chart(fig_cost, use_container_width=True)
            else:
                st.info("No cost center data available to display")
        except Exception as e:
            st.error(f"Error creating cost center chart: {str(e)}")
    
    # Employee List
    st.subheader("👥 Employee List")
    
    # Add filters for the table
    col1, col2 = st.columns(2)
    with col1:
        risk_filter = st.multiselect(
            "Filter by Risk Level",
            options=sorted(filtered_df['Risk Level'].unique()),
            default=sorted(filtered_df['Risk Level'].unique()),
            key="risk_filter"
        )
    
    with col2:
        probability_threshold = st.slider(
            "Minimum Attrition Probability",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.1,
            format="%0.1f",
            key="prob_threshold"
        )
    
    # Apply filters
    table_df = filtered_df[
        (filtered_df['Risk Level'].isin(risk_filter)) &
        (filtered_df['Attrition Probability'] >= probability_threshold)
    ]
    
    # Sort by Attrition Probability
    table_df = table_df.sort_values('Attrition Probability', ascending=False)
    
    # Add a delete checkbox column
    table_df['Delete'] = False
    
    # Display table with selected columns
    display_cols = ['Employee ID', 'Attrition Prediction', 'Attrition Probability', 
                   'Risk Level', 'Triggers', 'Prediction_Date', 'HR_Comments', 'OPS_comments']
    
    # Format the table
    table_df['Attrition Probability'] = table_df['Attrition Probability'].map('{:.2%}'.format)
    table_df['Prediction_Date'] = table_df['Prediction_Date'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Show the table with checkboxes
    edited_df = st.data_editor(
        table_df[display_cols + ['Delete']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "HR_Comments": st.column_config.TextColumn(
                "HR Comments",
                help="Add HR comments here",
                width="large"
            ),
            "OPS_comments": st.column_config.TextColumn(
                "OPS Comments",
                help="Add OPS comments here",
                width="large"
            ),
            "Delete": st.column_config.CheckboxColumn(
                "Delete",
                help="Check to mark this row for deletion"
            )
        },
        key="data_editor"
    )
    
    # --- BUTTONS SECTION ---
    col_save, _,col_delete = st.columns([1,7,1])

    with col_save:
        if st.button("Save Comments"):
            try:
                # Read the original file
                original_df = pd.read_excel('false_positives_tracking.xlsx')
                # Update comments in original dataframe
                for idx, row in edited_df.iterrows():
                    mask = (original_df['Employee ID'] == row['Employee ID']) & \
                           (original_df['Prediction_Date'] == row['Prediction_Date'])
                    original_df.loc[mask, 'HR_Comments'] = row['HR_Comments']
                    original_df.loc[mask, 'OPS_comments'] = row['OPS_comments']
                # Save back to Excel
                original_df.to_excel('false_positives_tracking.xlsx', index=False)
                st.session_state.action_message = "Comments saved successfully!"
                st.session_state.action_message_type = "success"
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.session_state.action_message = f"Error saving comments: {str(e)}"
                st.session_state.action_message_type = "error"
                st.rerun()

    with col_delete:
        if st.button("Delete Selected"):
            try:
                # Read the original file
                original_df = pd.read_excel('false_positives_tracking.xlsx')
                # Find rows to delete
                to_delete = edited_df[edited_df['Delete']]
                for idx, row in to_delete.iterrows():
                    mask = (
                        (original_df['Employee ID'] == row['Employee ID']) &
                        (original_df['Prediction_Date'] == row['Prediction_Date'])
                    )
                    original_df = original_df[~mask]
                # Save back to Excel
                original_df.to_excel('false_positives_tracking.xlsx', index=False)
                st.session_state.action_message = "Selected rows deleted successfully!"
                st.session_state.action_message_type = "success"
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.session_state.action_message = f"Error deleting rows: {str(e)}"
                st.session_state.action_message_type = "error"
                st.rerun()
    
    # Download button for filtered data
    csv = edited_df[display_cols].to_csv(index=False)
    st.download_button(
        label="Download Filtered Data",
        data=csv,
        file_name=f"attrition_tracking_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
else:
    st.warning("No data available. Please ensure the tracking file exists and contains data.") 

if 'action_message' not in st.session_state:
    st.session_state.action_message = ""
if 'action_message_type' not in st.session_state:
    st.session_state.action_message_type = "success"

if st.session_state.action_message:
    st.markdown(
        f"<div style='text-align:center; font-size:18px; color:{'green' if st.session_state.action_message_type == 'success' else 'red'}; margin-bottom: 20px;'>{st.session_state.action_message}</div>",
        unsafe_allow_html=True
    )
    # Optionally clear the message after showing it once
    st.session_state.action_message = ""
