
package com.ecommerce.inventory.service;

import com.ecommerce.inventory.model.dto.InventoryDTO;

public interface InventoryCacheService {
    InventoryDTO getFromCache(String skuCode);
    void cacheInventory(InventoryDTO inventory);
    void evictFromCache(String skuCode);
    boolean hasStock(String skuCode, int quantity);
}