
package com.ecommerce.inventory.model.dto;

import lombok.Data;

@Data
public class DeductRequest {
    private String skuCode;
    private Integer quantity;
    private String orderId;
}