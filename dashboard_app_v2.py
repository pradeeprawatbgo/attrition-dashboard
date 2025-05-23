import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import time
from google_sheets_utils import get_sheet_data, update_sheet_data, append_sheet_data

# Set page config
st.set_page_config(
    page_title="Attrition Tracking Dashboard",
    page_icon="📊",
    layout="wide"
)

# Google Sheet configuration
SPREADSHEET_ID = st.secrets["spreadsheet_id"]
TRACKING_SHEET_RANGE = "Tracking!A:Z"  # Adjust based on your sheet name and range

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

# Function to load and process data
@st.cache_data(ttl=30)  # Cache for 30 seconds
def load_data():
    try:
        df = get_sheet_data(SPREADSHEET_ID, TRACKING_SHEET_RANGE)
        if df is None:
            st.error("Error loading data from Google Sheet")
            return None
            
        df['Prediction_Date'] = pd.to_datetime(df['Prediction_Date'])
        # Convert comment columns to string type
        df['HR_Comments'] = df['HR_Comments'].astype(str)
        df['OPS_comments'] = df['OPS_comments'].astype(str)
        # Replace 'nan' with empty string
        df['HR_Comments'] = df['HR_Comments'].replace('nan', '')
        df['OPS_comments'] = df['OPS_comments'].replace('nan', '')
        
        # Convert Attrition Probability to numeric, handling percentage format
        if 'Attrition Probability' in df.columns:
            # Remove % sign if present and convert to float
            df['Attrition Probability'] = df['Attrition Probability'].astype(str).str.rstrip('%').astype('float') / 100.0
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

# Clear cache when needed
def clear_cache():
    load_data.clear()

# Load data
df = load_data()

