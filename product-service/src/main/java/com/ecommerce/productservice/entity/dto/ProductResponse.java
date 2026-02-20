package com.ecommerce.product.model.dto;

import com.ecommerce.product.model.enums.ProductStatus;
import lombok.Builder;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/**
 * 商品查询返回结果
 */
@Data
@Builder
public class ProductResponse {
    private Long id;
    private String name;
    private String description;
    private BigDecimal price;
    private Integer stock;
    private ProductStatus status;

    // 分类信息
    private Long categoryId;
    private String categoryName;

    // 图片信息
    private String mainImageUrl;
    private List<String> galleryImageUrls;

    // 扩展属性
    private Map<String, String> attributes;

    // 时间信息
    private LocalDateTime createTime;
    private LocalDateTime updateTime;

    // 计算折扣率（可选）
    private BigDecimal discountRate;

    // 评分信息（可选）
    private Double averageRating;
    private Integer reviewCount;

    /**
     * 从实体转换
     */
    public static ProductResponse fromEntity(Product product) {
        return ProductResponse.builder()
                .id(product.getId())
                .name(product.getName())
                .description(product.getDescription())
                .price(product.getPrice())
                .stock(product.getStock())
                .status(product.getStatus())
                .categoryId(product.getCategory().getId())
                .categoryName(product.getCategory().getName())
                .mainImageUrl(product.getMainImageUrl())
                .galleryImageUrls(product.getGalleryImageUrls())
                .attributes(product.getAttributes())
                .createTime(product.getCreatedAt())
                .updateTime(product.getUpdatedAt())
                .build();
    }
}