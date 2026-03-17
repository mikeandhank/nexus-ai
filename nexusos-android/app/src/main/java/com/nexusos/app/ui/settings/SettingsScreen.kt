package com.nexusos.app.ui.settings

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import com.nexusos.app.api.NexusService

@Composable
fun SettingsScreen(modifier: Modifier = Modifier, onLogout: () -> Unit) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .background(Color.Black)
            .padding(16.dp)
    ) {
        Text(
            text = "Settings",
            style = MaterialTheme.typography.headlineMedium,
            color = Color.White
        )
        
        Spacer(modifier = Modifier.height(24.dp))
        
        // Settings List
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A1A)),
            shape = RoundedCornerShape(16.dp)
        ) {
            Column {
                SettingsItem(icon = Icons.Default.Person, title = "Account", color = Color.Blue)
                SettingsItem(icon = Icons.Default.Notifications, title = "Notifications", color = Color(0xFFFF9800))
                SettingsItem(icon = Icons.Default.Security, title = "Security", color = Color(0xFF4CAF50))
                SettingsItem(icon = Icons.Default.Help, title = "Help", color = Color(0xFF9C27B0))
            }
        }
        
        Spacer(modifier = Modifier.weight(1f))
        
        // Logout Button
        Button(
            onClick = {
                NexusService.shared.logout()
                onLogout()
            },
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(
                containerColor = Color(0xFF1A1A1A)
            ),
            shape = RoundedCornerShape(12.dp)
        ) {
            Text(
                text = "Sign Out",
                color = Color.Red
            )
        }
    }
}

@Composable
fun SettingsItem(icon: ImageVector, title: String, color: Color) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            imageVector = icon,
            contentDescription = title,
            tint = color,
            modifier = Modifier.size(24.dp)
        )
        
        Spacer(modifier = Modifier.width(16.dp))
        
        Text(
            text = title,
            color = Color.White,
            modifier = Modifier.weight(1f)
        )
        
        Icon(
            imageVector = Icons.Default.ChevronRight,
            contentDescription = null,
            tint = Color.Gray
        )
    }
}
