import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import shap
import eli5
from eli5.sklearn import PermutationImportance
import lime
import lime.lime_tabular
import warnings
warnings.filterwarnings('ignore')

class ModelExplainer:
    """模型可解释性分析"""

    def __init__(self, model, X_train, feature_names, model_type='xgboost'):
        self.model = model
        self.X_train = X_train
        self.feature_names = feature_names
        self.model_type = model_type

    def explain_with_shap(self, X_explain, output_path=None):
        """使用SHAP解释模型"""

        if self.model_type == 'xgboost':
            # 创建SHAP解释器
            explainer = shap.TreeExplainer(self.model)
            shap_values = explainer.shap_values(X_explain)

            # 全局特征重要性
            shap.summary_plot(shap_values, X_explain, feature_names=self.feature_names, show=False)
            if output_path:
                plt.savefig(f"{output_path}/shap_summary.png", bbox_inches='tight')
            plt.show()

            # 特征重要性条形图
            shap.plots.bar(explainer.shap_values(X_explain)[0], feature_names=self.feature_names)
            if output_path:
                plt.savefig(f"{output_path}/shap_bar.png", bbox_inches='tight')

            # 单个预测的解释
            shap.force_plot(
                explainer.expected_value,
                shap_values[0,:],
                X_explain.iloc[0,:],
                feature_names=self.feature_names,
                matplotlib=True,
                show=False
            )
            if output_path:
                plt.savefig(f"{output_path}/shap_force.png", bbox_inches='tight')

            return shap_values

        elif self.model_type == 'lightfm':
            # LightFM的解释（使用物品和用户嵌入）
            user_features = X_explain['user_features']
            item_features = X_explain['item_features']

            scores = self.model.predict(user_features, item_features)

            # 分析每个特征的贡献
            contributions = []
            for i, feat in enumerate(self.feature_names):
                contrib = user_features[:, i].dot(item_features[:, i])
                contributions.append((feat, contrib))

            return sorted(contributions, key=lambda x: abs(x[1]), reverse=True)

    def get_permutation_importance(self, X_val, y_val):
        """排列重要性"""

        perm = PermutationImportance(self.model, random_state=42).fit(X_val, y_val)

        # 可视化
        eli5.show_weights(perm, feature_names=self.feature_names)

        return perm

    def explain_with_lime(self, X_instance, instance_idx=0):
        """LIME局部解释"""

        # 创建LIME解释器
        explainer = lime.lime_tabular.LimeTabularExplainer(
            self.X_train.values,
            feature_names=self.feature_names,
            class_names=['not_purchase', 'purchase'],
            mode='classification'
        )

        # 解释单个实例
        exp = explainer.explain_instance(
            X_instance.values[instance_idx],
            self.model.predict_proba,
            num_features=10
        )

        # 可视化
        exp.show_in_notebook(show_all=False)

        # 获取解释列表
        explanation_list = exp.as_list()

        return explanation_list

    def feature_interaction_analysis(self, X_sample):
        """特征交互分析"""

        if self.model_type == 'xgboost':
            # 使用SHAP交互值
            explainer = shap.TreeExplainer(self.model)
            shap_interaction = explainer.shap_interaction_values(X_sample)

            # 计算平均交互强度
            interaction_matrix = np.abs(shap_interaction).mean(axis=0)

            # 可视化交互矩阵
            plt.figure(figsize=(12, 10))
            plt.imshow(interaction_matrix, cmap='YlOrRd')
            plt.colorbar()
            plt.xticks(range(len(self.feature_names)), self.feature_names, rotation=45)
            plt.yticks(range(len(self.feature_names)), self.feature_names)
            plt.title("Feature Interaction Strength")
            plt.tight_layout()

            return interaction_matrix

    def generate_explanation_report(self, X_sample, y_sample, output_path):
        """生成完整的解释报告"""

        import os
        os.makedirs(output_path, exist_ok=True)

        # 1. SHAP全局解释
        shap_values = self.explain_with_shap(X_sample, output_path)

        # 2. 排列重要性
        perm_importance = self.get_permutation_importance(X_sample, y_sample)

        # 3. 特征交互分析
        interaction_matrix = self.feature_interaction_analysis(X_sample)

        # 4. 生成文本报告
        with open(f"{output_path}/explanation_report.txt", 'w') as f:
            f.write("MODEL EXPLANATION REPORT\n")
            f.write("="*50 + "\n\n")

            f.write("TOP 10 FEATURES (SHAP):\n")
            mean_shap = np.abs(shap_values).mean(axis=0)
            top_indices = np.argsort(mean_shap)[-10:][::-1]
            for idx in top_indices:
                f.write(f"  {self.feature_names[idx]}: {mean_shap[idx]:.4f}\n")

            f.write("\nFEATURE INTERACTIONS:\n")
            # 找出最强的特征交互对
            n_features = len(self.feature_names)
            interactions = []
            for i in range(n_features):
                for j in range(i+1, n_features):
                    interactions.append((self.feature_names[i], self.feature_names[j],
                                        interaction_matrix[i,j]))

            interactions.sort(key=lambda x: x[2], reverse=True)
            for i in range(min(10, len(interactions))):
                f.write(f"  {interactions[i][0]} x {interactions[i][1]}: {interactions[i][2]:.4f}\n")

        print(f"Explanation report saved to {output_path}")

def analyze_cold_start(model, user_features, item_features, new_users=None, new_items=None):
    """分析冷启动问题"""

    if new_users is None:
        # 模拟新用户（所有特征为平均值或0）
        new_users = np.zeros_like(user_features[:5])

    if new_items is None:
        # 模拟新物品
        new_items = np.zeros_like(item_features[:5])

    results = {
        'existing_user_existing_item': [],
        'new_user_existing_item': [],
        'existing_user_new_item': [],
        'new_user_new_item': []
    }

    # 现有用户-现有物品
    for i in range(min(10, len(user_features))):
        for j in range(min(10, len(item_features))):
            score = model.predict(user_features[i:i+1], item_features[j:j+1])
            results['existing_user_existing_item'].append(score[0])

    # 新用户-现有物品
    for i in range(min(5, len(new_users))):
        for j in range(min(10, len(item_features))):
            score = model.predict(new_users[i:i+1], item_features[j:j+1])
            results['new_user_existing_item'].append(score[0])

    # 现有用户-新物品
    for i in range(min(10, len(user_features))):
        for j in range(min(5, len(new_items))):
            score = model.predict(user_features[i:i+1], new_items[j:j+1])
            results['existing_user_new_item'].append(score[0])

    # 新用户-新物品
    for i in range(min(5, len(new_users))):
        for j in range(min(5, len(new_items))):
            score = model.predict(new_users[i:i+1], new_items[j:j+1])
            results['new_user_new_item'].append(score[0])

    # 计算平均分数
    summary = {}
    for k, v in results.items():
        summary[k] = np.mean(v) if v else 0

    # 冷启动衰减分析
    cold_start_gap = {
        'user_cold_start': summary['new_user_existing_item'] - summary['existing_user_existing_item'],
        'item_cold_start': summary['existing_user_new_item'] - summary['existing_user_existing_item'],
        'double_cold_start': summary['new_user_new_item'] - summary['existing_user_existing_item']
    }

    return summary, cold_start_gap