from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.window import Window
from pyspark.ml.feature import StringIndexer
import argparse
from datetime import datetime, timedelta

class BehaviorETL:
    def __init__(self, date=None):
        self.spark = SparkSession.builder \
            .appName("BehaviorETL") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .enableHiveSupport() \
            .getOrCreate()

        self.date = date or datetime.now().strftime("%Y-%m-%d")

    def extract_raw_behaviors(self):
        """从Hive或Parquet提取原始行为数据"""
        # 读取前一天的行为日志
        df = self.spark.sql(f"""
            SELECT
                user_id,
                item_id,
                action,
                timestamp,
                session_id,
                page_url,
                dwell_time
            FROM raw_data.user_behaviors
            WHERE dt = '{self.date}'
        """)
        return df

    def transform_user_features(self, df):
        """生成用户特征"""
        # 用户基础统计
        user_stats = df.groupBy("user_id").agg(
            count(when(col("action") == "click", True)).alias("total_clicks"),
            count(when(col("action") == "add_to_cart", True)).alias("total_add_to_cart"),
            count(when(col("action") == "purchase", True)).alias("total_purchases"),
            countDistinct("item_id").alias("unique_items_viewed"),
            countDistinct("session_id").alias("total_sessions"),
            avg("dwell_time").alias("avg_dwell_time")
        )

        # 用户活跃时段特征
        user_hour = df.withColumn("hour", hour(from_unixtime("timestamp"))) \
            .groupBy("user_id", "hour").agg(count("*").alias("hour_count"))

        # 找出用户最活跃的时段
        window_spec = Window.partitionBy("user_id").orderBy(desc("hour_count"))
        user_peak_hour = user_hour.withColumn("rank", row_number().over(window_spec)) \
            .filter(col("rank") == 1) \
            .select("user_id", col("hour").alias("peak_hour"))

        # 用户偏好品类（假设item_id包含品类信息）
        user_category = df.filter(col("action") == "purchase") \
            .groupBy("user_id", "category_id") \
            .agg(count("*").alias("purchase_count")) \
            .withColumn("rank", row_number().over(
                Window.partitionBy("user_id").orderBy(desc("purchase_count"))
            )) \
            .filter(col("rank") <= 3) \
            .groupBy("user_id") \
            .agg(collect_list("category_id").alias("top_categories"))

        # 合并所有特征
        user_features = user_stats \
            .join(user_peak_hour, "user_id", "left") \
            .join(user_category, "user_id", "left")

        return user_features

    def transform_item_features(self, df):
        """生成物品特征"""
        # 物品基础统计
        item_stats = df.groupBy("item_id").agg(
            count(when(col("action") == "click", True)).alias("total_clicks"),
            count(when(col("action") == "purchase", True)).alias("total_purchases"),
            countDistinct("user_id").alias("unique_users"),
            avg("dwell_time").alias("avg_dwell_time")
        )

        # 物品的购买转化率
        item_stats = item_stats.withColumn(
            "purchase_rate",
            when(col("total_clicks") > 0, col("total_purchases") / col("total_clicks"))
            .otherwise(0.0)
        )

        # 物品共现矩阵（用于ItemCF）
        # 找到经常一起购买的物品对
        pair_df = df.filter(col("action") == "purchase") \
            .groupBy("user_id") \
            .agg(collect_list("item_id").alias("items"))

        # 展开物品对
        from pyspark.sql.functions import udf
        from itertools import combinations

        def generate_pairs(items):
            return list(combinations(sorted(items), 2))

        generate_pairs_udf = udf(generate_pairs, ArrayType(StructType([
            StructField("item_i", StringType()),
            StructField("item_j", StringType())
        ])))

        item_pairs = pair_df.select(generate_pairs_udf("items").alias("pairs")) \
            .select(explode("pairs").alias("pair")) \
            .select(col("pair.item_i"), col("pair.item_j")) \
            .groupBy("item_i", "item_j").agg(count("*").alias("cooccurrence"))

        return item_stats, item_pairs

    def transform_session_features(self, df):
        """生成会话特征"""
        session_features = df.groupBy("session_id", "user_id").agg(
            min("timestamp").alias("session_start"),
            max("timestamp").alias("session_end"),
            count("*").alias("actions_in_session"),
            collect_list("item_id").alias("items_viewed"),
            sum(when(col("action") == "purchase", 1).otherwise(0)).alias("purchases_in_session")
        ).withColumn(
            "session_duration",
            col("session_end") - col("session_start")
        ).withColumn(
            "converted",
            when(col("purchases_in_session") > 0, 1).otherwise(0)
        )

        return session_features

    def load_features(self, user_features, item_features, session_features):
        """加载特征到Hive表和特征存储"""
        # 写入Hive分区表
        user_features.write \
            .mode("overwrite") \
            .partitionBy("dt") \
            .format("parquet") \
            .saveAsTable("features.user_features")

        item_features.write \
            .mode("overwrite") \
            .partitionBy("dt") \
            .saveAsTable("features.item_features")

        session_features.write \
            .mode("overwrite") \
            .partitionBy("dt") \
            .saveAsTable("features.session_features")

        # 同时输出到Redis（通过Spark-Redis连接器）
        user_features.write \
            .format("org.apache.spark.sql.redis") \
            .option("table", "user_features") \
            .option("key.column", "user_id") \
            .mode("overwrite") \
            .save()

    def run(self):
        """执行ETL流程"""
        print(f"Running ETL for date: {self.date}")

        # 提取
        raw_df = self.extract_raw_behaviors()

        # 转换
        user_features = self.transform_user_features(raw_df)
        item_features, item_pairs = self.transform_item_features(raw_df)
        session_features = self.transform_session_features(raw_df)

        # 加载
        self.load_features(user_features, item_features, session_features)

        # 计算物品相似度（ItemCF）
        self.calculate_item_similarity(item_pairs)

        print("ETL completed successfully")

    def calculate_item_similarity(self, item_pairs):
        """基于共现计算物品相似度"""
        # 计算每个物品的总出现次数
        item_count = item_pairs.groupBy("item_i").agg(sum("cooccurrence").alias("item_count"))

        # 计算相似度（使用Jaccard相似度）
        similarity_df = item_pairs.join(item_count.alias("a"),
                                       col("item_i") == col("a.item_i")) \
            .join(item_count.alias("b"), col("item_j") == col("b.item_i")) \
            .withColumn(
                "similarity",
                col("cooccurrence") / (col("a.item_count") + col("b.item_count") - col("cooccurrence"))
            ) \
            .select("item_i", "item_j", "similarity")

        # 保存相似度结果
        similarity_df.write \
            .mode("overwrite") \
            .format("parquet") \
            .save("/data/item_similarity/")

        return similarity_df

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, help="ETL date (YYYY-MM-DD)")
    args = parser.parse_args()

    etl = BehaviorETL(args.date)
    etl.run()