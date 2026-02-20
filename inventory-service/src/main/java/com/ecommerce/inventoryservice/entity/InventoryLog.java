
package com.ecommerce.inventory.model.entity;

import javax.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "inventory_log")
public class InventoryLog {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String skuCode;

    @Column(nullable = false)
    private String operationType;

    @Column(nullable = false)
    private Integer quantity;

    @Column(nullable = false)
    private String referenceId;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    @Column(nullable = false)
    private String operator;

    // Getters and Setters
}