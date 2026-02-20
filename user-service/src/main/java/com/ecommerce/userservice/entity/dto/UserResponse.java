
// UserResponse.java
public record UserResponse(
        String id,
        String username,
        String email,
        UserRole role,
        LocalDateTime createdAt
) {
    public static UserResponse fromEntity(User user) {
        return new UserResponse(
                user.getId(),
                user.getUsername(),
                user.getEmail(),
                user.getRole(),
                user.getCreatedAt()
        );
    }
}