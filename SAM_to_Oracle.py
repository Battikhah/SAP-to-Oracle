import pandas as pd
import re

def clean_amount(amount_str, role=None):
    """
    Clean amount string by removing spaces, commas, and converting to float
    Handle "-" differently based on role:
    - Reviewers: "-" becomes 0 (or null)
    - Approvers: "-" becomes 1
    """
    if pd.isna(amount_str) or str(amount_str).strip() == '-':
        if role and 'reviewer' in role.lower():
            return 0  # Reviewers get 0 for "-"
        else:
            return 1  # Approvers get 1 for "-"
    
    # Remove spaces, commas, and other formatting
    cleaned = str(amount_str).replace(' ', '').replace(',', '').replace('"', '').strip()
    
    try:
        return float(cleaned)
    except ValueError:
        # If can't parse, use same logic as "-"
        if role and 'reviewer' in role.lower():
            return 0
        else:
            return 1

def transform_sheet_to_oracle(df, sheet_name):
    """
    Transform a single sheet's data to Oracle format
    """
    
    # Define the approval level thresholds
    approval_levels = [
        {"level": 1, "amount_from": 1, "amount_to": 1000.99},
        {"level": 2, "amount_from": 1001.00, "amount_to": 5000.99},
        {"level": 3, "amount_from": 5001.00, "amount_to": 10000.99},
        {"level": 4, "amount_from": 10001.00, "amount_to": 25000.99},
        {"level": 5, "amount_from": 25001.00, "amount_to": 100000.99},
        {"level": 6, "amount_from": 100001.00, "amount_to": 1000000.99},
        {"level": 7, "amount_from": 1000001.00, "amount_to": 99999999.99}
    ]
    
    # Clean column names (remove extra spaces)
    df.columns = df.columns.str.strip()
    
    print(f"\n{sheet_name} Sheet - Column names found:", df.columns.tolist())
    print(f"{sheet_name} Sheet - First few rows:")
    print(df.head())
    
    # Try to identify the correct column names based on common patterns
    cost_center_col = None
    oracle_id_col = None
    threshold_from_col = None
    threshold_to_col = None
    role_col = None
    
    for col in df.columns:
        col_lower = col.lower()
        if 'cost' in col_lower and 'center' in col_lower:
            cost_center_col = col
        elif 'oracle' in col_lower and 'id' in col_lower:
            oracle_id_col = col
        elif 'threshold' in col_lower and 'from' in col_lower:
            threshold_from_col = col
        elif 'threshold' in col_lower and ('to' in col_lower or 'too' in col_lower):
            threshold_to_col = col
        elif 'role' in col_lower or 'type' in col_lower:
            role_col = col
    
    print(f"{sheet_name} Sheet - Identified columns:")
    print(f"  Cost Center: {cost_center_col}")
    print(f"  Oracle ID: {oracle_id_col}")
    print(f"  Threshold From: {threshold_from_col}")
    print(f"  Threshold To: {threshold_to_col}")
    print(f"  Role: {role_col}")
    
    # If we couldn't auto-identify required columns, let user know the available columns
    if not all([cost_center_col, oracle_id_col, threshold_from_col, threshold_to_col]):
        print(f"\n{sheet_name} Sheet - Could not automatically identify all required columns.")
        print("Available columns:", df.columns.tolist())
        return None
    
    # Remove rows where essential columns are empty
    df = df.dropna(subset=[cost_center_col, oracle_id_col], how='all')
    
    # Create list to store transformed rows
    transformed_rows = []
    
    for index, row in df.iterrows():
        cost_center = row[cost_center_col]
        oracle_id = row[oracle_id_col]
        
        # Get role if available
        role = row[role_col] if role_col else 'Approver'  # Default to Approver
        
        # Clean amounts based on role
        threshold_from = clean_amount(row[threshold_from_col], role)
        threshold_to = clean_amount(row[threshold_to_col], role)
        
        # Skip rows with missing essential data
        if pd.isna(cost_center) or pd.isna(oracle_id):
            continue
            
        print(f"{sheet_name} - Processing: Cost Center={cost_center}, Oracle ID={oracle_id}, Role={role}, From={threshold_from}, To={threshold_to}")
        
        # Determine if this person is a reviewer or approver
        is_reviewer = role and 'reviewer' in str(role).lower()
        
        if is_reviewer:
            # For reviewers with 0 thresholds, create a single entry with 0 amounts
            if threshold_from == 0 and threshold_to == 0:
                new_row = {
                    'Cost Center': cost_center,
                    'Level': 1,  # Reviewers typically get level 1
                    'Type': 'Employee',
                    'Role': 'REVIEWER',
                    'Oracle ID': oracle_id,
                    'Threshold Amount From': 0,
                    'Threshold Amount To': 0
                }
                transformed_rows.append(new_row)
                print(f"  Added reviewer entry: 0 - 0")
            else:
                # For reviewers with specific thresholds, map to appropriate levels
                for level_info in approval_levels:
                    range_start = max(threshold_from, level_info['amount_from'])
                    range_end = min(threshold_to, level_info['amount_to'])
                    
                    if range_start <= range_end:
                        new_row = {
                            'Cost Center': cost_center,
                            'Level': level_info['level'],
                            'Type': 'Employee',
                            'Role': 'REVIEWER',
                            'Oracle ID': oracle_id,
                            'Threshold Amount From': range_start,
                            'Threshold Amount To': range_end
                        }
                        transformed_rows.append(new_row)
                        print(f"  Added reviewer level {level_info['level']}: {range_start} - {range_end}")
        else:
            # For approvers - existing logic
            # Check if this is a full range case (from 1 to very high amount)
            is_full_range = (
                threshold_from == 1 and threshold_to >= 99999999
            )
            
            if is_full_range:
                # Create 7 rows, one for each approval level
                for level_info in approval_levels:
                    new_row = {
                        'Cost Center': cost_center,
                        'Level': level_info['level'],
                        'Type': 'Employee',
                        'Role': 'APPROVER',
                        'Oracle ID': oracle_id,
                        'Threshold Amount From': level_info['amount_from'],
                        'Threshold Amount To': level_info['amount_to']
                    }
                    transformed_rows.append(new_row)
                    print(f"  Added approver level {level_info['level']}: {level_info['amount_from']} - {level_info['amount_to']}")
            else:
                # For specific ranges, determine which level(s) they fall into
                for level_info in approval_levels:
                    # Check if the threshold range overlaps with this approval level
                    range_start = max(threshold_from, level_info['amount_from'])
                    range_end = min(threshold_to, level_info['amount_to'])
                    
                    if range_start <= range_end:
                        new_row = {
                            'Cost Center': cost_center,
                            'Level': level_info['level'],
                            'Type': 'Employee', 
                            'Role': 'APPROVER',
                            'Oracle ID': oracle_id,
                            'Threshold Amount From': range_start,
                            'Threshold Amount To': range_end
                        }
                        transformed_rows.append(new_row)
                        print(f"  Added approver level {level_info['level']}: {range_start} - {range_end}")
    
    # Create DataFrame from transformed rows
    result_df = pd.DataFrame(transformed_rows)
    
    if len(result_df) == 0:
        print(f"{sheet_name} Sheet - No data was transformed. Please check your input file format.")
        return None
    
    # Sort by Cost Center and Level for better organization
    result_df = result_df.sort_values(['Cost Center', 'Oracle ID', 'Level'])
    
    print(f"{sheet_name} Sheet - Transformation complete!")
    print(f"  Original rows: {len(df)}")
    print(f"  Transformed rows: {len(result_df)}")
    
    return result_df

