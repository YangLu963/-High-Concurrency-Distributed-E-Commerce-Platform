package com.ecommerce.inventory.scheduler;

import com.ecommerce.inventory.repository.InventoryRepository;
import com.ecommerce.inventory.repository.InventoryLogRepository;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class InventorySnapshotJob {

    private final InventoryRepository inventoryRepository;
    private final InventoryLogRepository logRepository;

    public InventorySnapshotJob(InventoryRepository inventoryRepository,
                                InventoryLogRepository logRepository) {
        this.inventoryRepository = inventoryRepository;
        this.logRepository = logRepository;
    }

    @Scheduled(cron = "0 0 0 * * ?") // Run daily at midnight
    @Transactional
    public void takeDailySnapshot() {
        // Implementation to taake daily inventory snapshot
    }
}