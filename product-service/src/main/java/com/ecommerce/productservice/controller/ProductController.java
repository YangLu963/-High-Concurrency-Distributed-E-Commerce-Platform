2@RestController
@RequestMapping("/api/products")
@RequiredArgsConstructor
public class ProductController {
    private final ProductService productService;

    @PostMapping
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<ProductResponse> createProduct(
            @Valid @RequestBody ProductRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(productService.createProduct(request));
    }

    @GetMapping("/search")
    public ResponseEntity<Page<ProductResponse>> searchProducts(
            @RequestParam String keyword,
            @PageableDefault(sort = "price", direction = DESC) Pageable pageable) {
        return ResponseEntity.ok(productService.searchProducts(keyword, pageable));
    }

    @PostMapping("/{id}/stock/decrease")
    public ResponseEntity<Void> decreaseStock(
            @PathVariable Long id,
            @RequestParam int quantity) {
        productService.decreaseStock(id, quantity);
        return ResponseEntity.ok().build();
    }
}