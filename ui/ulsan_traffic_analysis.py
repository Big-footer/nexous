# 울산 교통량 데이터 분석 프로그램

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


def load_data(file_path):
    """Load traffic data from a CSV file."""
    return pd.read_csv(file_path)


def preprocess_data(df):
    """Preprocess the traffic data."""
    df['date'] = pd.to_datetime(df['date'])
    df = df.dropna()
    return df


def analyze_data(df):
    """Analyze the traffic data."""
    daily_traffic = df.groupby(df['date'].dt.date).sum()
    return daily_traffic


def visualize_data(daily_traffic):
    """Visualize the traffic data."""
    plt.figure(figsize=(10, 6))
    sns.lineplot(data=daily_traffic, x=daily_traffic.index, y='traffic_count')
    plt.title('Daily Traffic Volume')
    plt.xlabel('Date')
    plt.ylabel('Traffic Count')
    plt.show()


# Example usage
# df = load_data('ulsan_traffic_data.csv')
# df = preprocess_data(df)
# daily_traffic = analyze_data(df)
# visualize_data(daily_traffic)

# 이 프로그램은 울산 지역 교통량 데이터를 분석하는 데 사용됩니다. 다른 지역 데이터에도 응용 가능합니다.