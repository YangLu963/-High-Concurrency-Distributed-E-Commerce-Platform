package com.ecommerce.inventory.controller;

import com.ecommerce.inventory.model.dto.InventoryDTO;
import com.ecommerce.inventory.model.dto.DeductRequest;
import com.ecommerce.inventory.service.InventoryService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/inventory")
public class InventoryController {

    private final InventoryService inventoryService;

    public InventoryController(InventoryService inventoryService) {
        this.inventoryService = inventoryService;
    }

    @GetMapping("/{skuCode}")
    public ResponseEntity<InventoryDTO> getInventory(@PathVariable String skuCode) {
        // Implementation
    }

    @PostMapping("/deduct")
    public ResponseEntity<Boolean> deductInventory(@RequestBody DeductRequest request) {
        boolean result = inventoryService.deductInventory(request);
        return ResponseEntity.ok(result);
    }
}