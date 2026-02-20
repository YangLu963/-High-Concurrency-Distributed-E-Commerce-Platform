package com.ecommerce.inventory.exception;

public class InventoryShortageException extends RuntimeException {
    public InventoryShortageException(String message) {
        super(message);
    }
}