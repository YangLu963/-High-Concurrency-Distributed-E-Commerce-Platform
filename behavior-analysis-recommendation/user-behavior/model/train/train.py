import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging
import joblib
import json
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# 机器学习库
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import xgboost as xgb
import lightgbm as lgb
from lightfm import LightFM
from lightfm.data import Dataset
from lightfm.evaluation import precision_at_k, recall_at_k

# 特征存储
import feast
from feast import FeatureStore

# 实验跟踪
import mlflow
import mlflow.sklearn
import mlflow.xgboost

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecommendationTrainer:
    """推荐模型训练器"""

    def __init__(self,
                 model_type: str = 'xgboost',
                 feature_store_path: str = '../feature_store',
                 experiment_name: str = 'recommendation_model'):

        self.model_type = model_type
        self.model = None
        self.feature_names = None
        self.label_encoders = {}

        # 初始化Feature Store
        self.fs = FeatureStore(repo_path=feature_store_path)

        # 初始化MLflow
        mlflow.set_experiment(experiment_name)

        logger.info(f"Initialized {model_type} trainer")

    def prepare_training_data(self,
                             start_date: datetime,
                             end_date: datetime) -> Tuple[pd.DataFrame, pd.Series]:
        """准备训练数据"""

        # 构建实体DataFrame（用户-物品对）
        entity_df = self._build_entity_df(start_date, end_date)

        # 从Feature Store获取特征
        features = self.fs.get_historical_features(
            entity_df=entity_df,
            features=[
                "user_profile_features:total_clicks",
                "user_profile_features:total_purchases",
                "user_profile_features:avg_dwell_time",
                "user_profile_features:unique_items_viewed",
                "user_profile_features:peak_hour",
                "user_profile_features:user_segment",
                "user_statistical_features:click_7d_avg",
                "user_statistical_features:purchase_30d_total",
                "user_statistical_features:active_days_30d",
                "user_statistical_features:category_entropy",
                "item_statistical_features:total_clicks",
                "item_statistical_features:total_purchases",
                "item_statistical_features:purchase_rate",
                "item_statistical_features:popularity_score",
                "item_statistical_features:avg_dwell_time",
            ]
        ).to_df()

        # 处理特征
        X, y = self._process_features(features)

        logger.info(f"Prepared training data: {X.shape[0]} samples, {X.shape[1]} features")

        return X, y

    def _build_entity_df(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """构建实体DataFrame（用户-物品交互）"""
        # 这里应该从数据仓库获取真实的用户-物品交互
        # 简化实现：生成示例数据

        # 假设从数据库获取
        import psycopg2

        conn = psycopg2.connect(
            host="localhost",
            database="ecommerce",
            user="user",
            password="password"
        )

        query = f"""
            SELECT
                user_id,
                item_id,
                event_timestamp,
                CASE WHEN action = 'purchase' THEN 1 ELSE 0 END as label
            FROM user_behaviors
            WHERE event_timestamp BETWEEN '{start_date}' AND '{end_date}'
            LIMIT 10000
        """

        entity_df = pd.read_sql(query, conn)
        conn.close()

        return entity_df

    def _process_features(self, features_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """特征处理：编码、标准化"""

        # 分离特征和标签
        if 'label' in features_df.columns:
            y = features_df['label']
            X = features_df.drop(columns=['label', 'event_timestamp', 'user_id', 'item_id'])
        else:
            y = None
            X = features_df

        # 处理分类特征
        categorical_cols = X.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            if col not in self.label_encoders:
                self.label_encoders[col] = LabelEncoder()
                X[col] = self.label_encoders[col].fit_transform(X[col].astype(str))
            else:
                X[col] = self.label_encoders[col].transform(X[col].astype(str))

        # 处理数值特征
        numeric_cols = X.select_dtypes(include=[np.number]).columns
        scaler = StandardScaler()
        X[numeric_cols] = scaler.fit_transform(X[numeric_cols])

        self.feature_names = list(X.columns)

        return X, y

    def train_xgboost(self, X_train, y_train, X_val, y_val):
        """训练XGBoost模型"""

        # 定义参数网格
        param_grid = {
            'n_estimators': [100, 200, 300],
            'max_depth': [3, 5, 7],
            'learning_rate': [0.01, 0.05, 0.1],
            'subsample': [0.8, 1.0],
            'colsample_bytree': [0.8, 1.0]
        }

        # 基础模型
        xgb_model = xgb.XGBClassifier(
            objective='binary:logistic',
            eval_metric='auc',
            use_label_encoder=False,
            random_state=42
        )

        # 网格搜索
        grid_search = GridSearchCV(
            xgb_model,
            param_grid,
            cv=3,
            scoring='roc_auc',
            n_jobs=-1,
            verbose=1
        )

        grid_search.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            early_stopping_rounds=10,
            verbose=False
        )

        self.model = grid_search.best_estimator_

        logger.info(f"Best XGBoost params: {grid_search.best_params_}")
        logger.info(f"Best XGBoost AUC: {grid_search.best_score_}")

        return self.model

    def train_lightfm(self, user_ids, item_ids, interactions):
        """训练LightFM模型（协同过滤）"""

        # 创建数据集
        dataset = Dataset()
        dataset.fit(
            users=user_ids.unique(),
            items=item_ids.unique()
        )

        # 构建交互矩阵
        (interactions_matrix, weights_matrix) = dataset.build_interactions(
            [(uid, iid, weight) for uid, iid, weight in zip(user_ids, item_ids, interactions)]
        )

        # 训练模型
        model = LightFM(
            loss='warp',
            learning_rate=0.05,
            item_alpha=1e-6,
            user_alpha=1e-6,
            random_state=42
        )

        model.fit(
            interactions_matrix,
            epochs=30,
            num_threads=4,
            verbose=True
        )

        self.model = {
            'model': model,
            'dataset': dataset,
            'user_mapping': dataset.mapping()[0],
            'item_mapping': dataset.mapping()[2]
        }

        return self.model

    def train(self, X=None, y=None, **kwargs):
        """训练主函数"""

        with mlflow.start_run() as run:

            # 记录参数
            mlflow.log_param("model_type", self.model_type)

            if self.model_type == 'xgboost':
                # 准备数据
                if X is None or y is None:
                    X, y = self.prepare_training_data(
                        start_date=kwargs.get('start_date', datetime.now() - timedelta(days=30)),
                        end_date=kwargs.get('end_date', datetime.now())
                    )

                # 划分训练集和验证集
                X_train, X_val, y_train, y_val = train_test_split(
                    X, y, test_size=0.2, random_state=42, stratify=y
                )

                # 训练
                model = self.train_xgboost(X_train, y_train, X_val, y_val)

                # 评估
                y_pred = model.predict_proba(X_val)[:, 1]
                auc = roc_auc_score(y_val, y_pred)

                # 记录指标
                mlflow.log_metric("val_auc", auc)
                mlflow.log_metric("train_samples", len(X_train))

                # 记录特征重要性
                importance = model.feature_importances_
                for name, imp in zip(self.feature_names, importance):
                    mlflow.log_metric(f"feature_importance_{name}", imp)

                # 保存模型
                mlflow.xgboost.log_model(model, "xgboost_model")

                # 保存特征名称
                with open('feature_names.json', 'w') as f:
                    json.dump(self.feature_names, f)
                mlflow.log_artifact('feature_names.json')

            elif self.model_type == 'lightfm':
                # 准备数据（用户ID, 物品ID, 交互）
                user_ids = kwargs.get('user_ids')
                item_ids = kwargs.get('item_ids')
                interactions = kwargs.get('interactions')

                model = self.train_lightfm(user_ids, item_ids, interactions)

                # 保存模型
                import pickle
                with open('lightfm_model.pkl', 'wb') as f:
                    pickle.dump(model, f)
                mlflow.log_artifact('lightfm_model.pkl')

            # 记录模型
            run_id = run.info.run_id
            logger.info(f"Training completed. Run ID: {run_id}")

            return run_id

class ModelManager:
    """模型管理：版本控制、部署等"""

    def __init__(self, model_registry_path: str = './models'):
        self.model_registry_path = model_registry_path
        self.models = {}

    def save_model(self, model, model_name: str, version: str, metadata: Dict = None):
        """保存模型到本地"""
        import os

        model_path = f"{self.model_registry_path}/{model_name}/{version}"
        os.makedirs(model_path, exist_ok=True)

        # 保存模型
        if model_name == 'xgboost':
            joblib.dump(model, f"{model_path}/model.pkl")
        elif model_name == 'lightfm':
            import pickle
            with open(f"{model_path}/model.pkl", 'wb') as f:
                pickle.dump(model, f)

        # 保存元数据
        if metadata:
            with open(f"{model_path}/metadata.json", 'w') as f:
                json.dump(metadata, f)

        logger.info(f"Model saved to {model_path}")
        return model_path

    def load_model(self, model_name: str, version: str = 'latest'):
        """加载模型"""
        import os
        import glob

        if version == 'latest':
            # 查找最新版本
            versions = glob.glob(f"{self.model_registry_path}/{model_name}/*")
            if not versions:
                raise ValueError(f"No model found for {model_name}")
            version = max([v.split('/')[-1] for v in versions])

        model_path = f"{self.model_registry_path}/{model_name}/{version}"

        # 加载模型
        if model_name == 'xgboost':
            model = joblib.load(f"{model_path}/model.pkl")
        elif model_name == 'lightfm':
            import pickle
            with open(f"{model_path}/model.pkl", 'rb') as f:
                model = pickle.load(f)
        else:
            model = None

        # 加载元数据
        metadata = {}
        if os.path.exists(f"{model_path}/metadata.json"):
            with open(f"{model_path}/metadata.json", 'r') as f:
                metadata = json.load(f)

        return model, metadata

if __name__ == "__main__":
    # 训练示例
    trainer = RecommendationTrainer(
        model_type='xgboost',
        feature_store_path='../feature_store'
    )

    # 训练模型
    run_id = trainer.train(
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now()
    )

    # 保存模型
    manager = ModelManager()
    manager.save_model(
        model=trainer.model,
        model_name='xgboost',
        version='v1.0.0',
        metadata={
            'run_id': run_id,
            'feature_names': trainer.feature_names,
            'train_date': datetime.now().isoformat()
        }
    )