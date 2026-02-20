import os
import json
import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import asyncio
from contextlib import asynccontextmanager

# FastAPI
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# 监控
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import prometheus_client

# 缓存
import aioredis
from aioredis import Redis

# 模型加载
import joblib
import pickle
import xgboost as xgb

# 特征存储
import feast
from feast import FeatureStore

# 配置
from pydantic import BaseSettings, BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ 配置 ============

class Settings(BaseSettings):
    """应用配置"""
    app_name: str = "Recommendation API"
    environment: str = "production"
    redis_url: str = "redis://localhost:6379"
    feature_store_path: str = "/app/feature_store"
    model_path: str = "/app/models"
    model_name: str = "xgboost"
    model_version: str = "latest"
    kafka_broker: str = "localhost:9092"

    class Config:
        env_file = ".env"

settings = Settings()

# ============ 数据模型 ============

class RecommendationRequest(BaseModel):
    """推荐请求"""
    user_id: str
    session_id: Optional[str] = None
    page_type: str = "home"  # home, product_detail, cart, search
    num_recommendations: int = 20
    exclude_item_ids: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None

class RecommendationItem(BaseModel):
    """推荐物品"""
    item_id: str
    score: float
    reason: Optional[str] = None
    features: Optional[Dict[str, float]] = None

class RecommendationResponse(BaseModel):
    """推荐响应"""
    user_id: str
    request_id: str
    recommendations: List[RecommendationItem]
    processing_time_ms: float
    model_version: str
    experiment_id: Optional[str] = None

class TrackEventRequest(BaseModel):
    """跟踪事件"""
    user_id: str
    item_id: str
    action: str  # impression, click, add_to_cart, purchase
    request_id: Optional[str] = None
    position: Optional[int] = None
    timestamp: Optional[float] = None

# ============ 监控指标 ============

recommendation_counter = Counter(
    'recommendation_requests_total',
    'Total recommendation requests',
    ['page_type', 'model_version']
)

recommendation_latency = Histogram(
    'recommendation_latency_seconds',
    'Recommendation latency',
    ['page_type']
)

item_impression_counter = Counter(
    'item_impressions_total',
    'Total item impressions',
    ['item_id', 'page_type']
)

item_click_counter = Counter(
    'item_clicks_total',
    'Total item clicks',
    ['item_id']
)

click_through_rate_gauge = Gauge(
    'click_through_rate',
    'Click through rate',
    ['user_id']
)

active_users_gauge = Gauge(
    'active_users',
    'Number of active users in last 5 minutes'
)

# ============ 缓存和存储 ============

class RecommendationCache:
    """推荐结果缓存"""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.default_ttl = 300  # 5分钟

    async def get_cached_recommendations(self, user_id: str, page_type: str) -> Optional[List[Dict]]:
        """获取缓存的推荐结果"""
        cache_key = f"rec:{user_id}:{page_type}"
        cached = await self.redis.get(cache_key)
        if cached:
            logger.info(f"Cache hit for user {user_id}")
            return json.loads(cached)
        return None

    async def cache_recommendations(self, user_id: str, page_type: str,
                                   recommendations: List[Dict], ttl: int = None):
        """缓存推荐结果"""
        cache_key = f"rec:{user_id}:{page_type}"
        await self.redis.setex(
            cache_key,
            ttl or self.default_ttl,
            json.dumps(recommendations)
        )

    async def invalidate_user_cache(self, user_id: str):
        """失效用户缓存（当用户有新行为时）"""
        pattern = f"rec:{user_id}:*"
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
            logger.info(f"Invalidated {len(keys)} caches for user {user_id}")

