// CartController.java
package com.example.cart.controller;

import com.example.cart.dto.CartDTO;
import com.example.cart.dto.CartItemDTO;
import com.example.cart.service.CartService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;

@RestController
@RequestMapping("/carts")
public class CartController {
    private final CartService cartService;

    @Autowired
    public CartController(CartService cartService) {
        this.cartService = cartService;
    }

    @PostMapping("/{userId}/items")
    public ResponseEntity<CartDTO> addItem(
            @PathVariable String userId,
            @Valid @RequestBody CartItemDTO itemDTO) {
        return ResponseEntity.ok(cartService.addItem(userId, itemDTO));
    }

    @GetMapping("/{userId}")
    public ResponseEntity<CartDTO> getCart(@PathVariable String userId) {
        return ResponseEntity.ok(cartService.getCart(userId));
    }

    @DeleteMapping("/{userId}/items/{sku}")
    public ResponseEntity<Void> removeItem(
            @PathVariable String userId,
            @PathVariable String sku) {
        cartService.removeItem(userId, sku);
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/{userId}/checkout")
    public ResponseEntity<Void> checkout(@PathVariable String userId) {
        cartService.checkout(userId);
        return ResponseEntity.accepted().build();
    }
}