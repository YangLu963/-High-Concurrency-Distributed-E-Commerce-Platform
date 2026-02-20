package com.ecommerce.inventory.model.entity;

import javax.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "inventory", indexes = {
        @Index(name = "idx_sku", columnList = "skuCode"),
        @Index(name = "idx_product", columnList = "productId")
})
public class Inventory {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String skuCode;

    @Column(nullable = false)
    private Long productId;

    @Column(nullable = false)
    private Integer totalQuantity;

    @Column(nullable = false)
    private Integer availableQuantity;

    @Column(nullable = false)
    private Integer reservedQuantity;

    @Column(nullable = false)
    private Integer version;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    @Column(nullable = false)
    private LocalDateTime updatedAt;

    // Getters and Setters
    // Constructors
}