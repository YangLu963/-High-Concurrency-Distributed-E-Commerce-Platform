
package com.ecommerce.inventory.model.dto;

import lombok.Data;

@Data
public class AdjustmentDTO {
    private String skuCode;
    private Integer adjustment;
    private String reason;
    private String operator;
}
