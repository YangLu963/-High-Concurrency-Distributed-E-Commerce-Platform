package com.ecommerce.inventory.model.dto;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class InventoryDTO {
    private String skuCode;
    private Long productId;
    private Integer totalQuantity;
    private Integer availableQuantity;
    private Integer reservedQuantity;
    private LocalDateTime lastUpdated;
}