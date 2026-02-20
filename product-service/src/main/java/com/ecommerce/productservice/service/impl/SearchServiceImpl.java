package com.ecommerce.product.service.impl;

import com.ecommerce.product.model.Product;
import com.ecommerce.product.model.dto.ProductResponse;
import com.ecommerce.product.repository.es.ProductEsRepository;
import com.ecommerce.product.service.SearchService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class SearchServiceImpl implements SearchService {
    private final ProductEsRepository productEsRepository;

    @Override
    public Page<ProductResponse> searchProducts(
            String keyword,
            Pageable pageable) {
        return productEsRepository.findByNameOrDescriptionContaining(keyword, pageable)
                .map(this::convertToResponse);
    }

    @Override
    public Page<ProductResponse> searchByCategory(
            Long categoryId,
            Pageable pageable) {
        return productEsRepository.findByCategoryId(categoryId, pageable)
                .map(this::convertToResponse);
    }

    private ProductResponse convertToResponse(Product product) {
        return ProductResponse.builder()
                .id(product.getId())
                .name(product.getName())
                .description(product.getDescription())
                .price(product.getPrice())
                .stock(product.getStock())
                .categoryId(product.getCategory().getId())
                .categoryName(product.getCategory().getName())
                .createTime(product.getCreatedAt())
                .build();
    }
}