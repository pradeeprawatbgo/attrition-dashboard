import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import time
from google_sheets_utils_v2 import get_sheet_data, update_sheet_data, append_sheet_data

# Set page config
st.set_page_config(
    page_title="Attrition Tracking Dashboard",
    page_icon="📊",
    layout="wide"
)

# Google Sheet configuration
SPREADSHEET_ID = st.secrets["spreadsheet_id"]
TRACKING_SHEET_RANGE = "Tracking!A:Z"  # Adjust based on your sheet name and range

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
            
        df['Date of Report Generation'] = pd.to_datetime(df['Date of Report Generation'])
        # Convert comment columns to string type
        df['HR_Comments'] = df['HR_Comments'].astype(str)
        df['OPS_comments'] = df['OPS_comments'].astype(str)
        # Replace 'nan' with empty string
        df['HR_Comments'] = df['HR_Comments'].replace('nan', '')
        df['OPS_comments'] = df['OPS_comments'].replace('nan', '')
        
        # Convert Attrition Probability to numeric
        df['Attrition Probability'] = df['Attrition Probability'].astype(str).str.replace('%', '')
        df['Attrition Probability'] = pd.to_numeric(df['Attrition Probability'], errors='coerce')
        
        # If values are greater than 1, assume they are percentages and convert to decimal
        df['Attrition Probability'] = df['Attrition Probability'].apply(
            lambda x: x/100 if pd.notnull(x) and x > 1 else x
        )
        
        # Fill NaN values with 0
        df['Attrition Probability'] = df['Attrition Probability'].fillna(0)
        
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
    # Add filters at the top: Start Date, End Date, Cost Center, Tenure Bucket
    # Get unique values for filters
    cost_centers = ['All'] + sorted(df['Cost Center'].dropna().unique().tolist())
    tenure_buckets = ['All'] + sorted(df['Tenure Bucket (Today Based)'].dropna().unique().tolist())

    # Add refresh button and filters in a row
    col1, col2, col3, col4= st.columns([ 1, 1, 1, 1])

    with col1:
        min_date = df['Date of Report Generation'].min().date()
        max_date = df['Date of Report Generation'].max().date()
        start_date = st.date_input("Start Date", min_date, key="start_date")

    with col2:
        end_date = st.date_input("End Date", max_date, key="end_date")

    with col3:
        selected_cost_center = st.selectbox("Cost Center", cost_centers, key="cost_center")

    with col4:
        selected_tenure = st.selectbox("Tenure Bucket", tenure_buckets, key="tenure_bucket")
        
    # with col5:
    #     if st.button("🔄 Refresh", key="refresh_button", use_container_width=True):
    #         st.session_state.clear()  # Reset all filters and session state
    #         st.session_state.last_refresh = datetime.now()
    #         st.rerun()

    # Filter data based on all filters
    mask = (df['Date of Report Generation'].dt.date >= start_date) & (df['Date of Report Generation'].dt.date <= end_date)
    if selected_cost_center != 'All':
        mask &= (df['Cost Center'] == selected_cost_center)
    if selected_tenure != 'All':
        mask &= (df['Tenure Bucket (Today Based)'] == selected_tenure)
    filtered_df = df[mask]
    
    # Ensure Attrition Probability is properly formatted
    df['Attrition Probability'] = pd.to_numeric(df['Attrition Probability'].astype(str).str.replace('%', ''), errors='coerce')
    df['Attrition Probability'] = df['Attrition Probability'].apply(lambda x: x/100 if pd.notnull(x) and x > 1 else x)
    df['Attrition Probability'] = df['Attrition Probability'].fillna(0)  # Fill any NaN values with 0

    # Top metrics
    st.subheader("📈 Key Metrics")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    # Define colors for each metric
    metric_colors = {
        'inactive': '#cc0000',  # Red for inactive
        'severe': '#ff4d4d',    # Red for severe
        'more_likely': '#ff944d',  # Orange for more likely
        'intermediate': '#ffc04d',  # Yellow for intermediate
        'mild': '#ffe04d',      # Light yellow for mild
        'regrettable': '#008000'  # Green for regrettable
    }
    
    with col1:
        total_inactive = (filtered_df['Attrition Prediction'] == 'Inactive').sum()
        st.markdown(f"""
        <div style='text-align: center; padding: 10px; background-color: {metric_colors['inactive']}; border-radius: 5px;'>
            <p style='color: white; margin: 0;'>Total Inactive Employees</p>
            <p style='color: white; margin: 0;'>{total_inactive}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        severe_count = filtered_df[filtered_df['Risk Level'] == 'Severe'].shape[0]
        st.markdown(f"""
        <div style='text-align: center; padding: 10px; background-color: {metric_colors['severe']}; border-radius: 5px;'>
            <p style='color: white; margin: 0;'>Severe Risk</p>
            <p style='color: white; margin: 0;'>{severe_count}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        more_likely_count = filtered_df[filtered_df['Risk Level'] == 'More Likely'].shape[0]
        st.markdown(f"""
        <div style='text-align: center; padding: 10px; background-color: {metric_colors['more_likely']}; border-radius: 5px;'>
            <p style='color: white; margin: 0;'>More Likely</p>
            <p style='color: white; margin: 0;'>{more_likely_count}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        intermediate_count = filtered_df[filtered_df['Risk Level'] == 'Intermediate Risk'].shape[0]
        st.markdown(f"""
        <div style='text-align: center; padding: 10px; background-color: {metric_colors['intermediate']}; border-radius: 5px;'>
            <p style='color: white; margin: 0;'>Intermediate Risk</p>
            <p style='color: white; margin: 0;'>{intermediate_count}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        mild_count = filtered_df[filtered_df['Risk Level'] == 'Mild Risk'].shape[0]
        st.markdown(f"""
        <div style='text-align: center; padding: 10px; background-color: {metric_colors['mild']}; border-radius: 5px;'>
            <p style='color: white; margin: 0;'>Mild Risk</p>
            <p style='color: white; margin: 0;'>{mild_count}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col6:
        regrettable_count = filtered_df[filtered_df['Regrettable Y/N'] == 'Yes'].shape[0]
        st.markdown(f"""
        <div style='text-align: center; padding: 10px; background-color: {metric_colors['regrettable']}; border-radius: 5px;'>
            <p style='color: white; margin: 0;'>Regrettable</p>
            <p style='color: white; margin: 0;'>{regrettable_count}</p>
        </div>
        """, unsafe_allow_html=True)
    
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
                # Debug information
                # st.write("Available Attrition Prediction values:", filtered_df['Attrition Prediction'].unique())
                
                # Filter for inactive employees
                inactive_df = filtered_df[filtered_df['Attrition Prediction'].str.lower() == 'inactive']
                cost_center_counts = inactive_df['Cost Center'].value_counts()
                
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
                    st.info("No inactive employees found in the selected date range")
            else:
                st.warning("Cost Center information not available in the data")
        except Exception as e:
            st.error(f"Error creating cost center chart: {str(e)}")
            st.write("Debug - DataFrame columns:", filtered_df.columns.tolist())
            st.write("Debug - Sample data:", filtered_df[['Attrition Prediction', 'Cost Center']].head())
    
    # Employee List
    st.subheader("👥 Employee List")
    
    # Add filters for the table
    # col1, col2 = st.columns(2)
    # with col1:
    #     risk_filter = st.multiselect(
    #         "Filter by Risk Level",
    #         options=sorted(df['Risk Level'].unique()),
    #         default=sorted(df['Risk Level'].unique()),  # Default to all risk levels
    #         key="risk_filter"
    #     )
    
    # with col2:
    #     # Set default range for probability slider
    #     min_prob = 0.0
    #     max_prob = 1.0
    #     default_value = 0.0  # Default to 0 to show all probabilities
        
    #     # Only update if we have valid probability values
    #     if pd.notnull(df['Attrition Probability']).any():
    #         min_prob = float(df['Attrition Probability'].min())
    #         max_prob = float(df['Attrition Probability'].max())
        
    #     probability_threshold = st.slider(
    #         "Minimum Attrition Probability",
    #         min_value=min_prob,
    #         max_value=max_prob,
    #         value=default_value,  # Default to 0
    #         step=0.01,
    #         format="%0.2f",
    #         key="prob_threshold"
    #     )
    
    # # Apply filters
    # table_df = df[
    #     (df['Risk Level'].isin(risk_filter)) &
    #     (df['Attrition Probability'] >= probability_threshold)
    # ].copy()
    table_df = filtered_df.copy()  # Use filtered_df instead of df
    
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
    display_cols = ['SR.No.', 'Date of Report Generation','Employee ID','Employee Name','Cost Center','Attrition Prediction', 'Actual Status','Attrition Probability', 
                   'Risk Level', 'Tenure Bucket (Today Based)','Triggers', 'HR_Comments', 'OPS_comments','Regrettable Y/N']
    
    # Format the table
    table_df['Date of Report Generation'] = pd.to_datetime(table_df['Date of Report Generation']).dt.strftime('%Y-%m-%d')
    
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
                format="%.2f",
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
            "Regrettable Y/N": st.column_config.TextColumn(
                "Regrettable",
                help="Is this attrition regrettable?",
                width="small"
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
                
                # Standardize date format to match the table (YYYY-MM-DD HH:MM:SS)
                current_df['Date of Report Generation'] = pd.to_datetime(current_df['Date of Report Generation'], errors='coerce').dt.strftime('%Y-%m-%d')
                edited_df['Date of Report Generation'] = pd.to_datetime(edited_df['Date of Report Generation'], errors='coerce').dt.strftime('%Y-%m-%d')

                for idx, row in edited_df.iterrows():
                    emp_id = str(row['Employee ID'])
                    date_val = str(row['Date of Report Generation'])
                    current_df['Employee ID'] = current_df['Employee ID'].astype(str)
                    mask = (current_df['Employee ID'] == emp_id) & \
                           (current_df['Date of Report Generation'] == date_val)
                    if mask.sum() > 0:
                        current_df.loc[mask, 'HR_Comments'] = row['HR_Comments']
                        current_df.loc[mask, 'OPS_comments'] = row['OPS_comments']
                        current_df.loc[mask, 'Regrettable Y/N'] = row['Regrettable Y/N']

                # Ensure columns match display_cols (excluding 'SR.No.' and 'Delete')
                save_cols = [col for col in display_cols if col not in ['SR.No.', 'Delete']]
                current_df = current_df[save_cols]
                # st.write("Saving this DataFrame to Google Sheet:", current_df.head())
                # st.write("Columns:", current_df.columns.tolist())

                # Save back to Google Sheet
                if update_sheet_data(SPREADSHEET_ID, TRACKING_SHEET_RANGE, current_df):
                    st.session_state.action_message = "Comments saved successfully!"
                    st.session_state.action_message_type = "success"
                    time.sleep(2)
                    # st.rerun()
                else:
                    st.error("Failed to save comments to Google Sheet")
            except Exception as e:
                st.session_state.action_message = f"Error saving comments: {str(e)}"
                st.session_state.action_message_type = "error"
                # st.rerun()

    with col_delete:
        if st.button("Delete Selected"):
            try:
                # Get the current data from Google Sheet
                current_df = get_sheet_data(SPREADSHEET_ID, TRACKING_SHEET_RANGE)
                if current_df is None:
                    st.error("Error loading current data from Google Sheet")
                    st.stop()
                
                # Convert Date of Report Generation to datetime for comparison
                current_df['Date of Report Generation'] = pd.to_datetime(current_df['Date of Report Generation'])
                edited_df['Date of Report Generation'] = pd.to_datetime(edited_df['Date of Report Generation'])
                
                # Find rows to delete
                to_delete = edited_df[edited_df['Delete']]
                if not to_delete.empty:
                    # Create a mask for rows to keep
                    mask = pd.Series(True, index=current_df.index)
                    for _, row in to_delete.iterrows():
                        delete_mask = (
                            (current_df['Employee ID'] == row['Employee ID']) &
                            (current_df['Date of Report Generation'] == row['Date of Report Generation'])
                        )
                        mask = mask & ~delete_mask
                    
                    # Keep only rows that weren't marked for deletion
                    current_df = current_df[mask]
                    
                    # Convert timestamp to string format before saving
                    current_df['Date of Report Generation'] = current_df['Date of Report Generation'].dt.strftime('%Y-%m-%d')
                    
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
