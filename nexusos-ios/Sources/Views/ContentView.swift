import SwiftUI

// MARK: - Models

struct User: Codable {
    let user_id: String
    let name: String
    let email: String
}

struct LoginResponse: Codable {
    let access_token: String
    let refresh_token: String
    let user: User
}

struct ChatMessage: Identifiable, Codable {
    let id: String
    let role: String
    let content: String
    let timestamp: Date
    
    init(id: String = UUID().uuidString, role: String, content: String, timestamp: Date = Date()) {
        self.id = id
        self.role = role
        self.content = content
        self.timestamp = timestamp
    }
}

struct ChatResponse: Codable {
    let response: String
    let conversation_id: String
    let tokens: Int
    let cost: Double
    let model: String
}

struct UsageSummary: Codable {
    let summary: UsageStats
    let by_model: [ModelUsage]
}

struct UsageStats: Codable {
    let total_requests: Int
    let total_tokens: Int
    let total_cost_usd: Double
}

struct ModelUsage: Codable {
    let model: String
    let provider: String
    let requests: Int
    let tokens: Int
    let cost: Double
}

// MARK: - API Service

class NexusService: ObservableObject {
    static let shared = NexusService()
    
    let baseURL = "http://187.124.150.225:8080/api"
    
    @Published var isLoggedIn = false
    @Published var accessToken: String = ""
    @Published var user: User?
    @Published var errorMessage: String?
    
    private init() {
        // Check for stored token
        if let token = UserDefaults.standard.string(forKey: "accessToken") {
            self.accessToken = token
            self.isLoggedIn = true
        }
    }
    
    func login(email: String, password: String) async throws {
        let url = URL(string: "\(baseURL)/auth/login")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(["email": email, "password": password])
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw NSError(domain: "Login failed", code: 401)
        }
        
        let loginResponse = try JSONDecoder().decode(LoginResponse.self, from: data)
        
        await MainActor.run {
            self.accessToken = loginResponse.access_token
            self.user = loginResponse.user
            self.isLoggedIn = true
            UserDefaults.standard.set(loginResponse.access_token, forKey: "accessToken")
        }
    }
    
    func register(email: String, password: String, name: String) async throws {
        let url = URL(string: "\(baseURL)/auth/register")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(["email": email, "password": password, "name": name])
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 201 else {
            throw NSError(domain: "Registration failed", code: 400)
        }
        
        let loginResponse = try JSONDecoder().decode(LoginResponse.self, from: data)
        
        await MainActor.run {
            self.accessToken = loginResponse.access_token
            self.user = loginResponse.user
            self.isLoggedIn = true
            UserDefaults.standard.set(loginResponse.access_token, forKey: "accessToken")
        }
    }
    
    func chat(message: String) async throws -> ChatResponse {
        guard !accessToken.isEmpty else { throw NSError(domain: "Not logged in", code: 401) }
        
        let url = URL(string: "\(baseURL)/chat")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        request.httpBody = try JSONEncoder().encode(["message": message])
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw NSError(domain: "Chat failed", code: 500)
        }
        
        return try JSONDecoder().decode(ChatResponse.self, from: data)
    }
    
    func getUsage() async throws -> UsageSummary {
        guard !accessToken.isEmpty else { throw NSError(domain: "Not logged in", code: 401) }
        
        let url = URL(string: "\(baseURL)/usage")!
        var request = URLRequest(url: url)
        request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw NSError(domain: "Usage fetch failed", code: 500)
        }
        
        return try JSONDecoder().decode(UsageSummary.self, from: data)
    }
    
    func logout() {
        accessToken = ""
        user = nil
        isLoggedIn = false
        UserDefaults.standard.removeObject(forKey: "accessToken")
    }
}

// MARK: - Views

struct ContentView: View {
    @StateObject private var service = NexusService.shared
    @State private var selectedTab = 0
    
    var body: some View {
        Group {
            if service.isLoggedIn {
                MainTabView()
            } else {
                LoginView()
            }
        }
        .environmentObject(service)
    }
}

struct LoginView: View {
    @EnvironmentObject var service: NexusService
    @State private var email = ""
    @State private var password = ""
    @State private var isRegistering = false
    @State private var name = ""
    @State private var isLoading = false
    @State private var errorMessage = ""
    
    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()
            
