package com.nexusos.app

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.nexusos.app.api.NexusService
import com.nexusos.app.ui.chat.ChatScreen
import com.nexusos.app.ui.settings.SettingsScreen
import com.nexusos.app.ui.usage.UsageScreen

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(onLogout: () -> Unit) {
    var selectedTab by remember { mutableStateOf(0) }
    
    Scaffold(
        bottomBar = {
            NavigationBar(
                containerColor = Color(0xFF1A1A1A)
            ) {
                NavigationBarItem(
                    icon = { Icon(Icons.Default.Chat, contentDescription = "Chat") },
                    label = { Text("Chat") },
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = Color(0xFF4F46E5),
                        selectedTextColor = Color(0xFF4F46E5),
                        indicatorColor = Color(0xFF4F46E5).copy(alpha = 0.2f)
                    )
                )
                NavigationBarItem(
                    icon = { Icon(Icons.Default.BarChart, contentDescription = "Usage") },
                    label = { Text("Usage") },
                    selected = selectedTab == 1,
                    onClick = { selectedTab = 1 },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = Color(0xFF4F46E5),
                        selectedTextColor = Color(0xFF4F46E5),
                        indicatorColor = Color(0xFF4F46E5).copy(alpha = 0.2f)
                    )
                )
                NavigationBarItem(
                    icon = { Icon(Icons.Default.Settings, contentDescription = "Settings") },
                    label = { Text("Settings") },
                    selected = selectedTab == 2,
                    onClick = { selectedTab = 2 },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = Color(0xFF4F46E5),
                        selectedTextColor = Color(0xFF4F46E5),
                        indicatorColor = Color(0xFF4F46E5).copy(alpha = 0.2f)
                    )
                )
            }
        }
    ) { paddingValues ->
        when (selectedTab) {
            0 -> ChatScreen(modifier = Modifier.padding(paddingValues))
            1 -> UsageScreen(modifier = Modifier.padding(paddingValues))
            2 -> SettingsScreen(modifier = Modifier.padding(paddingValues), onLogout = onLogout)
        }
    }
}
