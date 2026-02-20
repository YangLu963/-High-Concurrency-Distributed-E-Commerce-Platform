public interface ProductService {
    ProductResponse createProduct(ProductRequest request);
    ProductResponse updateProduct(Long id, ProductRequest request);
    Page<ProductResponse> searchProducts(String keyword, Pageable pageable);
    void decreaseStock(Long productId, int quantity);
    void increaseStock(Long productId, int quantity);
    List<PriceHistoryDTO> getPriceHistory(Long productId);
}