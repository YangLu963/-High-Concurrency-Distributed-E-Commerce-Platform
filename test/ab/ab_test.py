
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import redis
import json
import logging
from typing import Dict, List, Optional, Tuple
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ABTestManager:
    """AB测试管理器"""

    def __init__(self, redis_host='localhost', redis_port=6379, db=1):
        self.redis = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=db,
            decode_responses=True
        )
        self.experiments = {}
        self.load_experiments()

    def load_experiments(self):
        """加载实验配置"""
        experiments_key = "ab:experiments"
        experiments_json = self.redis.get(experiments_key)

        if experiments_json:
            self.experiments = json.loads(experiments_json)
        else:
            # 默认实验配置
            self.experiments = {
                "ranking_model_v2": {
                    "name": "Ranking Model v2",
                    "description": "测试新的排序模型",
                    "start_date": "2024-01-01",
                    "end_date": "2024-03-01",
                    "variants": {
                        "control": {"weight": 50, "model": "xgboost_v1"},
                        "treatment": {"weight": 50, "model": "xgboost_v2"}
                    },
                    "metrics": ["ctr", "purchase_rate", "revenue_per_user"],
                    "status": "active"
                },
                "diversity_strategy": {
                    "name": "多样性策略",
                    "description": "测试MMR多样性参数",
                    "start_date": "2024-01-15",
                    "end_date": "2024-02-15",
                    "variants": {
                        "control": {"weight": 33, "lambda": 0.5},
                        "treatment_a": {"weight": 33, "lambda": 0.3},
                        "treatment_b": {"weight": 34, "lambda": 0.7}
                    },
                    "metrics": ["ctr", "diversity_score", "session_length"],
                    "status": "active"
                },
                "cold_start_strategy": {
                    "name": "冷启动策略",
                    "description": "测试新用户推荐算法",
                    "start_date": "2024-02-01",
                    "end_date": "2024-03-01",
                    "variants": {
                        "control": {"weight": 50, "strategy": "popular"},
                        "treatment": {"weight": 50, "strategy": "content_based"}
                    },
                    "metrics": ["new_user_ctr", "new_user_retention"],
                    "status": "draft"
                }
            }
            self.save_experiments()

    def save_experiments(self):
        """保存实验配置"""
        self.redis.set("ab:experiments", json.dumps(self.experiments))

    def assign_variant(self, user_id: str, experiment_id: str) -> str:
        """为用户分配实验组"""
        experiment = self.experiments.get(experiment_id)
        if not experiment or experiment['status'] != 'active':
            return 'control'

        # 使用一致性哈希确保同一用户始终分配到同一组
        hash_value = int(hashlib.md5(f"{user_id}:{experiment_id}".encode()).hexdigest(), 16)
        total_weight = sum(v['weight'] for v in experiment['variants'].values())
        hash_mod = hash_value % total_weight

        cumulative = 0
        for variant_name, variant_config in experiment['variants'].items():
            cumulative += variant_config['weight']
            if hash_mod < cumulative:
                return variant_name

        return 'control'

    def get_experiment_config(self, experiment_id: str, variant: str) -> Dict:
        """获取实验配置"""
        experiment = self.experiments.get(experiment_id, {})
        return experiment.get('variants', {}).get(variant, {})

    def record_exposure(self, user_id: str, experiment_id: str,
                       variant: str, request_id: str):
        """记录实验曝光"""
        key = f"ab:exposure:{experiment_id}:{variant}"
        self.redis.hincrby(key, "count", 1)

        # 记录用户归属
        user_exp_key = f"ab:user:{user_id}"
        self.redis.hset(user_exp_key, experiment_id,
                       json.dumps({"variant": variant, "request_id": request_id}))
        self.redis.expire(user_exp_key, 86400 * 30)  # 30天过期

    def record_conversion(self, user_id: str, experiment_id: str,
                         event_type: str, value: float = 1.0):
        """记录转化事件"""
        # 获取用户所属实验组
        user_exp_key = f"ab:user:{user_id}"
        exp_data = self.redis.hget(user_exp_key, experiment_id)

        if not exp_data:
            return

        exp_info = json.loads(exp_data)
        variant = exp_info['variant']

        # 记录转化
        key = f"ab:conversion:{experiment_id}:{variant}:{event_type}"
        self.redis.hincrbyfloat(key, "sum", value)
        self.redis.hincrby(key, "count", 1)

        # 记录用户转化
        user_conv_key = f"ab:user_conv:{user_id}"
        self.redis.hset(user_conv_key, f"{experiment_id}:{event_type}",
                       json.dumps({"variant": variant, "value": value, "time": datetime.now().isoformat()}))

    def get_experiment_results(self, experiment_id: str) -> Dict:
        """获取实验结果"""
        experiment = self.experiments.get(experiment_id, {})
        if not experiment:
            return {}

        results = {
            "experiment_id": experiment_id,
            "name": experiment['name'],
            "status": experiment['status'],
            "variants": {}
        }

        for variant in experiment['variants'].keys():
            # 获取曝光数据
            exposure_key = f"ab:exposure:{experiment_id}:{variant}"
            exposures = self.redis.hgetall(exposure_key)
            exposure_count = int(exposures.get('count', 0))

            variant_result = {
                "exposure_count": exposure_count,
                "metrics": {}
            }

            # 获取各指标数据
            for metric in experiment['metrics']:
                conv_key = f"ab:conversion:{experiment_id}:{variant}:{metric}"
                conv_data = self.redis.hgetall(conv_key)

                conv_sum = float(conv_data.get('sum', 0))
                conv_count = int(conv_data.get('count', 0))

                if exposure_count > 0:
                    variant_result['metrics'][metric] = {
                        "value": conv_sum / exposure_count,
                        "total": conv_sum,
                        "count": conv_count
                    }

            results['variants'][variant] = variant_result

        # 计算统计显著性
        results = self.calculate_significance(results)

        return results

    def calculate_significance(self, results: Dict) -> Dict:
        """计算统计显著性"""
        variants = results['variants']

        if 'control' not in variants or len(variants) < 2:
            return results

        control = variants['control']

        for variant_name, variant_data in variants.items():
            if variant_name == 'control':
                continue

            for metric, metric_data in variant_data.get('metrics', {}).items():
                control_metric = control.get('metrics', {}).get(metric, {})

                # 获取数据
                control_value = control_metric.get('value', 0)
                treatment_value = metric_data.get('value', 0)
                control_count = control.get('exposure_count', 0)
                treatment_count = variant_data.get('exposure_count', 0)

                # 计算lift
                if control_value > 0:
                    lift = (treatment_value - control_value) / control_value
                else:
                    lift = 0

                # 进行t检验（简化版）
                # 假设二项分布，使用z检验
                if control_count > 0 and treatment_count > 0:
                    #  pooled standard error
                    p_pool = (control_value * control_count + treatment_value * treatment_count) / (control_count + treatment_count)
                    se = np.sqrt(p_pool * (1 - p_pool) * (1/control_count + 1/treatment_count))

                    if se > 0:
                        z_score = (treatment_value - control_value) / se
                        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
                    else:
                        z_score = 0
                        p_value = 1.0

                    # 判断是否显著
                    is_significant = p_value < 0.05
                else:
                    z_score = 0
                    p_value = 1.0
                    is_significant = False

                # 添加到结果
                if 'significance' not in variant_data:
                    variant_data['significance'] = {}

                variant_data['significance'][metric] = {
                    "lift": lift,
                    "z_score": z_score,
                    "p_value": p_value,
                    "is_significant": is_significant
                }

        return results

    def create_experiment(self, experiment_config: Dict):
        """创建新实验"""
        experiment_id = experiment_config['id']
        self.experiments[experiment_id] = experiment_config
        self.save_experiments()
        logger.info(f"Created experiment: {experiment_id}")

    def start_experiment(self, experiment_id: str):
        """启动实验"""
        if experiment_id in self.experiments:
            self.experiments[experiment_id]['status'] = 'active'
            self.save_experiments()
            logger.info(f"Started experiment: {experiment_id}")

    def stop_experiment(self, experiment_id: str):
        """停止实验"""
        if experiment_id in self.experiments:
            self.experiments[experiment_id]['status'] = 'completed'
            self.save_experiments()
            logger.info(f"Stopped experiment: {experiment_id}")

    def analyze_results(self, experiment_id: str, output_path: str = None):
        """分析并可视化结果"""
        results = self.get_experiment_results(experiment_id)
        experiment = self.experiments.get(experiment_id, {})

        print(f"\n{'='*60}")
        print(f"AB Test Results: {experiment.get('name')}")
        print(f"Experiment ID: {experiment_id}")
        print(f"Status: {experiment.get('status')}")
        print(f"{'='*60}\n")

        # 打印各变体结果
        for variant, data in results['variants'].items():
            print(f"\nVariant: {variant.upper()}")
            print(f"  Exposures: {data['exposure_count']}")

            for metric, metric_data in data.get('metrics', {}).items():
                print(f"  {metric}: {metric_data['value']:.4f} (n={metric_data['count']})")

            # 打印显著性
            for metric, sig_data in data.get('significance', {}).items():
                sig_star = "***" if sig_data['is_significant'] else ""
                print(f"  {metric} lift: {sig_data['lift']*100:.2f}% {sig_star} (p={sig_data['p_value']:.4f})")

        # 生成图表
        if output_path:
            self.plot_results(results, experiment, output_path)

        return results

    def plot_results(self, results: Dict, experiment: Dict, output_path: str):
        """绘制结果图表"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        metrics = experiment.get('metrics', [])
        variants = list(results['variants'].keys())

        # 指标对比图
        for i, metric in enumerate(metrics[:4]):
            ax = axes[i//2, i%2]

            values = []
            errors = []

            for variant in variants:
                metric_data = results['variants'][variant].get('metrics', {}).get(metric, {})
                value = metric_data.get('value', 0)
                count = metric_data.get('count', 0)

                values.append(value)

                # 标准误
                if count > 0:
                    se = np.sqrt(value * (1 - value) / count)
                    errors.append(se)
                else:
                    errors.append(0)

            bars = ax.bar(variants, values, yerr=errors, capsize=5)

            # 标注显著性
            for j, variant in enumerate(variants):
                if variant != 'control':
                    sig_data = results['variants'][variant].get('significance', {}).get(metric, {})
                    if sig_data.get('is_significant'):
                        bars[j].set_color('green')
                        ax.text(j, values[j] + errors[j] + 0.01, '*',
                               ha='center', va='bottom', fontsize=16)

            ax.set_title(f'{metric}')
            ax.set_ylabel('Value')

        plt.tight_layout()
        plt.savefig(f"{output_path}/ab_test_{experiment['id']}.png")
        plt.show()

class ABTestClient:
    """AB测试客户端（用于API服务）"""

    def __init__(self, redis_host='localhost', redis_port=6379):
        self.redis = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        self.manager = ABTestManager(redis_host, redis_port)

    def get_variant(self, user_id: str, experiment_id: str) -> Tuple[str, Dict]:
        """获取用户所属实验组"""
        variant = self.manager.assign_variant(user_id, experiment_id)
        config = self.manager.get_experiment_config(experiment_id, variant)
        return variant, config

    def track_exposure(self, user_id: str, experiment_id: str,
                      variant: str, request_id: str):
        """跟踪曝光"""
        self.manager.record_exposure(user_id, experiment_id, variant, request_id)

    def track_conversion(self, user_id: str, experiment_id: str,
                        event_type: str, value: float = 1.0):
        """跟踪转化"""
        self.manager.record_conversion(user_id, experiment_id, event_type, value)

    def get_active_experiments(self) -> List[str]:
        """获取进行中的实验"""
        experiments = self.manager.experiments
        return [exp_id for exp_id, exp in experiments.items()
                if exp.get('status') == 'active']

if __name__ == "__main__":
    # 示例用法
    manager = ABTestManager()

    # 模拟流量分配
    for i in range(1000):
        user_id = f"user_{i}"
        variant = manager.assign_variant(user_id, "ranking_model_v2")
        manager.record_exposure(user_id, "ranking_model_v2", variant, f"req_{i}")

        # 模拟点击（10%概率）
        if np.random.random() < 0.1:
            manager.record_conversion(user_id, "ranking_model_v2", "click")

        # 模拟购买（1%概率）
        if np.random.random() < 0.01:
            manager.record_conversion(user_id, "ranking_model_v2", "purchase",
                                     value=np.random.uniform(10, 100))

    # 分析结果
    results = manager.analyze_results("ranking_model_v2", output_path="./plots")
    print(json.dumps(results, indent=2))