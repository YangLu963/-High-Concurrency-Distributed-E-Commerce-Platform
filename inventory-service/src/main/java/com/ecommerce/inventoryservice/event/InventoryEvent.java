package com.ecommerce.inventory.event;

import com.ecommerce.inventory.model.dto.InventoryDTO;
import java.time.LocalDateTime;

public class InventoryEvent {
    private final String eventType;
    private final InventoryDTO inventory;
    private final LocalDateTime eventTime;

    public InventoryEvent(String eventType, InventoryDTO inventory) {
        this.eventType = eventType;
        this.inventory = inventory;
        this.eventTime = LocalDateTime.now();
    }

    // Getters
    public String getEventType() { return eventType; }
    public InventoryDTO getInventory() { return inventory; }
    public LocalDateTime getEventTime() { return eventTime; }
}