            VStack(spacing: 24) {
                // Logo
                VStack(spacing: 8) {
                    Text("⬡")
                        .font(.system(size: 60))
                        .foregroundColor(Color(hex: "4f46e5"))
                    Text("NexusOS")
                        .font(.system(size: 32, weight: .bold))
                        .foregroundColor(.white)
                    Text("Your Personal AI Agent")
                        .foregroundColor(.gray)
                }
                .padding(.bottom, 40)
                
                // Form
                VStack(spacing: 16) {
                    if isRegistering {
                        TextField("Name", text: $name)
                            .textFieldStyle(AppTextFieldStyle())
                    }
                    
                    TextField("Email", text: $email)
                        .textFieldStyle(AppTextFieldStyle())
                        .textContentType(.emailAddress)
                        .autocapitalization(.none)
                    
                    SecureField("Password", text: $password)
                        .textFieldStyle(AppTextFieldStyle())
                        .textContentType(.password)
                }
                .padding(.horizontal, 40)
                
                // Error
                if !errorMessage.isEmpty {
                    Text(errorMessage)
                        .foregroundColor(.red)
                        .font(.caption)
                }
                
                // Buttons
                VStack(spacing: 12) {
                    Button(action: performLogin) {
                        Text(isLoading ? "Please wait..." : (isRegistering ? "Create Account" : "Sign In"))
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color(hex: "4f46e5"))
                            .foregroundColor(.white)
                            .cornerRadius(12)
                    }
                    .disabled(isLoading)
                    
                    Button(action: { isRegistering.toggle() }) {
                        Text(isRegistering ? "Already have an account? Sign In" : "Create Account")
                            .foregroundColor(.gray)
                    }
                }
                .padding(.horizontal, 40)
                
                Spacer()
            }
            .padding(.top, 60)
        }
    }
    
    func performLogin() {
        isLoading = true
        errorMessage = ""
        
        Task {
            do {
                if isRegistering {
                    try await service.register(email: email, password: password, name: name)
                } else {
                    try await service.login(email: email, password: password)
                }
            } catch {
                await MainActor.run {
                    errorMessage = "Login failed. Please check your credentials."
                }
            }
            await MainActor.run {
                isLoading = false
            }
        }
    }
}

struct MainTabView: View {
    @EnvironmentObject var service: NexusService
    @State private var selectedTab = 0
    
    var body: some View {
        TabView(selection: $selectedTab) {
            ChatView()
                .tabItem {
                    Label("Chat", systemImage: "bubble.left.and.bubble.right")
                }
                .tag(0)
            
            UsageView()
                .tabItem {
                    Label("Usage", systemImage: "chart.bar")
                }
                .tag(1)
            
            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gear")
                }
                .tag(2)
        }
        .accentColor(Color(hex: "4f46e5"))
    }
}

struct ChatView: View {
    @EnvironmentObject var service: NexusService
    @State private var message = ""
    @State private var messages: [ChatMessage] = []
    @State private var isLoading = false
    
    var body: some View {
        NavigationView {
            ZStack {
                Color.black.ignoresSafeArea()
                
                VStack(spacing: 0) {
                    // Messages
                    ScrollViewReader { proxy in
                        ScrollView {
                            LazyVStack(spacing: 12) {
                                ForEach(messages) { msg in
                                    MessageBubble(message: msg)
                                        .id(msg.id)
                                }
                            }
                            .padding()
                        }
                        .onChange(of: messages.count) { _ in
                            if let last = messages.last {
                                withAnimation {
                                    proxy.scrollTo(last.id, anchor: .bottom)
                                }
                            }
                        }
                    }
                    
                    // Input
                    HStack(spacing: 12) {
                        TextField("Type message...", text: $message)
                            .padding()
                            .background(Color(hex: "1a1a1a"))
                            .cornerRadius(12)
                            .foregroundColor(.white)
                        
                        Button(action: sendMessage) {
                            Image(systemName: "arrow.up.circle.fill")
                                .font(.system(size: 32))
                                .foregroundColor(Color(hex: "4f46e5"))
                        }
                        .disabled(message.isEmpty || isLoading)
                    }
                    .padding()
                    .background(Color(hex: "111111"))
                }
            }
            .navigationTitle("Chat")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: { messages = [] }) {
                        Image(systemName: "trash")
                            .foregroundColor(.gray)
                    }
                }
            }
        }
    }
    
    func sendMessage() {
        guard !message.isEmpty else { return }
        
        let userMsg = ChatMessage(role: "user", content: message)
        messages.append(userMsg)
        
        let msgCopy = message
        message = ""
        isLoading = true
        
        Task {
            do {
                let response = try await service.chat(message: msgCopy)
                await MainActor.run {
                    let assistantMsg = ChatMessage(role: "assistant", content: response.response)
                    messages.append(assistantMsg)
                    isLoading = false
                }
            } catch {
                await MainActor.run {
                    let errorMsg = ChatMessage(role: "assistant", content: "Error: \(error.localizedDescription)")
                    messages.append(errorMsg)
                    isLoading = false
                }
            }
        }
    }
}

struct MessageBubble: View {
    let message: ChatMessage
    
    var body: some View {
        HStack {
            if message.role == "user" { Spacer() }
            
            VStack(alignment: message.role == "user" ? .trailing : .leading, spacing: 4) {
                Text(message.content)
                    .padding(12)
                    .background(message.role == "user" ? Color(hex: "4f46e5") : Color(hex: "1a1a1a"))
                    .foregroundColor(.white)
                    .cornerRadius(16)
            }
            
            if message.role != "user" { Spacer() }
        }
    }
}

struct UsageView: View {
    @EnvironmentObject var service: NexusService
    @State private var usage: UsageSummary?
    
