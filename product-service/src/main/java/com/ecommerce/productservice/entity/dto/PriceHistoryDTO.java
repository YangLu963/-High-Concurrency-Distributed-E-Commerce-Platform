package com.ecommerce.product.model.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 商品价格变更记录
 */
@Data
@Schema(description = "商品价格历史记录")
public class PriceHistoryDTO {
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    @Schema(description = "变更时间", example = "2023-08-20 14:30:00")
    private LocalDateTime changeTime;

    @Schema(description = "原价格", example = "100.00")
    private BigDecimal oldPrice;

    @Schema(description = "新价格", example = "120.00")
    private BigDecimal newPrice;

    @Schema(description = "操作人", example = "admin")
    private String changedBy;

    @Schema(description = "变更原因", example = "促销调价")
    private String changeReason;

    // 自动计算字段
    @Schema(description = "变动金额", accessMode = READ_ONLY)
    public BigDecimal getChangeAmount() {
        return newPrice.subtract(oldPrice);
    }

    @Schema(description = "变动百分比", accessMode = READ_ONLY)
    public String getChangePercentage() {
        if (oldPrice.compareTo(BigDecimal.ZERO) == 0) {
            return "N/A";
        }
        BigDecimal percent = getChangeAmount()
                .divide(oldPrice, 4, BigDecimal.ROUND_HALF_UP)
                .multiply(BigDecimal.valueOf(100));
        return percent.stripTrailingZeros().toPlainString() + "%";
    }
}