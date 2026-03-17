package com.nexusos.app.api

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException

class NexusService {
    companion object {
        val shared = NexusService()
        const val BASE_URL = "http://187.124.150.225:8080/api"
    }

    private val client = OkHttpClient()
    var accessToken: String = ""
        private set

    var isLoggedIn: Boolean = false
        private set

    data class LoginResponse(
        val accessToken: String,
        val refreshToken: String,
        val user: User
    )

    data class User(
        val userId: String,
        val name: String,
        val email: String
    )

    data class ChatResponse(
        val response: String,
        val conversationId: String,
        val tokens: Int,
        val cost: Double,
        val model: String
    )

    data class UsageSummary(
        val summary: UsageStats,
        val byModel: List<ModelUsage>
    )

    data class UsageStats(
        val totalRequests: Int,
        val totalTokens: Int,
        val totalCostUsd: Double
    )

    data class ModelUsage(
        val model: String,
        val provider: String,
        val requests: Int,
        val tokens: Int,
        val cost: Double
    )

    suspend fun login(email: String, password: String): Result<LoginResponse> = withContext(Dispatchers.IO) {
        try {
            val json = JSONObject().put("email", email).put("password", password)
            val request = Request.Builder()
                .url("$BASE_URL/auth/login")
                .post(json.toString().toRequestBody("application/json".toMediaType()))
                .build()

            val response = client.newCall(request).execute()
            if (response.code == 200) {
                val body = JSONObject(response.body?.string() ?: "")
                accessToken = body.getString("access_token")
                isLoggedIn = true
                
                val userObj = body.getJSONObject("user")
                val user = User(
                    userId = userObj.getString("user_id"),
                    name = userObj.getString("name"),
                    email = userObj.getString("email")
                )
                Result.success(LoginResponse(
                    accessToken = body.getString("access_token"),
                    refreshToken = body.getString("refresh_token"),
                    user = user
                ))
            } else {
                Result.failure(Exception("Login failed"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun register(email: String, password: String, name: String): Result<LoginResponse> = withContext(Dispatchers.IO) {
        try {
            val json = JSONObject()
                .put("email", email)
                .put("password", password)
                .put("name", name)
            
            val request = Request.Builder()
                .url("$BASE_URL/auth/register")
                .post(json.toString().toRequestBody("application/json".toMediaType()))
                .build()

            val response = client.newCall(request).execute()
            if (response.code == 201) {
                val body = JSONObject(response.body?.string() ?: "")
                accessToken = body.getString("access_token")
                isLoggedIn = true
                
                val userObj = body.getJSONObject("user")
                val user = User(
                    userId = userObj.getString("user_id"),
                    name = userObj.getString("name"),
                    email = userObj.getString("email")
                )
                Result.success(LoginResponse(
                    accessToken = body.getString("access_token"),
                    refreshToken = body.getString("refresh_token"),
                    user = user
                ))
            } else {
                Result.failure(Exception("Registration failed"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun chat(message: String): Result<ChatResponse> = withContext(Dispatchers.IO) {
        try {
            val json = JSONObject().put("message", message)
            val request = Request.Builder()
                .url("$BASE_URL/chat")
                .addHeader("Authorization", "Bearer $accessToken")
                .post(json.toString().toRequestBody("application/json".toMediaType()))
                .build()

            val response = client.newCall(request).execute()
            if (response.code == 200) {
                val body = JSONObject(response.body?.string() ?: "")
                Result.success(ChatResponse(
                    response = body.getString("response"),
                    conversationId = body.getString("conversation_id"),
                    tokens = body.getInt("tokens"),
                    cost = body.getDouble("cost"),
                    model = body.getString("model")
                ))
            } else {
                Result.failure(Exception("Chat failed"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getUsage(): Result<UsageSummary> = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("$BASE_URL/usage")
                .addHeader("Authorization", "Bearer $accessToken")
                .get()
                .build()

            val response = client.newCall(request).execute()
            if (response.code == 200) {
                val body = JSONObject(response.body?.string() ?: "")
                val summaryObj = body.getJSONObject("summary")
                val summary = UsageStats(
                    totalRequests = summaryObj.getInt("total_requests"),
                    totalTokens = summaryObj.getInt("total_tokens"),
                    totalCostUsd = summaryObj.getDouble("total_cost_usd")
                )
                
                val byModelArray = body.getJSONArray("by_model")
                val byModel = mutableListOf<ModelUsage>()
                for (i in 0 until byModelArray.length()) {
                    val m = byModelArray.getJSONObject(i)
                    byModel.add(ModelUsage(
                        model = m.getString("model"),
                        provider = m.getString("provider"),
                        requests = m.getInt("requests"),
                        tokens = m.getInt("tokens"),
                        cost = m.getDouble("cost")
                    ))
                }
                
                Result.success(UsageSummary(summary, byModel))
            } else {
                Result.failure(Exception("Usage fetch failed"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    fun logout() {
        accessToken = ""
        isLoggedIn = false
    }
}
