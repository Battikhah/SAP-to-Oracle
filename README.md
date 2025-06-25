# SAP to Oracle Data Transformation Tool

## Overview

This Python tool transforms SAP/SAM approval workflow data into Oracle ERP-compatible format, automatically mapping approval hierarchies and threshold amounts across different approval levels.

## Key Features

### 🔄 **Automated Data Transformation**

- Converts SAP approval data to Oracle import format
- Processes both General and Research approval workflows
- Handles multiple approval levels (1-7) with predefined thresholds

### 👥 **Role-Based Processing**

- **Reviewers**: Handles review-only roles with appropriate threshold mapping
- **Approvers**: Creates approval hierarchy with amount-based levels

### 💰 **Smart Threshold Mapping**

- **Level 1**: $1 - $1,000.99
- **Level 2**: $1,001 - $5,000.99
- **Level 3**: $5,001 - $10,000.99
- **Level 4**: $10,001 - $25,000.99
- **Level 5**: $25,001 - $100,000.99
- **Level 6**: $100,001 - $1,000,000.99
- **Level 7**: $1,000,001 - $99,999,999.99

### 🧹 **Data Cleaning**

- Automatically detects and maps column names
- Handles missing data and formatting inconsistencies
- Converts currency amounts and removes formatting characters

## Input Requirements

### Expected Excel File Structure

Your input file should contain sheets named "General" and/or "Research" with columns containing:

- Cost Center information
- Oracle ID
- Threshold amounts (From/To)
- Role designation (Reviewer/Approver)

### Supported Input Formats

The tool automatically detects columns with names containing:

- "cost center" → Cost Center
- "oracle id" → Oracle User ID
- "threshold from" → Lower threshold amount
- "threshold to" → Upper threshold amount
- "role" or "type" → User role designation

## Usage

### Basic Usage

```python
python SAP_to_Oracle.py
```

### Preview Mode

The tool automatically shows a preview before full transformation:

```python
preview_transformation("Files/Raw Data.xlsx", num_rows=3)
```

### Programmatic Usage

```python
from SAP_to_Oracle import transform_sam_to_oracle

# Transform your data
success = transform_sam_to_oracle("your_input_file.xlsx")
```

## Output Files

The tool generates separate Oracle-compatible files:

- `Oracle_Import_General.xlsx` - General approval workflows
- `Oracle_Import_Research.xlsx` - Research approval workflows

### Output Schema

| Column                | Description               |
| --------------------- | ------------------------- |
| Cost Center           | Original cost center code |
| Level                 | Approval level (1-7)      |
| Type                  | Always "Employee"         |
| Role                  | REVIEWER or APPROVER      |
| Oracle ID             | User's Oracle system ID   |
| Threshold Amount From | Lower bound for approval  |
| Threshold Amount To   | Upper bound for approval  |

## Data Processing Logic

### For Reviewers

- Dash ("-") values → Converted to 0
- Creates review entries without approval authority
- Maps to appropriate levels based on review thresholds

### For Approvers

- Dash ("-") values → Converted to 1 (minimum approval amount)
- Full range approvers → Creates entries for all 7 levels
- Specific range approvers → Maps to overlapping approval levels

## Dependencies

```
pandas>=1.3.0
openpyxl>=3.0.0
```

## Installation

```bash
pip install pandas openpyxl
```

## Error Handling

- Validates input file existence
- Checks for required columns
- Handles missing or malformed data
- Provides detailed error messages and processing logs

## Example Transformation

**Input (SAP Format):**
| Cost Center | Oracle ID | Threshold From | Threshold To | Role |
|-------------|-----------|----------------|--------------|------|
| CC001 | user123 | 1 | 99999999 | Approver |
| CC002 | user456 | - | - | Reviewer |

**Output (Oracle Format):**
| Cost Center | Level | Type | Role | Oracle ID | Threshold Amount From | Threshold Amount To |
|-------------|-------|------|------|-----------|---------------------|-------------------|
| CC001 | 1 | Employee | APPROVER | user123 | 1 | 1000.99 |
| CC001 | 2 | Employee | APPROVER | user123 | 1001 | 5000.99 |
| ... | ... | ... | ... | ... | ... | ... |
| CC002 | | Employee | REVIEWER | user456 | | |
