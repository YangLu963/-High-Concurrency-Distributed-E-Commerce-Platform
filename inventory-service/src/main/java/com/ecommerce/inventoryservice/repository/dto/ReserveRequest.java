package com.ecommerce.inventory.model.dto;

import lombok.Data;

@Data
public class ReserveRequest {
    private String skuCode;
    private Integer quantity;
    private String reservationId;
}