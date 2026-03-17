package com.nexusos.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.nexusos.app.ui.chat.ChatScreen
import com.nexusos.app.ui.login.LoginScreen
import com.nexusos.app.ui.theme.NexusOSTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            NexusOSTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = Color.Black
                ) {
                    val service = com.nexusos.app.api.NexusService.shared
                    var isLoggedIn by remember { mutableStateOf(service.isLoggedIn) }
                    
                    if (isLoggedIn) {
                        MainScreen(onLogout = { isLoggedIn = false })
                    } else {
                        LoginScreen(onLoginSuccess = { isLoggedIn = true })
                    }
                }
            }
        }
    }
}
