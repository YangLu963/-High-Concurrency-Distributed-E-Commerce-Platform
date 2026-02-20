from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import redis
import psycopg2
from psycopg2.extras import RealDictCursor
import json

class UserFeatureStore:
    """用户特征存储与管理"""

    def __init__(self, redis_host='localhost', redis_port=6379,
                 pg_host='localhost', pg_db='feature_store'):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

        self.pg_conn = psycopg2.connect(
            host=pg_host,
            database=pg_db,
            user='feature_user',
            password='feature_pass',
            cursor_factory=RealDictCursor
        )

        # 特征Schema定义
        self.feature_schema = {
            # 实时特征（来自Faust）
            'realtime_features': {
                'click_count_5min': float,
                'add_to_cart_count_5min': float,
                'purchase_count_5min': float,
                'ctr_5min': float,
                'recent_items': list,
                'current_session_items': list,
            },

            # 用户画像特征（来自Spark ETL）
            'profile_features': {
                'total_clicks': int,
                'total_purchases': int,
                'avg_dwell_time': float,
                'unique_items_viewed': int,
                'top_categories': list,
                'peak_hour': int,
                'user_segment': str,
                'purchase_power': float,  # 消费能力
            },

            # 统计特征（来自离线计算）
            'statistical_features': {
                'click_7d_avg': float,
                'purchase_30d_total': int,
                'category_entropy': float,  # 品类多样性
                'active_days_30d': int,
                'session_avg_duration': float,
            },

            # 嵌入特征（来自模型）
            'embedding_features': {
                'user_vector': list,  # 128维向量
                'category_preference_vector': list,
            }
        }

    def get_user_features(self, user_id: str, feature_groups: List[str] = None) -> Dict:
        """获取用户所有特征（在线推理用）"""
        if feature_groups is None:
            feature_groups = ['realtime_features', 'profile_features', 'statistical_features']

        features = {}

        # 1. 从Redis获取实时特征
        for group in feature_groups:
            if group == 'realtime_features':
                realtime = self.get_realtime_features(user_id)
                features.update(realtime)

        # 2. 从PostgreSQL获取离线特征
        for group in feature_groups:
            if group in ['profile_features', 'statistical_features']:
                offline = self.get_offline_features(user_id, group)
                features.update(offline)

        # 3. 从Redis获取Embedding（如果有）
        if 'embedding_features' in feature_groups:
            embedding = self.get_embedding_features(user_id)
            features.update(embedding)

        return features

    def get_realtime_features(self, user_id: str) -> Dict:
        """从Redis获取实时特征"""
        features = {}
        user_key = f"user:{user_id}:realtime"

        # 获取最近行为计数
        hour_key = datetime.now().strftime("%Y%m%d%H")
        actions = self.redis_client.hgetall(f"{user_key}:actions:{hour_key}")
        if actions:
            features['click_count_5min'] = float(actions.get('click', 0))
            features['add_to_cart_count_5min'] = float(actions.get('add_to_cart', 0))
            features['purchase_count_5min'] = float(actions.get('purchase', 0))

        # 计算实时CTR
        clicks = features.get('click_count_5min', 0)
        purchases = features.get('purchase_count_5min', 0)
        if clicks > 0:
            features['ctr_5min'] = purchases / clicks
        else:
            features['ctr_5min'] = 0.0

        # 获取最近交互物品
        recent = self.redis_client.lrange(f"{user_key}:recent_items", 0, 9)
        features['recent_items'] = recent

        return features

    def get_offline_features(self, user_id: str, feature_group: str) -> Dict:
        """从PostgreSQL获取离线特征"""
        cursor = self.pg_conn.cursor()

        table_map = {
            'profile_features': 'user_profiles',
            'statistical_features': 'user_statistics'
        }

        table = table_map.get(feature_group)
        if not table:
            return {}

        cursor.execute(f"""
            SELECT * FROM {table}
            WHERE user_id = %s
            ORDER BY updated_at DESC
            LIMIT 1
        """, (user_id,))

        row = cursor.fetchone()
        cursor.close()

        return dict(row) if row else {}

    def get_embedding_features(self, user_id: str) -> Dict:
        """从Redis获取用户Embedding"""
        embedding_key = f"user:{user_id}:embedding"

        # 尝试获取DSSM模型生成的向量
        vector = self.redis_client.get(embedding_key)
        if vector:
            # 假设存储的是JSON字符串
            import json
            return {'user_vector': json.loads(vector)}

        return {}

    def update_realtime_features(self, user_id: str, features: Dict):
        """更新实时特征（由Faust调用）"""
        pipe = self.redis_client.pipeline()
        user_key = f"user:{user_id}:realtime"

        for key, value in features.items():
            if isinstance(value, (int, float)):
                pipe.hset(f"{user_key}:current", key, value)
            elif isinstance(value, list):
                pipe.set(f"{user_key}:{key}", json.dumps(value))

        pipe.expire(f"{user_key}:current", 3600)  # 1小时过期
        pipe.execute()

    def batch_update_offline_features(self, features_df: pd.DataFrame, feature_group: str):
        """批量更新离线特征（由Spark调用）"""
        cursor = self.pg_conn.cursor()

        table_map = {
            'profile_features': 'user_profiles',
            'statistical_features': 'user_statistics'
        }

        table = table_map.get(feature_group)
        if not table:
            return

        # 批量upsert
        for _, row in features_df.iterrows():
            columns = list(row.index)
            values = [row[col] for col in columns]

            # 构建upsert语句
            placeholders = ','.join(['%s'] * len(columns))
            updates = ','.join([f"{col}=EXCLUDED.{col}" for col in columns if col != 'user_id'])

            query = f"""
                INSERT INTO {table} ({','.join(columns)})
                VALUES ({placeholders})
                ON CONFLICT (user_id) DO UPDATE
                SET {updates}, updated_at = NOW()
            """

            cursor.execute(query, values)

        self.pg_conn.commit()
        cursor.close()

    def get_feature_importance(self, feature_name: str) -> float:
        """获取特征重要性（来自模型训练）"""
        cursor = self.pg_conn.cursor()
        cursor.execute("""
            SELECT importance FROM feature_importance
            WHERE feature_name = %s
            ORDER BY updated_at DESC LIMIT 1
        """, (feature_name,))

        row = cursor.fetchone()
        cursor.close()

        return row['importance'] if row else 0.0

