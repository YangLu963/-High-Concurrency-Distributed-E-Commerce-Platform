package com.ecommerce.product.repository;

import com.ecommerce.product.model.entity.Category;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import java.util.List;
import java.util.Optional;

public interface CategoryRepository extends JpaRepository<Category, Long> {
    Optional<Category> findByNameAndParentId(String name, Long parentId);

    List<Category> findByParentId(Long parentId);

    List<Category> findByLevel(Integer level);

    @Query("SELECT c FROM Category c WHERE c.parentId IS NULL")
    List<Category> findRootCategories();

    @Query("SELECT COUNT(p) FROM Product p WHERE p.category.id = :categoryId")
    Long countProductsInCategory(Long categoryId);

    boolean existsByNameAndParentIdAndIdNot(String name, Long parentId, Long excludedId);
}