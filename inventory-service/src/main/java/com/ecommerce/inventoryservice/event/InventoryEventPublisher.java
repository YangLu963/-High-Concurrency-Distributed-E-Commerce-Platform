package com.ecommerce.inventory.event;

import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Component;

@Component
public class InventoryEventPublisher {

    private final ApplicationEventPublisher eventPublisher;

    public InventoryEventPublisher(ApplicationEventPublisher eventPublisher) {
        this.eventPublisher = eventPublisher;
    }

    public void publishInventoryChanged(InventoryDTO inventory, String eventType) {
        InventoryEvent event = new InventoryEvent(eventType, inventory);
        eventPublisher.publishEvent(event);
    }
}