-- 价格历史表
CREATE TABLE price_history (
                               id BIGSERIAL PRIMARY KEY,
                               product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                               old_price DECIMAL(19,2) NOT NULL,
                               new_price DECIMAL(19,2) NOT NULL,
                               change_reason VARCHAR(255),
                               changed_by VARCHAR(50) NOT NULL,
                               change_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                               operation_type VARCHAR(20) NOT NULL -- PRICE_UPDATE/DISCOUNT/COST_CHANGE
);

-- 为查询优化创建索引
CREATE INDEX idx_price_history_product ON price_history(product_id);
CREATE INDEX idx_price_history_time ON price_history(change_time);

-- 添加外键约束日志记录（可选）
COMMENT ON TABLE price_history IS '商品价格变更历史表';
COMMENT ON COLUMN price_history.operation_type IS '操作类型: 调价/折扣/成本变动';
