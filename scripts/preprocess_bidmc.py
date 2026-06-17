import wfdb
import os
import pandas as pd
import numpy as np

print("Preprocessing BIDMC Numerics Dataset...")

data_dir = "../data/raw/physionet_bidmc"
output_file = "../data/raw/bidmc_vitals.csv"

# We will collect records and map them to our canonical schema
all_records = []

for record_num in range(1, 11):
    record_name = f"bidmc{record_num:02d}n"
    try:
        # Download and read numeric record directly from PhysioNet
        record = wfdb.rdrecord(record_name, pn_dir='bidmc')
        
        sig_names = [s.strip(',') for s in record.sig_name]
        
        # Create a dataframe for this patient
        df = pd.DataFrame(record.p_signal, columns=sig_names)
        
        # Map to Canonical Schema
        mapped_df = pd.DataFrame()
        mapped_df['heart_rate'] = df['HR'] if 'HR' in df.columns else 0.0
        mapped_df['spo2'] = df['SpO2'] if 'SpO2' in df.columns else 0.0
        
        # BIDMC numerics usually lack Temp/BP, handle missingness explicitly with NaN
        mapped_df['temperature'] = np.nan
        mapped_df['systolic_bp'] = np.nan
        mapped_df['diastolic_bp'] = np.nan
        
        mapped_df['patient_id'] = f"P_{record_num}"
        
        # Explicit deterministic label generation based on WHO rules (Layer 2 Simulation)
        conditions = [
            (mapped_df['spo2'] < 92) & (mapped_df['spo2'] > 0),
            (mapped_df['heart_rate'] > 120),
            (mapped_df['spo2'] < 95) & (mapped_df['spo2'] >= 92)
        ]
        choices = ['critical', 'warning', 'warning']
        mapped_df['health_status'] = np.select(conditions, choices, default='normal')
        
        all_records.append(mapped_df)
        print(f"✓ Processed record {record_num}")
    except Exception as e:
        print(f"✗ Error processing record {record_num}: {e}")

if all_records:
    final_df = pd.concat(all_records, ignore_index=True)
    # Drop rows where HR or SpO2 is missing (NaN or 0)
    final_df = final_df.dropna(subset=['heart_rate', 'spo2'])
    final_df = final_df[(final_df['heart_rate'] > 0) & (final_df['spo2'] > 0)]
    final_df.to_csv(output_file, index=False)
    print(f"BIDMC preprocessing complete! Saved to {output_file}")
    print(f"Total readings: {len(final_df)}")
else:
    print("No records processed.")
