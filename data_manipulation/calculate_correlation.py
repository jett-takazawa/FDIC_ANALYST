import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Load your data (adjust path as needed)
df = pd.read_json('data_2014_with_cagr.json')

# 2. Drop zipcode & year
df_num = df.drop(columns=['zipCode', 'year'])

# 3. Compute the Pearson correlation matrix
corr_matrix = df_num.corr()
print(corr_matrix.round(2))
corr_matrix.to_csv('corr_matrix.csv')

"""
# 4. Plot
plt.figure(figsize=(25, 18))
sns.heatmap(corr_matrix, center=0, cmap='vlag', annot=False)
plt.title('Correlation matrix of all numeric variables')
plt.tight_layout()
plt.show()
"""



