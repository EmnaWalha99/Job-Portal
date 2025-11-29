import pandas as pd

df = pd.read_csv(r"C:\Users\marie\OneDrive\Desktop\Job_Portal\job_emploisTunisie.csv")
df.to_excel(r"C:\Users\marie\OneDrive\Desktop\Job_Portal\emploisTunisie.xlsx", index=False)