def transform_sam_to_oracle(input_file):
    """
    Transform SAM data to Oracle format for both General and Research sheets
    """
    
    try:
        # Read all sheets from the Excel file
        excel_file = pd.ExcelFile(input_file)
        print("Available sheets:", excel_file.sheet_names)
        
        # Process General sheet
        if 'General' in excel_file.sheet_names:
            print("\n" + "="*60)
            print("PROCESSING GENERAL SHEET")
            print("="*60)
            
            general_df = pd.read_excel(input_file, sheet_name='General')
            general_result = transform_sheet_to_oracle(general_df, 'General')
            
            if general_result is not None:
                general_output = "Oracle_Import_General.xlsx"
                general_result.to_excel(general_output, index=False)
                print(f"General sheet saved to: {general_output}")
            else:
                print("Failed to process General sheet")
        else:
            print("Warning: 'General' sheet not found")
        
        # Process Research sheet
        if 'Research' in excel_file.sheet_names:
            print("\n" + "="*60)
            print("PROCESSING RESEARCH SHEET")
            print("="*60)
            
            research_df = pd.read_excel(input_file, sheet_name='Research')
            research_result = transform_sheet_to_oracle(research_df, 'Research')
            
            if research_result is not None:
                research_output = "Oracle_Import_Research.xlsx"
                research_result.to_excel(research_output, index=False)
                print(f"Research sheet saved to: {research_output}")
            else:
                print("Failed to process Research sheet")
        else:
            print("Warning: 'Research' sheet not found")
            
        return True
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def preview_transformation(input_file, num_rows=3):
    """
    Preview the transformation for both sheets without saving to file
    """
    try:
        excel_file = pd.ExcelFile(input_file)
        print("Available sheets:", excel_file.sheet_names)
        
        # Preview General sheet
        if 'General' in excel_file.sheet_names:
            print("\n" + "="*50)
            print("GENERAL SHEET PREVIEW")
            print("="*50)
            general_df = pd.read_excel(input_file, sheet_name='General')
            print("Original General data:")
            print(general_df.head(num_rows))
            
            general_result = transform_sheet_to_oracle(general_df, 'General')
            if general_result is not None:
                print("\nTransformed General data preview:")
                print(general_result.head(10))
        
        # Preview Research sheet
        if 'Research' in excel_file.sheet_names:
            print("\n" + "="*50)
            print("RESEARCH SHEET PREVIEW")
            print("="*50)
            research_df = pd.read_excel(input_file, sheet_name='Research')
            print("Original Research data:")
            print(research_df.head(num_rows))
            
            research_result = transform_sheet_to_oracle(research_df, 'Research')
            if research_result is not None:
                print("\nTransformed Research data preview:")
                print(research_result.head(10))
                
    except Exception as e:
        print(f"Error during preview: {str(e)}")
        import traceback
        traceback.print_exc()

# Example usage
if __name__ == "__main__":
    # Use your actual Excel file
    input_filename = "Raw Data.xlsx"
    
    try:
        # Preview the transformation first
        print("Previewing transformation for both sheets...")
        preview_transformation(input_filename, 3)
        
        print("\n" + "="*80)
        print("PERFORMING FULL TRANSFORMATION")
        print("="*80)
        
        success = transform_sam_to_oracle(input_filename)
        
        if success:
            print("\n" + "="*60)
            print("TRANSFORMATION COMPLETE!")
            print("="*60)
            print("Files created:")
            print("  - Oracle_Import_General.xlsx")
            print("  - Oracle_Import_Research.xlsx")
            print("\nRole handling:")
            print("  - Reviewers: '-' converted to 0")
            print("  - Approvers: '-' converted to 1")
        else:
            print("Transformation failed. Please check the error messages above.")
        
    except FileNotFoundError:
        print(f"Error: Could not find {input_filename}")
        print("Please make sure your Excel file is in the same directory as this script.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()