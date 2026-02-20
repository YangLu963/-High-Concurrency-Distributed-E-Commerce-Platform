package com.ecommerce.inventory.service.impl;

import com.ecommerce.inventory.model.entity.Inventory;
import com.ecommerce.inventory.model.dto.DeductRequest;
import com.ecommerce.inventory.model.dto.ReserveRequest;
import com.ecommerce.inventory.repository.InventoryRepository;
import com.ecommerce.inventory.service.InventoryService;
import com.ecommerce.inventory.exception.InventoryShortageException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class InventoryServiceImpl implements InventoryService {

    private final InventoryRepository inventoryRepository;

    public InventoryServiceImpl(InventoryRepository inventoryRepository) {
        this.inventoryRepository = inventoryRepository;
    }

    @Override
    @Transactional
    public boolean deductInventory(DeductRequest request) {
        Inventory inventory = inventoryRepository.findBySkuCode(request.getSkuCode())
                .orElseThrow(() -> new RuntimeException("Inventory not found"));

        if (inventory.getAvailableQuantity() < request.getQuantity()) {
            throw new InventoryShortageException("Insufficient inventory for SKU: " + request.getSkuCode());
        }

        inventory.setAvailableQuantity(inventory.getAvailableQuantity() - request.getQuantity());
        inventory.setTotalQuantity(inventory.getTotalQuantity() - request.getQuantity());
        inventoryRepository.save(inventory);

        return true;
    }

    @Override
    @Transactional
    public boolean reserveInventory(ReserveRequest request) {
        // Similar implementation with reservation logic
        // ...
    }
}