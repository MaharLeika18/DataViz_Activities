import pandas as pd
import sys
import os

def quarantine(df, mask, reason, quarantine_list):
    if mask.any():
        flagged = df[mask].copy()
        flagged['quarantine_reason'] = reason
        quarantine_list.append(flagged)
    return df[~mask]

# load csv file
filepath = input("Enter filename of csv file to be cleaned: ")

try:
    full_path = os.path.join(os.getcwd(), filepath)
    df = pd.read_csv(full_path)
    print(f"Loaded '{filepath}' successfully.")
except:
    print(f"File '{filepath}' could not be found in '{os.getcwd()}'. Please try again.")
    sys.exit()

# verify column names
expected_columns = ['transaction_id', 'cust_name', 'region', 'order_date', 'amount_paid', 'status']

df.columns = df.columns.str.lower()

if set(expected_columns).issubset(df.columns):
    print("All expected columns are present.")
else:
    missing = set(expected_columns) - set(df.columns)
    print(f"File is missing the following columns: {missing}. Please try again.")
    sys.exit()

print(f"\nReady for cleaning. Received dataset:\n\n{df}")

quarantine_records = []

# drop duplicates
dup_mask = df.duplicated(keep='first') 
df = quarantine(df, dup_mask, 'duplicate_record', quarantine_records)

# drop invalid amount values
raw_amount = df['amount_paid']
numeric_amount = pd.to_numeric(raw_amount, errors='coerce')
corrupted_amount_mask = numeric_amount.isna() & raw_amount.notna()  
df = quarantine(df, corrupted_amount_mask, 'invalid_amount_paid_format', quarantine_records)

# impute missing amount values
df['amount_paid'] = pd.to_numeric(df['amount_paid'], errors='coerce')
df['amount_paid'] = df['amount_paid'].fillna(df['amount_paid'].median()) 

# label missing names
df['cust_name'] = df['cust_name'].fillna('Unknown')

# mapping dictionary
region_mapping = {
    'NCR': 'National Capital Region',
    'Metro Manila': 'National Capital Region',
    'metro manila': 'National Capital Region',
    'ncr': 'National Capital Region',
    'calabarzon': 'Region IV-A',
    'CALABARZON': 'Region IV-A',
    'CaLaBaRZon': 'Region IV-A',
    'region iv-a': 'Region IV-A'
}

df['region'] = df['region'].replace(region_mapping)

# convert order_date
df['order_date'] = df['order_date'].str.replace("-", "/", regex=False)
df['order_date'] = pd.to_datetime(df['order_date'], format='%Y/%m/%d',errors='coerce')

invalid_date_mask = df['order_date'].isna()
df = quarantine(df, invalid_date_mask, 'invalid_order_date', quarantine_records)

# write quarantine log
if quarantine_records:
    quarantine_df = pd.concat(quarantine_records, ignore_index=True)
    quarantine_df.to_csv('quarantined_transactions.csv', index=False)
    print(f"\n{len(quarantine_df)} record(s) quarantined. Saved to 'quarantined_transactions.csv'")
    print(quarantine_df['quarantine_reason'].value_counts().to_string())
else:
    print("\nNo records required quarantining.")

# confirm and export to csv
print(f"\nData cleaning complete. Cleaned dataset:\n\n{df}\n")

while True:
    confirm = input("Save the cleaned file? Y/N: ").strip().lower()
    if confirm in ('y', 'yes'):
        out_name = input("Enter output filename (e.g. cleaned.csv): ").strip()
        df.to_csv(out_name, index=False)
        print(f"File saved as '{out_name}'.")
        break
    elif confirm in ('n', 'no'):
        print("File not saved.")
        break
    else:
        print("Please enter 'y' or 'n'.")