if df is not None:
    # Date filter
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
            options=sorted(df['Risk Level'].unique()),
            default=sorted(df['Risk Level'].unique()),
            key="risk_filter"
        )
    
    with col2:
        # Set default range for probability slider
        min_prob = 0.0
        max_prob = 1.0
        default_value = 0.0
        
        # Only update if we have valid probability values
        if df['Attrition Probability'].max() > 0:
            min_prob = float(df['Attrition Probability'].min())
            max_prob = float(df['Attrition Probability'].max())
            default_value = min_prob
        
        probability_threshold = st.slider(
            "Minimum Attrition Probability",
            min_value=min_prob,
            max_value=max_prob,
            value=default_value,
            step=0.01,
            format="%0.2f",
            key="prob_threshold"
        )
    
    # Apply filters
    table_df = df[
        (df['Risk Level'].isin(risk_filter)) &
        (df['Attrition Probability'] >= probability_threshold)
    ].copy()
    
    if len(table_df) == 0:
        st.warning("No data matches the current filters. Please adjust the filters.")
        st.stop()
    
    # Sort by Attrition Probability
    table_df = table_df.sort_values('Attrition Probability', ascending=False)
    
    # Add a delete checkbox column
    table_df['Delete'] = False
    
    # Remove existing SR.No. column if it exists
    if 'SR.No.' in table_df.columns:
        table_df = table_df.drop('SR.No.', axis=1)
    
    # Create SR.No. column
    table_df.insert(0, 'SR.No.', range(1, len(table_df) + 1))
    
    # Display table with selected columns
    display_cols = ['SR.No.', 'Employee ID', 'Attrition Prediction', 'Attrition Probability', 
                   'Risk Level', 'Triggers', 'Prediction_Date', 'Cost Center', 'HR_Comments', 'OPS_comments']
    
    # Format the table
    table_df['Prediction_Date'] = pd.to_datetime(table_df['Prediction_Date']).dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Select only the columns we want to display
    table_df = table_df[display_cols + ['Delete']]
    
    # Show the table with checkboxes
    edited_df = st.data_editor(
        table_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "SR.No.": st.column_config.NumberColumn(
                "SR.No.",
                help="Serial Number",
                width="small"
            ),
            "Attrition Probability": st.column_config.NumberColumn(
                "Attrition Probability",
                help="Probability of attrition",
                width="medium",
                format="%.2f%%",
                step=0.01,
                min_value=0.0,
                max_value=1.0
            ),
            "Cost Center": st.column_config.TextColumn(
                "Cost Center",
                help="Employee's Cost Center",
                width="medium"
            ),
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
    col_save, _,col_delete = st.columns([1,7.7,1])

    with col_save:
        if st.button("Save Comments"):
            try:
                # Get the current data from Google Sheet
                current_df = get_sheet_data(SPREADSHEET_ID, TRACKING_SHEET_RANGE)
                if current_df is None:
                    st.error("Error loading current data from Google Sheet")
                    st.stop()
                
                # Convert Prediction_Date to datetime for comparison
                current_df['Prediction_Date'] = pd.to_datetime(current_df['Prediction_Date'])
                edited_df['Prediction_Date'] = pd.to_datetime(edited_df['Prediction_Date'])
                
                # Update comments in the dataframe
                for idx, row in edited_df.iterrows():
                    mask = (current_df['Employee ID'] == row['Employee ID']) & \
                           (current_df['Prediction_Date'] == row['Prediction_Date'])
                    if mask.any():
                        current_df.loc[mask, 'HR_Comments'] = str(row['HR_Comments'])
                        current_df.loc[mask, 'OPS_comments'] = str(row['OPS_comments'])
                
                # Convert timestamp to string format before saving
                current_df['Prediction_Date'] = current_df['Prediction_Date'].dt.strftime('%Y-%m-%d %H:%M:%S')
                
                # Clean and format the data
                current_df = current_df.fillna('')  # Replace NaN with empty string
                
                # Convert numeric columns to string format
                if 'Attrition Probability' in current_df.columns:
                    # First convert to numeric, then format as percentage
                    current_df['Attrition Probability'] = pd.to_numeric(current_df['Attrition Probability'], errors='coerce')
                    current_df['Attrition Probability'] = current_df['Attrition Probability'].apply(
                        lambda x: f"{x:.2%}" if pd.notnull(x) else ''
                    )
                
                # Save back to Google Sheet
                if update_sheet_data(SPREADSHEET_ID, TRACKING_SHEET_RANGE, current_df):
                    st.session_state.action_message = "Comments saved successfully!"
                    st.session_state.action_message_type = "success"
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Failed to save comments to Google Sheet")
            except Exception as e:
                st.session_state.action_message = f"Error saving comments: {str(e)}"
                st.session_state.action_message_type = "error"
                st.rerun()

    with col_delete:
        if st.button("Delete Selected"):
            try:
                # Get the current data from Google Sheet
                current_df = get_sheet_data(SPREADSHEET_ID, TRACKING_SHEET_RANGE)
                if current_df is None:
                    st.error("Error loading current data from Google Sheet")
                    st.stop()
                
                # Convert Prediction_Date to datetime for comparison
                current_df['Prediction_Date'] = pd.to_datetime(current_df['Prediction_Date'])
                edited_df['Prediction_Date'] = pd.to_datetime(edited_df['Prediction_Date'])
                
                # Find rows to delete
                to_delete = edited_df[edited_df['Delete']]
                if not to_delete.empty:
                    # Create a mask for rows to keep
                    mask = pd.Series(True, index=current_df.index)
                    for _, row in to_delete.iterrows():
                        delete_mask = (
                            (current_df['Employee ID'] == row['Employee ID']) &
                            (current_df['Prediction_Date'] == row['Prediction_Date'])
                        )
                        mask = mask & ~delete_mask
                    
                    # Keep only rows that weren't marked for deletion
                    current_df = current_df[mask]
                    
                    # Convert timestamp to string format before saving
                    current_df['Prediction_Date'] = current_df['Prediction_Date'].dt.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Save back to Google Sheet
                    if update_sheet_data(SPREADSHEET_ID, TRACKING_SHEET_RANGE, current_df):
                        # Clear the cache to force a fresh data load
                        clear_cache()
                        st.session_state.action_message = "Selected rows deleted successfully!"
                        st.session_state.action_message_type = "success"
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("Failed to delete rows from Google Sheet")
                else:
                    st.warning("No rows selected for deletion")
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
    st.warning("No data available. Please ensure the Google Sheet exists and contains data.") 

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