class ItemFeatureStore:
    """物品特征存储"""

    def __init__(self, redis_host='localhost', redis_port=6379):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

        # 物品特征Schema
        self.feature_schema = {
            'item_metadata': {
                'category': str,
                'price': float,
                'brand': str,
                'title': str,
                'description': str,
            },
            'item_stats': {
                'total_clicks': int,
                'total_purchases': int,
                'avg_dwell_time': float,
                'purchase_rate': float,
                'popularity_score': float,
            },
            'item_embedding': {
                'item_vector': list,
                'category_vector': list,
            }
        }

    def get_item_features(self, item_id: str, include_embedding: bool = False) -> Dict:
        """获取物品特征"""
        item_key = f"item:{item_id}"

        # 从Redis获取元数据和统计
        metadata = self.redis_client.hgetall(f"{item_key}:metadata")
        stats = self.redis_client.hgetall(f"{item_key}:stats")

        features = {}
        features.update({k: self._parse_value(v) for k, v in metadata.items()})
        features.update({k: self._parse_value(v) for k, v in stats.items()})

        if include_embedding:
            embedding = self.redis_client.get(f"{item_key}:embedding")
            if embedding:
                features['item_vector'] = json.loads(embedding)

        return features

    def _parse_value(self, value):
        """解析Redis存储的值"""
        try:
            return int(value)
        except:
            try:
                return float(value)
            except:
                return value