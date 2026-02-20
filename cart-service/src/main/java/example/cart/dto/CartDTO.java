// CartDTO.java
package com.example.cart.dto;

import com.example.cart.entity.CartItem;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class CartDTO {
    private String userId;
    private List<CartItem> items;
    private BigDecimal totalPrice;
    private LocalDateTime createdAt;
}

// CartItemDTO.java
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