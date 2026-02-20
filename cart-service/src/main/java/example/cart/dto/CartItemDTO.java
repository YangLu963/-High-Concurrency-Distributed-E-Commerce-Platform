
package com.example.cart.dto;

import lombok.Data;

import javax.validation.constraints.Min;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import java.math.BigDecimal;

@Data
public class CartItemDTO {
    @NotBlank
    private String sku;

    @NotBlank
    private String name;

    @NotNull
    private BigDecimal price;

    @Min(1)
    private int quantity;

    private String imageUrl;
}
