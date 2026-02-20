package com.ecommerce.userservice.controller;

import com.ecommerce.user.dto.UserDTO;
import com.ecommerce.user.service.UserService;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/users")
public class UserController {
    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    @PostMapping("/register")
    public UserDTO register(@RequestBody UserDTO userDTO) {
        return userService.register(userDTO);
    }
}