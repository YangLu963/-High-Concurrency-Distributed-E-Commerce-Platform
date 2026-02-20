
package com.ecommerce.inventory.event.listener;
import com.ecommerce.inventory.event.InventoryEvent;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;
import org.springframework.context.event.EventListener;




@Component
public class InventoryEventListener {

    @Async
    @EventListener
    public void handleInventoryEvent(InventoryEvent event) {
        // Implement event handling logic
        System.out.println("Received inventory event: " + event.getEventType() +
                " for SKU: " + event.getInventory().getSkuCode());
    }
}