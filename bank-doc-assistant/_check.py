import pandas as pd
from pathlib import Path
df = pd.read_csv(Path(__file__).parent / "data" / "dataset.csv")
print("Columns:", list(df.columns))
print("Shape:", df.shape)
print(df.head(2).to_string())
