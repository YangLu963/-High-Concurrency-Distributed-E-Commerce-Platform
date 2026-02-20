CREATE TABLE inventory_log (
                               id BIGINT AUTO_INCREMENT PRIMARY KEY,
                               sku_code VARCHAR(50) NOT NULL COMMENT 'SKU编码',
                               operation_type VARCHAR(20) NOT NULL COMMENT '操作类型(DEDUCT/ADD/RESERVE/CANCEL)',
                               quantity INT NOT NULL COMMENT '操作数量',
                               before_quantity INT COMMENT '操作前库存',
                               after_quantity INT COMMENT '操作后库存',
                               reference_id VARCHAR(50) NOT NULL COMMENT '关联业务ID',
                               operator VARCHAR(50) COMMENT '操作人',
                               created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                               INDEX idx_sku (sku_code),
                               INDEX idx_ref (reference_id),
                               INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存操作日志表';

-- 添加日志记录触发器
DELIMITER //
CREATE TRIGGER after_inventory_update
    AFTER UPDATE ON inventory
    FOR EACH ROW
BEGIN
    IF NEW.available_quantity != OLD.available_quantity THEN
        INSERT INTO inventory_log (
            sku_code,
            operation_type,
            quantity,
            before_quantity,
            after_quantity,
            reference_id,
            operator
        ) VALUES (
            NEW.sku_code,
            CASE
                WHEN NEW.available_quantity < OLD.available_quantity THEN 'DEDUCT'
                ELSE 'ADD'
END,
ABS(NEW.available_quantity - OLD.available_quantity),
OLD.available_quantity,
NEW.available_quantity,
'SYSTEM',
'AUTO'
);
END IF;
END//
DELIMITER ;