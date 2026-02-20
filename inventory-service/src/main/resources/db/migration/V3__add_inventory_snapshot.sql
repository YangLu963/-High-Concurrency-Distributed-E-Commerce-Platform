CREATE TABLE inventory_snapshot (
                                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                                    sku_code VARCHAR(50) NOT NULL COMMENT 'SKU编码',
                                    total_quantity INT NOT NULL COMMENT '总库存量',
                                    available_quantity INT NOT NULL COMMENT '可用库存量',
                                    reserved_quantity INT NOT NULL COMMENT '预占库存量',
                                    snapshot_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '快照时间',
                                    INDEX idx_sku (sku_code),
                                    INDEX idx_time (snapshot_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存每日快照表';

-- 创建存储过程用于生成快照
DELIMITER //
CREATE PROCEDURE generate_inventory_snapshot()
BEGIN
INSERT INTO inventory_snapshot (
    sku_code,
    total_quantity,
    available_quantity,
    reserved_quantity
)
SELECT
    sku_code,
    total_quantity,
    available_quantity,
    reserved_quantity
FROM inventory;
END//
DELIMITER ;
