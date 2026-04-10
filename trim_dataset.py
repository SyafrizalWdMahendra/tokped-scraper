import pandas as pd

df = pd.read_csv('new_final_dataset.csv')

df_pos = df[df['Sentiment'] == 'positif']
df_neg = df[df['Sentiment'] == 'negatif']
df_net = df[df['Sentiment'] == 'netral']

target_count = len(df_neg) + len(df_net)

df_pos_trimmed = df_pos.sample(n=target_count, random_state=42)

df_final = pd.concat([df_pos_trimmed, df_neg, df_net])

df_final = df_final.sample(frac=1, random_state=42).reset_index(drop=True)

df_final.to_csv('trimmed_sentiment_dataset.csv', index=False)