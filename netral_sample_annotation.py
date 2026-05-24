import pandas as pd

# Load the dataset
df = pd.read_csv('robust_data/dataset/trimmed_sentiment_dataset.csv')

# Filter for 'netral' sentiment
netral_df = df[df['Sentiment'] == 'netral']

# Sample 250 rows (or all if less than 250)
num_samples = min(250, len(netral_df))
sampled_netral = netral_df.sample(n=num_samples, random_state=42)

# Save to Excel
output_filename = 'netral_samples_for_annotation.xlsx'
sampled_netral.to_excel(output_filename, index=False)

print(f"Saved {num_samples} rows to {output_filename}")