import pandas as pd
from sklearn.preprocessing import MinMaxScaler, LabelEncoder

# 读取数据集
file_path = r"C:\Users\18344\Desktop\机器学习模型实战\分类模型实战演示\附件\heart.csv"
df = pd.read_csv(file_path)

# 1. 识别缺失值
print("缺失值检查:")
print(df.isnull().sum())

# 填补缺失值（用均值填补数值型变量）
df['RestingBP'] = df['RestingBP'].fillna(df['RestingBP'].mean())
df['Cholesterol'] = df['Cholesterol'].fillna(df['Cholesterol'].mean())
df['MaxHR'] = df['MaxHR'].fillna(df['MaxHR'].mean())


# 再次检查是否存在缺失值
print("\n填补缺失值后缺失值检查:")
print(df.isnull().sum())

# 2. 异常值处理
# 使用IQR法处理异常值
Q1 = df[['RestingBP', 'Cholesterol', 'MaxHR']].quantile(0.25)
Q3 = df[['RestingBP', 'Cholesterol', 'MaxHR']].quantile(0.75)
IQR = Q3 - Q1

# 定义异常值的范围
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

# 去除异常值

df['RestingBP'] = df['RestingBP'].fillna(df['RestingBP'].mean())
df['Cholesterol'] = df['Cholesterol'].fillna(df['Cholesterol'].mean())
df['MaxHR'] = df['MaxHR'].fillna(df['MaxHR'].mean())


print("\n数据去除异常值后的样本数:", df.shape[0])

# 3. 处理重复值
print("\n重复值检查:")
print(df.duplicated().sum())

# 删除重复值
df = df.drop_duplicates()

print("\n删除重复值后的样本数:", df.shape[0])

# 4. 极差标准化：对RestingBP, Cholesterol, MaxHR进行标准化
scaler = MinMaxScaler()
df[['RestingBP', 'Cholesterol', 'MaxHR']] = scaler.fit_transform(df[['RestingBP', 'Cholesterol', 'MaxHR']])

# 5. 标签编码：对分类特征进行标签编码
label_columns = ['Sex', 'ChestPainType', 'ExerciseAngina', 'RestingECG', 'ST_Slope']
le = LabelEncoder()

for col in label_columns:
    df[col] = le.fit_transform(df[col])

# 输出预处理后的数据集
print("\n数据预处理后的前5行数据:")
print(df.head())

# 保存预处理后的数据集
output_path = r"C:\Users\18344\Desktop\机器学习模型实战\分类模型实战演示\分类模型实战\code\heart_preprocessed.csv"
df.to_csv(output_path, index=False)

print(f"\n预处理后的数据集已保存至：{output_path}")
