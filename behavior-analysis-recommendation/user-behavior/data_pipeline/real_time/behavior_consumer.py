import json
import faust
from datetime import datetime
from typing import List
import asyncpg
import redis

# Faust应用配置
app = faust.App(
    'behavior_consumer',
    broker='kafka://localhost:9092',
    value_serializer='json',
    web_port=6066,
)

# 定义数据模型
class UserBehavior(faust.Record, serializer='json'):
    user_id: str
    item_id: str
    action: str  # click, add_to_cart, purchase
    timestamp: float
    session_id: str
    page_url: str
    dwell_time: float = 0.0

# 定义Kafka topic
behavior_topic = app.topic('user-behavior', value_type=UserBehavior)

# 实时特征存储（Redis连接池）
redis_pool = redis.ConnectionPool(host='localhost', port=6379, decode_responses=True)

@app.agent(behavior_topic)
async def process_behavior(behaviors):
    """实时处理用户行为，生成特征"""
    async for behavior in behaviors:
        # 1. 存储原始行为到PostgreSQL
        await store_raw_behavior(behavior)

        # 2. 更新Redis实时特征
        await update_realtime_features(behavior)

        # 3. 检测即时兴趣信号（如短时间内多次点击）
        if await detect_instant_interest(behavior):
            await trigger_recommendation_refresh(behavior.user_id)

        # 4. 计算实时统计指标
        await update_realtime_stats(behavior)

async def store_raw_behavior(behavior: UserBehavior):
    """存储原始行为到PostgreSQL"""
    conn = await asyncpg.connect('postgresql://user:pass@localhost:5432/ecommerce')
    try:
        await conn.execute("""
            INSERT INTO user_behaviors
            (user_id, item_id, action, timestamp, session_id, page_url, dwell_time)
            VALUES ($1, $2, $3, to_timestamp($4), $5, $6, $7)
        """, behavior.user_id, behavior.item_id, behavior.action,
            behavior.timestamp, behavior.session_id,
            behavior.page_url, behavior.dwell_time)
    finally:
        await conn.close()

async def update_realtime_features(behavior: UserBehavior):
    """更新Redis实时特征"""
    r = redis.Redis(connection_pool=redis_pool)
    user_key = f"user:{behavior.user_id}:realtime"

    # 使用Redis pipeline批量操作
    pipe = r.pipeline()

    # 记录用户最近10个行为
    pipe.lpush(f"{user_key}:recent_items", behavior.item_id)
    pipe.ltrim(f"{user_key}:recent_items", 0, 9)

    # 更新各类行为的计数（1小时窗口）
    hour_key = datetime.now().strftime("%Y%m%d%H")
    pipe.hincrby(f"{user_key}:actions:{hour_key}", behavior.action, 1)

    # 记录用户点击序列（用于Session-based推荐）
    pipe.zadd(f"{user_key}:sequence",
              {f"{behavior.timestamp}:{behavior.item_id}": behavior.timestamp})
    pipe.zremrangebyrank(f"{user_key}:sequence", 0, -51)  # 保留最近50个

    # 设置过期时间（24小时）
    pipe.expire(f"{user_key}:recent_items", 86400)
    pipe.expire(f"{user_key}:actions:{hour_key}", 86400)

    pipe.execute()

async def detect_instant_interest(behavior: UserBehavior) -> bool:
    """检测即时兴趣（如短时间多次点击同一类商品）"""
    r = redis.Redis(connection_pool=redis_pool)

    # 检查用户最近3分钟内是否点击了同一商品超过3次
    recent = r.lrange(f"user:{behavior.user_id}:recent_items", 0, 9)
    if recent.count(behavior.item_id) >= 3:
        return True

    return False

async def trigger_recommendation_refresh(user_id: str):
    """触发推荐刷新（推送到WebSocket）"""
    # 这里可以发送消息到另一个topic或WebSocket
    refresh_topic = app.topic('recommendation-refresh')
    await refresh_topic.send(value={'user_id': user_id, 'reason': 'instant_interest'})