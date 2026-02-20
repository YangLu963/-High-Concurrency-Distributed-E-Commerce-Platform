@Configuration
@EnableCaching
public class CacheConfig {
    @Bean
    public RedisCacheManager cacheManager(RedisConnectionFactory factory) {
        RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig()
                .serializeValuesWith(SerializationPair.fromSerializer(new Jackson2JsonRedisSerializer<>(ProductResponse.class)))
                .entryTtl(Duration.ofMinutes(30));

        return RedisCacheManager.builder(factory)
                .cacheDefaults(config)
                .build();
    }
}