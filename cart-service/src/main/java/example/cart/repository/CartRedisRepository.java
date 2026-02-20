package com.example.ecommerce.cart.repository;

import com.example.ecommerce.cart.model.dto.CartDTO;
import org.springframework.data.redis.core.HashOperations;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Repository;

import javax.annotation.PostConstruct;
import java.util.Optional;

@Repository
public class RedisCartRepository {
    private static final String KEY = "Cart";
    private final RedisTemplate<String, Object> redisTemplate;
    private HashOperations<String, Long, CartDTO> hashOperations;

    public RedisCartRepository(RedisTemplate<String, Object> redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    @PostConstruct
    private void init() {
        hashOperations = redisTemplate.opsForHash();
    }

    public void save(CartDTO cartDTO) {
        hashOperations.put(KEY, cartDTO.getUserId(), cartDTO);
    }

    public Optional<CartDTO> findByUserId(Long userId) {
        return Optional.ofNullable(hashOperations.get(KEY, userId));
    }

    public void deleteByUserId(Long userId) {
        hashOperations.delete(KEY, userId);
    }
}