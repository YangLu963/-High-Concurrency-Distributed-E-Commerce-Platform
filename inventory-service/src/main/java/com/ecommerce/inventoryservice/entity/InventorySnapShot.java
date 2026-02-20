
package com.ecommerce.inventory.model.entity;

import javax.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "inventory_snapshot")
public class InventorySnapshot {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String skuCode;

    @Column(nullable = false)
    private Integer totalQuantity;

    @Column(nullable = false)
    private Integer availableQuantity;

    @Column(nullable = false)
    private Integer reservedQuantity;

    @Column(nullable = false)
    private LocalDateTime snapshotTime;

    // Getters and Setters
}