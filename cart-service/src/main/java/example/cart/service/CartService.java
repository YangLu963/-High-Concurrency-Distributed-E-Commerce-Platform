
public interface CartService {
    // 原有方法
    CartDTO addItem(String userId, CartItemDTO itemDTO);
    CartDTO getCart(String userId);
    void removeItem(String userId, String sku);
    void checkout(String userId);

    // 新增方法
    CartDTO updateItemQuantity(String userId, String sku, int quantity);
    CartDTO applyCoupon(String userId, String couponCode);
    CartDTO mergeCarts(String userId, String sessionId);
    List<CartDTO> getAbandonedCarts(Duration threshold);
}