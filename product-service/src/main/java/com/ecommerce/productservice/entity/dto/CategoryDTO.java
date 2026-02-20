package com.ecommerce.product.model.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.*;
import lombok.Data;

/**
 * 商品分类数据传输对象
 */
@Data
@Schema(description = "商品分类信息")
public class CategoryDTO {
    @Schema(description = "分类ID", example = "1")
    private Long id;

    @NotBlank(message = "分类名称不能为空")
    @Size(max = 50, message = "分类名称最长50个字符")
    @Schema(description = "分类名称", example = "电子产品")
    private String name;

    @URL(message = "图标URL格式不正确")
    @Schema(description = "分类图标URL", example = "https://example.com/icon.png")
    private String iconUrl;

    @Schema(description = "关联商品数量", accessMode = READ_ONLY)
    private Integer productCount;

    @Schema(description = "父分类ID", example = "0")
    private Long parentId;

    @Schema(description = "分类层级", accessMode = READ_ONLY)
    private Integer level;

    @Schema(description = "是否显示", example = "true")
    private Boolean visible = true;

    // 树形结构扩展
    @Schema(description = "子分类列表", accessMode = READ_ONLY)
    private List<CategoryDTO> children;

    /**
     * 快速构建方法
     */
    public static CategoryDTO of(Long id, String name) {
        CategoryDTO dto = new CategoryDTO();
        dto.setId(id);
        dto.setName(name);
        return dto;
    }
}