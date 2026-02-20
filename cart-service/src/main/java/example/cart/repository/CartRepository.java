package com.example.ecommerce.cart.repository;

import com.example.ecommerce.cart.model.Cart;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import javax.persistence.LockModeType;
import java.util.Optional;

public interface CartRepository extends JpaRepository<Cart, Long> {

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT c FROM Cart c WHERE c.userId = :userId")
    Optional<Cart> findByUserIdWithLock(@Param("userId") Long userId);

    Optional<Cart> findByUserId(Long userId);

    void deleteByUserId(Long userId);
}