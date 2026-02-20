
package com.ecommerce.inventory.service;

import com.ecommerce.inventory.model.dto.*;

public interface InventoryService {
    InventoryDTO getInventory(String skuCode);
    boolean deductInventory(DeductRequest request);
    boolean reserveInventory(ReserveRequest request);
    boolean cancelReservation(ReserveRequest request);
    boolean adjustInventory(AdjustmentDTO adjustment);
    void processInventoryAlert(InventoryAlertDTO alert);
}