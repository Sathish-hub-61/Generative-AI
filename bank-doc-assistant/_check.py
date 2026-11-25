import pandas as pd
df = pd.read_csv(r"C:\Generative AI\bank-doc-assistant\data\dataset.csv")
print("Columns:", list(df.columns))
print("Shape:", df.shape)
print(df.head(2).to_string())