class FeatureService:
    """特征服务"""

    def __init__(self, feature_store_path: str, redis_client: Redis):
        self.fs = FeatureStore(repo_path=feature_store_path)
        self.redis = redis_client

    async def get_user_features(self, user_id: str) -> Dict:
        """获取用户特征"""
        try:
            # 从FeatureStore获取在线特征
            features = self.fs.get_online_features(
                features=[
                    "user_profile_features:total_clicks",
                    "user_profile_features:total_purchases",
                    "user_profile_features:avg_dwell_time",
                    "user_profile_features:user_segment",
                    "user_realtime_features:click_count_5min",
                    "user_realtime_features:recent_items",
                    "user_statistical_features:click_7d_avg",
                    "user_statistical_features:purchase_30d_total"
                ],
                entity_rows=[{"user_id": user_id}]
            ).to_dict()

            return {k: v[0] if v else None for k, v in features.items()}
        except Exception as e:
            logger.error(f"Error getting user features: {e}")
            # 降级：从Redis获取基本特征
            return await self._get_user_features_fallback(user_id)

    async def _get_user_features_fallback(self, user_id: str) -> Dict:
        """降级获取用户特征"""
        user_key = f"user:{user_id}:realtime"
        recent = await self.redis.lrange(f"{user_key}:recent_items", 0, 9)

        return {
            "recent_items": recent,
            "user_segment": "unknown",
            "total_clicks": 0
        }

    async def get_item_features(self, item_ids: List[str]) -> Dict[str, Dict]:
        """批量获取物品特征"""
        try:
            entity_rows = [{"item_id": item_id} for item_id in item_ids]
            features = self.fs.get_online_features(
                features=[
                    "item_statistical_features:total_clicks",
                    "item_statistical_features:total_purchases",
                    "item_statistical_features:purchase_rate",
                    "item_statistical_features:popularity_score",
                ],
                entity_rows=entity_rows
            ).to_dict()

            # 转换为每个物品的特征字典
            result = {}
            for i, item_id in enumerate(item_ids):
                result[item_id] = {
                    k: v[i] if v else None
                    for k, v in features.items()
                }
            return result
        except Exception as e:
            logger.error(f"Error getting item features: {e}")
            return {item_id: {} for item_id in item_ids}

