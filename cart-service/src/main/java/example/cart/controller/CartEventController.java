// CartEventController.java
package com.example.cart.controller;

import com.example.cart.event.CartEvent;
import com.example.cart.service.CartEventService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Flux;

@RestController
@RequestMapping("/cart-events")
public class CartEventController {
    private final CartEventService eventService;

    @Autowired
    public CartEventController(CartEventService eventService) {
        this.eventService = eventService;
    }

    @GetMapping(value = "/{userId}/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<CartEvent>> streamCartEvents(
            @PathVariable String userId) {
        return eventService.getEventStream(userId);
    }

    @GetMapping("/{userId}/history")
    public Flux<CartEvent> getCartEventHistory(
            @PathVariable String userId,
            @RequestParam(defaultValue = "24h") String duration) {
        return eventService.getEventHistory(userId, duration);
    }
}