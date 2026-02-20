@Service
@RequiredArgsConstructor
@Slf4j
public class ProductServiceImpl implements ProductService {
    private final ProductRepository productRepository;
    private final ProductEsRepository esRepository;
    private final RedisTemplate<String, Object> redisTemplate;

    @Override
    @Transactional
    public ProductResponse createProduct(ProductRequest request) {
        Product product = Product.builder()
                .name(request.getName())
                .description(request.getDescription())
                .price(request.getPrice())
                .stock(request.getStock())
                .status(ProductStatus.AVAILABLE)
                .category(request.getCategory())
                .build();

        Product savedProduct = productRepository.save(product);
        esRepository.save(savedProduct); // 同步到ES
        return ProductResponse.fromEntity(savedProduct);
    }

    @Override
    @CacheEvict(value = "products", key = "#id")
    public ProductResponse updateProduct(Long id, ProductRequest request) {
        Product product = productRepository.findById(id)
                .orElseThrow(() -> new ProductNotFoundException(id));

        product.setName(request.getName());
        product.setDescription(request.getDescription());
        product.setPrice(request.getPrice());
        return ProductResponse.fromEntity(productRepository.save(product));
    }

    @Override
    @Cacheable(value = "products", key = "#productId")
    public ProductResponse getProduct(Long productId) {
        return productRepository.findById(productId)
                .map(ProductResponse::fromEntity)
                .orElseThrow(() -> new ProductNotFoundException(productId));
    }
}