class ModelService:
    """模型服务"""

    def __init__(self, model_path: str, model_name: str, model_version: str):
        self.model_path = model_path
        self.model_name = model_name
        self.model_version = model_version
        self.model = None
        self.feature_names = None
        self.load_model()

    def load_model(self):
        """加载模型"""
        try:
            if self.model_version == 'latest':
                # 查找最新版本
                import glob
                versions = glob.glob(f"{self.model_path}/{self.model_name}/*")
                if versions:
                    self.model_version = max([v.split('/')[-1] for v in versions])

            model_file = f"{self.model_path}/{self.model_name}/{self.model_version}/model.pkl"

            if self.model_name == 'xgboost':
                self.model = joblib.load(model_file)
            elif self.model_name == 'lightfm':
                with open(model_file, 'rb') as f:
                    self.model = pickle.load(f)
            else:
                raise ValueError(f"Unknown model type: {self.model_name}")

            # 加载特征名称
            feature_file = f"{self.model_path}/{self.model_name}/{self.model_version}/feature_names.json"
            if os.path.exists(feature_file):
                with open(feature_file, 'r') as f:
                    self.feature_names = json.load(f)

            logger.info(f"Loaded model {self.model_name}:{self.model_version}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.model = None

    async def predict(self, user_features: Dict, item_features: Dict[str, Dict]) -> Dict[str, float]:
        """预测用户对每个物品的得分"""
        if self.model is None:
            return self._fallback_predict(item_features)

        scores = {}
        try:
            # 构建特征向量
            for item_id, item_feat in item_features.items():
                # 合并用户和物品特征
                features = {}
                features.update(user_features)
                features.update(item_feat)

                # 转换为特征向量
                feature_vector = self._build_feature_vector(features)

                if feature_vector is not None:
                    # 预测
                    if hasattr(self.model, 'predict_proba'):
                        proba = self.model.predict_proba([feature_vector])[0]
                        scores[item_id] = float(proba[1])  # 正类概率
                    else:
                        score = self.model.predict([feature_vector])[0]
                        scores[item_id] = float(score)

            return scores
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return self._fallback_predict(item_features)

    def _build_feature_vector(self, features: Dict) -> np.ndarray:
        """构建特征向量"""
        if not self.feature_names:
            return None

        vector = []
        for name in self.feature_names:
            value = features.get(name, 0)
            # 处理缺失值
            if value is None:
                value = 0
            vector.append(float(value))

        return np.array(vector).reshape(1, -1)

    def _fallback_predict(self, item_features: Dict[str, Dict]) -> Dict[str, float]:
        """降级预测（基于流行度）"""
        scores = {}
        for item_id, features in item_features.items():
            # 使用物品流行度作为得分
            popularity = features.get('popularity_score', 0)
            scores[item_id] = float(popularity)
        return scores

# ============ 推荐引擎 ============

class RecommendationEngine:
    """推荐引擎核心"""

    def __init__(self, feature_service, model_service, cache):
        self.feature_service = feature_service
        self.model_service = model_service
        self.cache = cache

    async def recommend(self, request: RecommendationRequest) -> List[RecommendationItem]:
        """生成推荐"""
        # 1. 检查缓存
        cached = await self.cache.get_cached_recommendations(
            request.user_id, request.page_type
        )
        if cached:
            return [RecommendationItem(**item) for item in cached]

        # 2. 获取候选物品
        candidates = await self.get_candidates(request)

        # 3. 获取特征
        user_features = await self.feature_service.get_user_features(request.user_id)
        item_features = await self.feature_service.get_item_features(candidates)

        # 4. 模型预测
        scores = await self.model_service.predict(user_features, item_features)

        # 5. 后处理
        recommendations = await self.post_process(
            request, scores, user_features, item_features
        )

        # 6. 缓存结果
        if recommendations:
            await self.cache.cache_recommendations(
                request.user_id,
                request.page_type,
                [r.dict() for r in recommendations]
            )

        return recommendations

    async def get_candidates(self, request: RecommendationRequest) -> List[str]:
        """获取候选物品"""
        # 多路召回
        candidates = set()

        # 路1: 用户最近交互过的相似物品
        recent = await self.get_recent_similar_items(request.user_id)
        candidates.update(recent)

        # 路2: 热门物品
        popular = await self.get_popular_items(request.page_type)
        candidates.update(popular)

        # 路3: 基于类目的物品
        category_based = await self.get_category_based_items(request.user_id)
        candidates.update(category_based)

        # 移除排除的物品
        if request.exclude_item_ids:
            candidates -= set(request.exclude_item_ids)

        return list(candidates)[:200]  # 限制候选集大小

    async def get_recent_similar_items(self, user_id: str) -> List[str]:
        """获取最近交互物品的相似物品"""
        # 从Redis获取用户最近交互
        user_key = f"user:{user_id}:realtime"
        recent_items = await self.cache.redis.lrange(f"{user_key}:recent_items", 0, 5)

        if not recent_items:
            return []

        # 从Redis获取相似物品（预计算的ItemCF结果）
        similar_items = []
        for item_id in recent_items:
            sim_key = f"item:{item_id}:similar"
            sims = await self.cache.redis.zrevrange(sim_key, 0, 10)
            similar_items.extend(sims)

        return similar_items

    async def get_popular_items(self, page_type: str) -> List[str]:
        """获取热门物品"""
        popular_key = f"popular:{page_type}"
        popular = await self.cache.redis.zrevrange(popular_key, 0, 100)
        return popular

    async def get_category_based_items(self, user_id: str) -> List[str]:
        """获取基于用户偏好类目的物品"""
        # 获取用户top品类
        user_features = await self.feature_service.get_user_features(user_id)
        top_categories = user_features.get('top_categories', [])

        if not top_categories:
            return []

        # 从每个品类取一些物品
        items = []
        for category in top_categories[:3]:
            cat_key = f"category:{category}:items"
            cat_items = await self.cache.redis.zrevrange(cat_key, 0, 30)
            items.extend(cat_items)

        return items

    async def post_process(self, request: RecommendationRequest, scores: Dict[str, float],
                          user_features: Dict, item_features: Dict) -> List[RecommendationItem]:
        """后处理：多样性、过滤等"""

        # 按得分排序
        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # 多样性处理（MMR算法）
        final_items = self.diversify(sorted_items, user_features, item_features)

        # 截取需要的数量
        final_items = final_items[:request.num_recommendations]

        # 转换为ResponseItem
        recommendations = []
        for item_id, score in final_items:
            reason = self.generate_reason(item_id, user_features, item_features)
            recommendations.append(
                RecommendationItem(
                    item_id=item_id,
                    score=score,
                    reason=reason
                )
            )

        return recommendations

    def diversify(self, sorted_items, user_features, item_features, lambda_param=0.5):
        """MMR多样性重排序"""
        selected = []
        candidates = sorted_items.copy()

        if not candidates:
            return []

        # 选择第一个
        selected.append(candidates[0])
        candidates = candidates[1:]

        while len(selected) < min(50, len(sorted_items)) and candidates:
            max_score = -float('inf')
            best_item = None

            for item_id, score in candidates:
                # 计算与已选物品的最大相似度
                max_sim = 0
                for sel_id, _ in selected:
                    sim = self.calculate_similarity(item_id, sel_id, item_features)
                    max_sim = max(max_sim, sim)

                # MMR公式: lambda * 相关度 - (1-lambda) * 最大相似度
                mmr_score = lambda_param * score - (1 - lambda_param) * max_sim

                if mmr_score > max_score:
                    max_score = mmr_score
                    best_item = (item_id, score)

            if best_item:
                selected.append(best_item)
                candidates.remove(best_item)

        return selected

    def calculate_similarity(self, item_id1, item_id2, item_features):
        """计算两个物品的相似度（基于特征）"""
        feat1 = item_features.get(item_id1, {})
        feat2 = item_features.get(item_id2, {})

        # 使用品类相似度
        cat1 = feat1.get('category', '')
        cat2 = feat2.get('category', '')

        if cat1 == cat2:
            return 0.8
        elif cat1 and cat2 and cat1[:3] == cat2[:3]:  # 同大类
            return 0.5
        else:
            return 0.1

    def generate_reason(self, item_id, user_features, item_features):
        """生成推荐理由"""
        recent_items = user_features.get('recent_items', [])

        if recent_items and item_id in recent_items:
            return "因为您最近浏览过类似商品"

        if item_features.get(item_id, {}).get('purchase_rate', 0) > 0.1:
            return "热门推荐"

        return "猜你喜欢"

# ============ FastAPI应用 ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    app.state.redis = await aioredis.from_url(settings.redis_url, decode_responses=True)
    app.state.cache = RecommendationCache(app.state.redis)
    app.state.feature_service = FeatureService(settings.feature_store_path, app.state.redis)
    app.state.model_service = ModelService(
        settings.model_path,
        settings.model_name,
        settings.model_version
    )
    app.state.engine = RecommendationEngine(
        app.state.feature_service,
        app.state.model_service,
        app.state.cache
    )

    logger.info("Application started")
    yield

    # 关闭时
    await app.state.redis.close()
    logger.info("Application shutdown")

app = FastAPI(
    title="Recommendation API",
    description="电商推荐系统API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ API路由 ============

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/metrics")
async def metrics():
    """Prometheus监控指标"""
    return generate_latest()

@app.post("/api/v1/recommend", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    background_tasks: BackgroundTasks,
    request_obj: Request
):
    """获取推荐"""
    start_time = datetime.now()

    # 记录请求指标
    recommendation_counter.labels(
        page_type=request.page_type,
        model_version=settings.model_version
    ).inc()

    try:
        # 生成推荐
        recommendations = await request_obj.app.state.engine.recommend(request)

        # 计算处理时间
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        recommendation_latency.labels(request.page_type).observe(processing_time / 1000)

        # 异步记录曝光
        background_tasks.add_task(
            record_impressions,
            request.user_id,
            recommendations,
            request_obj
        )

        return RecommendationResponse(
            user_id=request.user_id,
            request_id=generate_request_id(),
            recommendations=recommendations,
            processing_time_ms=processing_time,
            model_version=settings.model_version
        )

    except Exception as e:
        logger.error(f"Recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/events")
async def track_event(event: TrackEventRequest):
    """跟踪用户事件"""
    try:
        # 存储事件到Kafka
        await send_to_kafka(event)

        # 更新指标
        if event.action == "impression":
            item_impression_counter.labels(
                item_id=event.item_id,
                page_type="all"
            ).inc()
        elif event.action == "click":
            item_click_counter.labels(item_id=event.item_id).inc()

        # 如果有request_id，记录到AB测试
        if event.request_id:
            await record_ab_test_event(event)

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Event tracking error: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/v1/refresh/{user_id}")
async def refresh_user_recommendations(user_id: str, request: Request):
    """刷新用户推荐缓存（有新行为时调用）"""
    await request.app.state.cache.invalidate_user_cache(user_id)
    return {"status": "success", "message": f"Cache invalidated for user {user_id}"}

@app.get("/api/v1/features/user/{user_id}")
async def get_user_features_api(user_id: str, request: Request):
    """获取用户特征（调试用）"""
    features = await request.app.state.feature_service.get_user_features(user_id)
    return features

@app.get("/api/v1/features/item/{item_id}")
async def get_item_features_api(item_id: str, request: Request):
    """获取物品特征（调试用）"""
    features = await request.app.state.feature_service.get_item_features([item_id])
    return features.get(item_id, {})

# ============ 辅助函数 ============

def generate_request_id() -> str:
    """生成请求ID"""
    import uuid
    return str(uuid.uuid4())

async def record_impressions(user_id: str, recommendations: List[RecommendationItem], request: Request):
    """记录曝光"""
    events = []
    for i, rec in enumerate(recommendations):
        events.append({
            "user_id": user_id,
            "item_id": rec.item_id,
            "action": "impression",
            "position": i,
            "timestamp": datetime.now().timestamp()
        })

    # 异步发送到Kafka
    await send_events_to_kafka(events)

async def send_to_kafka(event: TrackEventRequest):
    """发送单个事件到Kafka"""
    # 这里使用aiokafka实现
    import aiokafka
    producer = aiokafka.AIOKafkaProducer(
        bootstrap_servers=settings.kafka_broker
    )
    await producer.start()
    try:
        value = json.dumps(event.dict()).encode()
        await producer.send("user-events", value)
    finally:
        await producer.stop()

async def send_events_to_kafka(events: List[Dict]):
    """批量发送事件到Kafka"""
    import aiokafka
    producer = aiokafka.AIOKafkaProducer(
        bootstrap_servers=settings.kafka_broker
    )
    await producer.start()
    try:
        for event in events:
            value = json.dumps(event).encode()
            await producer.send("user-events", value)
    finally:
        await producer.stop()

async def record_ab_test_event(event: TrackEventRequest):
    """记录AB测试事件"""
    # 存储到AB测试专用的Redis
    ab_redis = await aioredis.from_url("redis://localhost:6380", decode_responses=True)

    # 记录用户属于哪个实验组
    if event.action == "impression":
        key = f"ab:exposure:{event.request_id}"
        await ab_redis.incr(key)
    elif event.action == "click":
        key = f"ab:click:{event.request_id}"
        await ab_redis.incr(key)
    elif event.action == "purchase":
        key = f"ab:purchase:{event.request_id}"
        await ab_redis.incr(key)

# ============ 启动 ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)