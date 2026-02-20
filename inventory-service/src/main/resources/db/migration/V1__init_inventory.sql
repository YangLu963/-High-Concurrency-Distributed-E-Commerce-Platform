CREATE TABLE inventory (
                           id BIGINT AUTO_INCREMENT PRIMARY KEY,
                           sku_code VARCHAR(50) NOT NULL UNIQUE,
                           product_id BIGINT NOT NULL,
                           total_quantity INT NOT NULL,
                           available_quantity INT NOT NULL,
                           reserved_quantity INT NOT NULL DEFAULT 0,
                           version INT NOT NULL DEFAULT 0,
                           created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                           updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                           INDEX idx_sku (sku_code),
                           INDEX idx_product (product_id)
);