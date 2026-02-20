package com.ecommerce.userservice.service;

import com.ecommerce.user.dto.UserDTO;

public interface UserService {
    UserDTO register(UserDTO userDTO);
    UserDTO getUserById(Long id);
}