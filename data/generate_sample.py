"""生成示例销售数据 data/sample.csv"""
import random
from pathlib import Path

import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

BASE_DIR = Path(__file__).resolve().parent
OUT_FILE = BASE_DIR / "sample.csv"

# 维度定义
REGIONS = {
    "华东": ["上海", "杭州", "南京", "苏州"],
    "华北": ["北京", "天津", "石家庄"],
    "华南": ["广州", "深圳", "厦门"],
    "西南": ["成都", "重庆", "昆明"],
    "华中": ["武汉", "长沙", "郑州"],
}

CATEGORIES = {
    "电子产品": [("笔记本电脑", 5500), ("手机", 3800), ("平板", 2600), ("显示器", 1200)],
    "家具":     [("办公桌", 800), ("人体工学椅", 1500), ("书柜", 600), ("沙发", 3000)],
    "办公用品": [("打印纸", 35), ("签字笔", 5), ("文件夹", 12), ("订书机", 25)],
}

CUSTOMERS = [
    "张三", "李四", "王五", "赵六", "钱七", "孙八", "周九", "吴十",
    "北京华信", "上海智远", "深圳云端", "成都天启", "广州盛达", "杭州锐意",
]

N_ROWS = 500
START = pd.Timestamp("2024-01-01")
END = pd.Timestamp("2024-12-31")

# 生成数据
rows = []
for i in range(N_ROWS):
    region = random.choice(list(REGIONS.keys()))
    city = random.choice(REGIONS[region])
    category = random.choice(list(CATEGORIES.keys()))
    product, base_price = random.choice(CATEGORIES[category])

    # 单价在基准价上下浮动 10%
    unit_price = round(base_price * random.uniform(0.9, 1.1), 2)
    quantity = random.randint(1, 20)
    amount = round(unit_price * quantity, 2)

    order_date = START + pd.Timedelta(days=random.randint(0, (END - START).days))
    # 让销售额有季节性：Q4 略高
    if order_date.month in (10, 11, 12):
        amount = round(amount * 1.15, 2)

    rows.append({
        "order_id": f"ORD{20240000 + i + 1}",
        "order_date": order_date.strftime("%Y-%m-%d"),
        "region": region,
        "city": city,
        "category": category,
        "product": product,
        "quantity": quantity,
        "unit_price": unit_price,
        "amount": amount,
        "customer": random.choice(CUSTOMERS),
    })

df = pd.DataFrame(rows).sort_values("order_date").reset_index(drop=True)
df.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")

print(f"已生成: {OUT_FILE}")
print(f"行数:   {len(df)}")
print(f"列:     {list(df.columns)}")
print("\n前 5 行预览:")
print(df.head().to_string(index=False))
print("\n销售额基本统计:")
print(df["amount"].describe().round(2).to_string())