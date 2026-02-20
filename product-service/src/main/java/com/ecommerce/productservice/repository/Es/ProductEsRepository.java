package com.ecommerce.product.repository.es;

import com.ecommerce.product.model.elasticsearch.ProductDocument;
import org.springframework.data.elasticsearch.annotations.Query;
import org.springframework.data.elasticsearch.repository.ElasticsearchRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import java.util.List;

public interface ProductEsRepository extends ElasticsearchRepository<ProductDocument, Long> {

    // 基本搜索
    Page<ProductDocument> findByNameOrDescription(String name, String description, Pageable pageable);

    // 分类搜索
    Page<ProductDocument> findByCategoryId(Long categoryId, Pageable pageable);

    // 带高亮的复杂搜索
    @Query("{\"bool\": {\"must\": [{\"multi_match\": {\"query\": \"?0\", \"fields\": [\"name^3\", \"description\", \"specs.*\"]}}]}}")
    Page<ProductDocument> fullTextSearch(String query, Pageable pageable);

    // 聚合查询示例
    @Query("{\"bool\": {\"filter\": [{\"term\": {\"categoryId\": \"?0\"}}], \"must\": [{\"range\": {\"price\": {\"gte\": \"?1\", \"lte\": \"?2\"}}]}}")
    List<ProductDocument> findByCategoryAndPriceRange(Long categoryId, Double minPrice, Double maxPrice);

    // 手动刷新索引
    @Query(value = "{\"index\": {\"_refresh\": true}}")
    void refreshIndex();
}