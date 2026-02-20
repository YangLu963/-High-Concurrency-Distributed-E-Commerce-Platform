package com.ecommerce.product.model.dto;

import jakarta.validation.constraints.*;
import lombok.Data;
import java.math.BigDecimal;
import java.util.Map;

/**
 * 商品创建/更新请求参数
 */
@Data
public class ProductRequest {
    @NotBlank(message = "商品名称不能为空")
    @Size(max = 100, message = "商品名称最长100个字符")
    private String name;

    @Size(max = 1000, message = "商品描述最长1000个字符")
    private String description;

    @NotNull(message = "价格不能为空")
    @DecimalMin(value = "0.01", message = "价格必须大于0")
    @Digits(integer = 10, fraction = 2, message = "价格格式不正确")
    private BigDecimal price;

    @NotNull(message = "库存不能为空")
    @Min(value = 0, message = "库存不能为负数")
    private Integer stock;

    @NotNull(message = "分类ID不能为空")
    private Long categoryId;

    // 商品状态（默认上架）
    private ProductStatus status = ProductStatus.AVAILABLE;

    // 商品扩展属性（颜色、尺寸等）
    private Map<@NotBlank String, @NotBlank String> attributes;

    // 商品主图URL
    @URL(message = "图片URL格式不正确")
    private String mainImageUrl;

    // 商品轮播图URL列表
    private List<@URL String> galleryImageUrls;
}