package com.ecommerce.inventory.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.scheduling.annotation.EnableAsync;

@Configuration
@EnableAsync
public class InventoryEventConfig {

    @Bean
    public InventoryEventPublisher inventoryEventPublisher(ApplicationEventPublisher applicationEventPublisher) {
        return new InventoryEventPublisher(applicationEventPublisher);
    }
}