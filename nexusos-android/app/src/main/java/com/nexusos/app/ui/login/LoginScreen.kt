package com.nexusos.app.ui.login

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.nexusos.app.api.NexusService

@Composable
fun LoginScreen(onLoginSuccess: () -> Unit) {
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var name by remember { mutableStateOf("") }
    var isRegistering by remember { mutableStateOf(false) }
    var isLoading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        // Logo
        Text(
            text = "⬡",
            style = MaterialTheme.typography.displayLarge,
            color = Color(0xFF4F46E5)
        )
        
        Text(
            text = "NexusOS",
            style = MaterialTheme.typography.headlineLarge,
            color = Color.White
        )
        
        Text(
            text = "Your Personal AI Agent",
            style = MaterialTheme.typography.bodyMedium,
            color = Color.Gray
        )
        
        Spacer(modifier = Modifier.height(48.dp))
        
        // Form
        if (isRegistering) {
            OutlinedTextField(
                value = name,
                onValueChange = { name = it },
                label = { Text("Name") },
                modifier = Modifier.fillMaxWidth(),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = Color(0xFF4F46E5),
                    unfocusedBorderColor = Color.Gray
                )
            )
            Spacer(modifier = Modifier.height(16.dp))
        }
        
        OutlinedTextField(
            value = email,
            onValueChange = { email = it },
            label = { Text("Email") },
            modifier = Modifier.fillMaxWidth(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = Color(0xFF4F46E5),
                unfocusedBorderColor = Color.Gray
            )
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("Password") },
            modifier = Modifier.fillMaxWidth(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = Color(0xFF4F46E5),
                unfocusedBorderColor = Color.Gray
            )
        )
        
        if (errorMessage.isNotEmpty()) {
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = errorMessage,
                color = Color.Red,
                style = MaterialTheme.typography.bodySmall
            )
        }
        
        Spacer(modifier = Modifier.height(24.dp))
        
        Button(
            onClick = {
                isLoading = true
                errorMessage = ""
                
                kotlinx.coroutines.MainScope().launch {
                    val result = if (isRegistering) {
                        NexusService.shared.register(email, password, name)
                    } else {
                        NexusService.shared.login(email, password)
                    }
                    
                    result.fold(
                        onSuccess = { onLoginSuccess() },
                        onFailure = { errorMessage = "Login failed. Check credentials." }
                    )
                    isLoading = false
                }
            },
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(
                containerColor = Color(0xFF4F46E5)
            ),
            enabled = !isLoading
        ) {
            Text(if (isLoading) "Please wait..." else if (isRegistering) "Create Account" else "Sign In")
        }
        
        Spacer(modifier = Modifier.height(16.dp))
        
        TextButton(onClick = { isRegistering = !isRegistering }) {
            Text(
                text = if (isRegistering) "Already have an account? Sign In" else "Create Account",
                color = Color.Gray
            )
        }
    }
}

private fun kotlinx.coroutines.MainScope() = kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.Main)
