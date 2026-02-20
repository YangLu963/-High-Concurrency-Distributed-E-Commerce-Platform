from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd

# Feast核心组件
from feast import (
    Entity,
    Feature,
    FeatureView,
    Field,
    FileSource,
    KafkaSource,
    PushSource,
    FeatureService,
    ValueType
)
from feast.types import Float32, Int32, String, Array, Bool
from feast.data_format import ParquetFormat, AvroFormat
from feast.infra.offline_stores.file_source import FileSource
from feast.infra.online_stores.redis import RedisOnlineStoreConfig

# 定义实体
user = Entity(
    name="user_id",
    value_type=ValueType.STRING,
    description="User identifier",
    join_keys=["user_id"],
)

item = Entity(
    name="item_id",
    value_type=ValueType.STRING,
    description="Item identifier",
    join_keys=["item_id"],
)

# 定义数据源

# 1. 离线数据源（来自Spark ETL的Parquet文件）
user_profile_source = FileSource(
    name="user_profile_source",
    path="s3://feature-store/user-profiles/",
    file_format=ParquetFormat(),
    timestamp_field="event_timestamp",
    created_timestamp_column="created_timestamp",
)

user_stats_source = FileSource(
    name="user_stats_source",
    path="s3://feature-store/user-stats/",
    file_format=ParquetFormat(),
    timestamp_field="event_timestamp",
)

item_stats_source = FileSource(
    name="item_stats_source",
    path="s3://feature-store/item-stats/",
    file_format=ParquetFormat(),
    timestamp_field="event_timestamp",
)

# 2. 实时数据源（来自Kafka）
behavior_stream_source = KafkaSource(
    name="behavior_stream",
    kafka_bootstrap_servers="localhost:9092",
    topic="user-behavior",
    timestamp_field="event_timestamp",
    message_format=AvroFormat(
        schema_json="""
        {
            "type": "record",
            "name": "UserBehavior",
            "fields": [
                {"name": "user_id", "type": "string"},
                {"name": "item_id", "type": "string"},
                {"name": "action", "type": "string"},
                {"name": "event_timestamp", "type": "long"}
            ]
        }
        """
    ),
)

# 定义特征视图

# 用户画像特征（每天更新）
user_profile_fv = FeatureView(
    name="user_profile_features",
    entities=[user],
    ttl=timedelta(days=30),
    schema=[
        Field(name="total_clicks", dtype=Int32),
        Field(name="total_purchases", dtype=Int32),
        Field(name="avg_dwell_time", dtype=Float32),
        Field(name="unique_items_viewed", dtype=Int32),
        Field(name="peak_hour", dtype=Int32),
        Field(name="user_segment", dtype=String),
        Field(name="top_categories", dtype=Array(String)),
    ],
    source=user_profile_source,
    online=True,
    tags={"team": "recommendation", "type": "profile"},
)

# 用户统计特征（每小时更新）
user_stats_fv = FeatureView(
    name="user_statistical_features",
    entities=[user],
    ttl=timedelta(days=7),
    schema=[
        Field(name="click_7d_avg", dtype=Float32),
        Field(name="purchase_30d_total", dtype=Int32),
        Field(name="active_days_30d", dtype=Int32),
        Field(name="category_entropy", dtype=Float32),
        Field(name="session_avg_duration", dtype=Float32),
    ],
    source=user_stats_source,
    online=True,
)

# 实时行为特征（近实时更新）
realtime_user_fv = FeatureView(
    name="user_realtime_features",
    entities=[user],
    ttl=timedelta(hours=24),
    schema=[
        Field(name="click_count_5min", dtype=Int32),
        Field(name="purchase_count_5min", dtype=Int32),
        Field(name="ctr_5min", dtype=Float32),
        Field(name="recent_items", dtype=Array(String)),
        Field(name="current_session_items", dtype=Array(String)),
    ],
    source=behavior_stream_source,
    online=True,
    tags={"type": "realtime"},
)

# 物品统计特征
item_stats_fv = FeatureView(
    name="item_statistical_features",
    entities=[item],
    ttl=timedelta(days=7),
    schema=[
        Field(name="total_clicks", dtype=Int32),
        Field(name="total_purchases", dtype=Int32),
        Field(name="purchase_rate", dtype=Float32),
        Field(name="popularity_score", dtype=Float32),
        Field(name="avg_dwell_time", dtype=Float32),
    ],
    source=item_stats_source,
    online=True,
)

# 定义特征服务（供在线推理使用）
recommendation_feature_service = FeatureService(
    name="recommendation_features",
    features=[
        user_profile_fv,
        user_stats_fv,
        realtime_user_fv,
        item_stats_fv,
    ],
    tags={"release": "production"},
)

# 定义训练数据集
from feast.infra.offline_stores.file_source import SavedDataset

class FeatureStoreRepo:
    """Feast仓库管理"""

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path

    def apply(self):
        """应用特征定义"""
        from feast import FeatureStore

        store = FeatureStore(repo_path=self.repo_path)
        store.apply([
            user,
            item,
            user_profile_fv,
            user_stats_fv,
            realtime_user_fv,
            item_stats_fv,
            recommendation_feature_service
        ])

        print("Feature definitions applied successfully")

    def get_training_data(self, entity_df: pd.DataFrame,
                          features: List[str] = None) -> pd.DataFrame:
        """获取训练数据"""
        from feast import FeatureStore

        store = FeatureStore(repo_path=self.repo_path)

        if features is None:
            features = [
                "user_profile_features:total_clicks",
                "user_profile_features:total_purchases",
                "user_profile_features:avg_dwell_time",
                "user_statistical_features:click_7d_avg",
                "user_statistical_features:purchase_30d_total",
                "item_statistical_features:purchase_rate",
                "item_statistical_features:popularity_score"
            ]

        training_df = store.get_historical_features(
            entity_df=entity_df,
            features=features,
        ).to_df()

        return training_df

    def get_online_features(self, entity_rows: List[Dict]) -> Dict:
        """获取在线特征（实时推理用）"""
        from feast import FeatureStore

        store = FeatureStore(repo_path=self.repo_path)

        feature_refs = [
            "user_profile_features:total_clicks",
            "user_profile_features:user_segment",
            "user_realtime_features:click_count_5min",
            "user_realtime_features:recent_items",
        ]

        features = store.get_online_features(
            features=feature_refs,
            entity_rows=entity_rows,
        ).to_dict()

        return features

    def push_events_to_stream(self, events: List[Dict]):
        """推送实时事件到流"""
        from feast import FeatureStore

        store = FeatureStore(repo_path=self.repo_path)

        # 将事件推送到PushSource（如果有配置）
        store.push(
            push_source_name="behavior_push_source",
            df=pd.DataFrame(events),
        )

    def materialize(self, start_date: datetime, end_date: datetime):
        """物化特征到在线存储"""
        from feast import FeatureStore

        store = FeatureStore(repo_path=self.repo_path)

        store.materialize(
            start_date=start_date,
            end_date=end_date,
            feature_views=[
                "user_profile_features",
                "user_statistical_features",
                "item_statistical_features"
            ]
        )

if __name__ == "__main__":
    # 初始化Feature Store
    repo = FeatureStoreRepo()

    # 应用特征定义
    repo.apply()

    # 物化过去7天的特征
    repo.materialize(
        start_date=datetime.now() - timedelta(days=7),
        end_date=datetime.now()
    )