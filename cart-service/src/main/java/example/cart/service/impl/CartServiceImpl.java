
// CartServiceImpl.java (新增方法实现)
@Transactional
public CartDTO updateItemQuantity(String userId, String sku, int quantity) {
    if (quantity <= 0) {
        throw new IllegalArgumentException("Quantity must be positive");
    }

    RLock lock = redissonClient.getLock("cart:" + userId);
    try {
        lock.lock();

        Cart cart = cartRepo.findById(userId)
                .orElseThrow(() -> new NotFoundException("Cart not found"));

        cart.updateItemQuantity(sku, quantity);
        cartRepo.saveCart(cart);

        kafkaTemplate.send("cart-events",
                new CartItemUpdatedEvent(userId, sku, quantity));

        return convertToDTO(cart);
    } finally {
        lock.unlock();
    }
}

@Transactional
public CartDTO applyCoupon(String userId, String couponCode) {
    PromotionResponse promo = promotionClient.validateCoupon(
            new CouponValidationRequest(userId, couponCode));

    if (!promo.isValid()) {
        throw new CouponException(couponCode, "Invalid or expired coupon");
    }

    Cart cart = cartRepo.findById(userId)
            .orElseThrow(() -> new NotFoundException("Cart not found"));

    Cart discountedCart = promotionCalculator.applyCartLevelPromotions(cart, couponCode);
    cartRepo.saveCart(discountedCart);

    return convertToDTO(discountedCart);
}