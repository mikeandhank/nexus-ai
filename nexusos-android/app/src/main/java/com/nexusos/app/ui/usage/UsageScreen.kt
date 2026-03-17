package com.nexusos.app.ui.usage

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.nexusos.app.api.NexusService
import kotlinx.coroutines.launch

@Composable
fun UsageScreen(modifier: Modifier = Modifier) {
    var usage by remember { mutableStateOf<NexusService.UsageSummary?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    val scope = rememberCoroutineScope()
    
    LaunchedEffect(Unit) {
        NexusService.shared.getUsage().fold(
            onSuccess = { usage = it },
            onFailure = { }
        )
        isLoading = false
    }
    
    Column(
        modifier = modifier
            .fillMaxSize()
            .background(Color.Black)
            .padding(16.dp)
    ) {
        Text(
            text = "Usage",
            style = MaterialTheme.typography.headlineMedium,
            color = Color.White
        )
        
        Spacer(modifier = Modifier.height(24.dp))
        
        if (isLoading) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                CircularProgressIndicator(color = Color(0xFF4F46E5))
            }
        } else if (usage != null) {
            // Summary Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A1A)),
                shape = RoundedCornerShape(16.dp)
            ) {
                Column(
                    modifier = Modifier.padding(24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "This Month",
                        color = Color.Gray
                    )
                    
                    Spacer(modifier = Modifier.height(16.dp))
                    
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceEvenly
                    ) {
                        StatItem(value = "${usage!!.summary.totalRequests}", label = "Requests")
                        StatItem(value = "${usage!!.summary.totalTokens}", label = "Tokens")
                        StatItem(value = "$${String.format("%.4f", usage!!.summary.totalCostUsd)}", label = "Cost")
                    }
                }
            }
            
            Spacer(modifier = Modifier.height(24.dp))
            
            // By Model
            Text(
                text = "By Model",
                style = MaterialTheme.typography.titleMedium,
                color = Color.Gray
            )
            
            Spacer(modifier = Modifier.height(12.dp))
            
            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(usage!!.byModel) { model ->
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A1A)),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(16.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text(
                                    text = model.model,
                                    color = Color.White
                                )
                                Text(
                                    text = model.provider,
                                    color = Color.Gray,
                                    style = MaterialTheme.typography.bodySmall
                                )
                            }
                            Column(horizontalAlignment = Alignment.End) {
                                Text(
                                    text = "${model.requests} req",
                                    color = Color.Gray
                                )
                                Text(
                                    text = "$${String.format("%.4f", model.cost)}",
                                    color = Color(0xFF4F46E5)
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun StatItem(value: String, label: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            text = value,
            style = MaterialTheme.typography.headlineMedium,
            color = Color(0xFF4F46E5)
        )
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall,
            color = Color.Gray
        )
    }
}