    var body: some View {
        NavigationView {
            ZStack {
                Color.black.ignoresSafeArea()
                
                ScrollView {
                    VStack(spacing: 20) {
                        if let usage = usage {
                            // Summary Card
                            VStack(spacing: 16) {
                                Text("This Month")
                                    .foregroundColor(.gray)
                                
                                HStack(spacing: 40) {
                                    VStack {
                                        Text("\(usage.summary.total_requests)")
                                            .font(.system(size: 32, weight: .bold))
                                            .foregroundColor(Color(hex: "4f46e5"))
                                        Text("Requests")
                                            .foregroundColor(.gray)
                                            .font(.caption)
                                    }
                                    
                                    VStack {
                                        Text("\(usage.summary.total_tokens)")
                                            .font(.system(size: 32, weight: .bold))
                                            .foregroundColor(Color(hex: "4f46e5"))
                                        Text("Tokens")
                                            .foregroundColor(.gray)
                                            .font(.caption)
                                    }
                                    
                                    VStack {
                                        Text(String(format: "$%.4f", usage.summary.total_cost_usd))
                                            .font(.system(size: 32, weight: .bold))
                                            .foregroundColor(Color(hex: "4f46e5"))
                                        Text("Cost")
                                            .foregroundColor(.gray)
                                            .font(.caption)
                                    }
                                }
                            }
                            .padding(24)
                            .background(Color(hex: "1a1a1a"))
                            .cornerRadius(16)
                            
                            // By Model
                            VStack(alignment: .leading, spacing: 12) {
                                Text("By Model")
                                    .foregroundColor(.gray)
                                    .padding(.horizontal)
                                
                                ForEach(usage.by_model, id: \.model) { model in
                                    HStack {
                                        VStack(alignment: .leading) {
                                            Text(model.model)
                                                .foregroundColor(.white)
                                            Text(model.provider)
                                                .foregroundColor(.gray)
                                                .font(.caption)
                                        }
                                        Spacer()
                                        Text("\(model.requests) req")
                                            .foregroundColor(.gray)
                                        Text(String(format: "$%.4f", model.cost))
                                            .foregroundColor(Color(hex: "4f46e5"))
                                    }
                                    .padding()
                                    .background(Color(hex: "1a1a1a"))
                                    .cornerRadius(12)
                                }
                            }
                        } else {
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: Color(hex: "4f46e5")))
                        }
                    }
                    .padding()
                }
            }
            .navigationTitle("Usage")
            .onAppear(perform: loadUsage)
        }
    }
    
    func loadUsage() {
        Task {
            do {
                let data = try await service.getUsage()
                await MainActor.run {
                    usage = data
                }
            } catch {
                print("Error loading usage: \(error)")
            }
        }
    }
}

struct SettingsView: View {
    @EnvironmentObject var service: NexusService
    
    var body: some View {
        NavigationView {
            ZStack {
                Color.black.ignoresSafeArea()
                
                VStack(spacing: 20) {
                    // User Info
                    if let user = service.user {
                        VStack(spacing: 8) {
                            Image(systemName: "person.circle.fill")
                                .font(.system(size: 60))
                                .foregroundColor(Color(hex: "4f46e5"))
                            Text(user.name)
                                .font(.title2)
                                .foregroundColor(.white)
                            Text(user.email)
                                .foregroundColor(.gray)
                        }
                        .padding()
                    }
                    
                    // Settings List
                    VStack(spacing: 0) {
                        SettingsRow(icon: "person", title: "Account", color: .blue)
                        SettingsRow(icon: "bell", title: "Notifications", color: .orange)
                        SettingsRow(icon: "lock", title: "Security", color: .green)
                        SettingsRow(icon: "questionmark.circle", title: "Help", color: .purple)
                    }
                    .background(Color(hex: "1a1a1a"))
                    .cornerRadius(16)
                    
                    Spacer()
                    
                    // Logout
                    Button(action: { service.logout() }) {
                        Text("Sign Out")
                            .foregroundColor(.red)
                            .padding()
                            .frame(maxWidth: .infinity)
                            .background(Color(hex: "1a1a1a"))
                            .cornerRadius(12)
                    }
                }
                .padding()
            }
            .navigationTitle("Settings")
        }
    }
}

struct SettingsRow: View {
    let icon: String
    let title: String
    let color: Color
    
    var body: some View {
        HStack(spacing: 16) {
            Image(systemName: icon)
                .foregroundColor(color)
                .frame(width: 24)
            Text(title)
                .foregroundColor(.white)
            Spacer()
            Image(systemName: "chevron.right")
                .foregroundColor(.gray)
        }
        .padding()
    }
}

struct AppTextFieldStyle: TextFieldStyle {
    func _body(configuration: TextField<Self._Label>) -> some View {
        configuration
            .padding()
            .background(Color(hex: "1a1a1a"))
            .cornerRadius(12)
            .foregroundColor(.white)
    }
}

// MARK: - Color Extension

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (1, 1, 1, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

#Preview {
    ContentView()
}
