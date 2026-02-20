
package com.ecommerce.inventory.model.dto;

import lombok.Data;

@Data
public class InventoryAlertDTO {
    private String skuCode;
    private Integer currentQuantity;
    private Integer threshold;
    private String alertType;
}