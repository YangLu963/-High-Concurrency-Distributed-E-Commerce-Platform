// UserRequest.java
public record UserRequest(
        @NotBlank @Size(min=3, max=50) String username,
        @NotBlank @Email String email,
        @NotBlank @Size(min=8) String password
) {}


// AuthResponse.java
public record AuthResponse(String token, UserResponse user) {}