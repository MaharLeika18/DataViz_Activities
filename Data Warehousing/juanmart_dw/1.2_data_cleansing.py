import pandas as pd
import sys
import os

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

# drop 15 dupes
dup_mask = df.duplicated(keep='first') 
dup_indices = df[dup_mask].index[:15]
df = df.drop(index=dup_indices)

# fill missing records
df['amount_paid'] = df['amount_paid'].fillna(df['amount_paid'].median())
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

