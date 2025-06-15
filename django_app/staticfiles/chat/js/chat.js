// T3 Chat Clone - Frontend JavaScript
class ChatApp {
    constructor() {
        this.socket = null;
        this.currentConversationId = null;
        this.isConnected = false;
        this.messageHistory = [];
        this.currentModel = 'openai/gpt-4o-mini';
        this.apiKeys = {};
        
        this.initializeElements();
        this.bindEvents();
        this.loadConversations();
        this.checkApiKeys();
    }

    initializeElements() {
        // Main elements
        this.messagesContainer = document.getElementById('messages-container');
        this.messageInput = document.getElementById('message-input');
        this.sendButton = document.getElementById('send-button');
        this.fileInput = document.getElementById('file-input');
        this.fileButton = document.getElementById('file-button');
        this.modelSelect = document.getElementById('model-select');
        this.settingsButton = document.getElementById('settings-button');
        this.newChatButton = document.getElementById('new-chat-button');
        this.conversationsList = document.getElementById('conversations-list');
        
        // Modal elements
        this.settingsModal = document.getElementById('settings-modal');
        this.modalOverlay = document.getElementById('modal-overlay');
        this.modalClose = document.getElementById('modal-close');
        this.settingsForm = document.getElementById('settings-form');
        
        // Sidebar toggle for mobile
        this.sidebarToggle = document.getElementById('sidebar-toggle');
        this.sidebar = document.getElementById('sidebar');
    }

    bindEvents() {
        // Message sending
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // File upload
        this.fileButton.addEventListener('click', () => this.fileInput.click());
        this.fileInput.addEventListener('change', (e) => this.handleFileUpload(e));

        // Model selection
        this.modelSelect.addEventListener('change', (e) => {
            this.currentModel = e.target.value;
            this.showStatusMessage(`Model changed to ${e.target.value}`, 'info');
        });

        // Settings modal
        this.settingsButton.addEventListener('click', () => this.openSettingsModal());
        this.modalClose.addEventListener('click', () => this.closeSettingsModal());
        this.modalOverlay.addEventListener('click', (e) => {
            if (e.target === this.modalOverlay) {
                this.closeSettingsModal();
            }
        });
        this.settingsForm.addEventListener('submit', (e) => this.saveSettings(e));

        // New chat
        this.newChatButton.addEventListener('click', () => this.startNewChat());

        // Sidebar toggle for mobile
        if (this.sidebarToggle) {
            this.sidebarToggle.addEventListener('click', () => this.toggleSidebar());
        }

        // Auto-resize textarea
        this.messageInput.addEventListener('input', () => this.autoResizeTextarea());
    }

    autoResizeTextarea() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
    }

    toggleSidebar() {
        this.sidebar.classList.toggle('open');
    }

    checkApiKeys() {
        const openrouterKey = localStorage.getItem('openrouter_api_key');
        const tavilyKey = localStorage.getItem('tavily_api_key');
        
        if (!openrouterKey) {
            this.showStatusMessage('Please configure your API keys in settings to start chatting.', 'warning');
            this.openSettingsModal();
        } else {
            this.apiKeys.openrouter = openrouterKey;
            this.apiKeys.tavily = tavilyKey;
            this.connectWebSocket();
        }
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat/`;
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
            console.log('WebSocket connected');
            this.isConnected = true;
            this.showStatusMessage('Connected to chat server', 'success');
            
            // Send authentication
            this.socket.send(JSON.stringify({
                type: 'authenticate',
                api_keys: this.apiKeys
            }));
        };
        
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };
        
        this.socket.onclose = () => {
            console.log('WebSocket disconnected');
            this.isConnected = false;
            this.showStatusMessage('Disconnected from server. Attempting to reconnect...', 'error');
            
            // Attempt to reconnect after 3 seconds
            setTimeout(() => {
                if (!this.isConnected) {
                    this.connectWebSocket();
                }
            }, 3000);
        };
        
        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.showStatusMessage('Connection error occurred', 'error');
        };
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'message_start':
                this.handleMessageStart(data);
                break;
            case 'message_chunk':
                this.handleMessageChunk(data);
                break;
            case 'message_complete':
                this.handleMessageComplete(data);
                break;
            case 'error':
                this.handleError(data);
                break;
            case 'conversation_created':
                this.handleConversationCreated(data);
                break;
            case 'conversations_list':
                this.handleConversationsList(data);
                break;
            case 'conversation_history':
                this.handleConversationHistory(data);
                break;
            case 'status':
                this.showStatusMessage(data.message, data.level || 'info');
                break;
        }
    }

    sendMessage() {
        const content = this.messageInput.value.trim();
        if (!content || !this.isConnected) return;

        // Add user message to UI immediately
        this.addMessage({
            role: 'user',
            content: content,
            timestamp: new Date().toISOString()
        });

        // Send to server
        this.socket.send(JSON.stringify({
            type: 'send_message',
            content: content,
            model: this.currentModel,
            conversation_id: this.currentConversationId
        }));

        // Clear input
        this.messageInput.value = '';
        this.autoResizeTextarea();
        this.sendButton.disabled = true;
    }

    handleMessageStart(data) {
        // Create assistant message placeholder
        this.currentAssistantMessage = this.addMessage({
            role: 'assistant',
            content: '',
            timestamp: new Date().toISOString(),
            model: data.model,
            streaming: true
        });
        
        this.showTypingIndicator();
    }

    handleMessageChunk(data) {
        if (this.currentAssistantMessage) {
            const contentElement = this.currentAssistantMessage.querySelector('.message-text');
            contentElement.textContent += data.content;
            this.scrollToBottom();
        }
    }

    handleMessageComplete(data) {
        this.hideTypingIndicator();
        
        if (this.currentAssistantMessage) {
            const contentElement = this.currentAssistantMessage.querySelector('.message-text');
            contentElement.innerHTML = this.formatMessage(data.content);
            this.currentAssistantMessage.classList.remove('streaming');
        }
        
        this.sendButton.disabled = false;
        this.currentAssistantMessage = null;
        this.scrollToBottom();
    }

    handleError(data) {
        this.hideTypingIndicator();
        this.showStatusMessage(data.message, 'error');
        this.sendButton.disabled = false;
        
        if (this.currentAssistantMessage) {
            this.currentAssistantMessage.remove();
            this.currentAssistantMessage = null;
        }
    }

    handleConversationCreated(data) {
        this.currentConversationId = data.conversation_id;
        this.loadConversations();
    }

    handleConversationsList(data) {
        this.renderConversations(data.conversations);
    }

    handleConversationHistory(data) {
        this.currentConversationId = data.conversation_id;
        this.messagesContainer.innerHTML = '';
        
        data.messages.forEach(message => {
            this.addMessage(message, false);
        });
        
        this.scrollToBottom();
        this.updateActiveConversation();
    }

    addMessage(message, scroll = true) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${message.role}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = message.role === 'user' ? 'U' : 'AI';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        const text = document.createElement('div');
        text.className = 'message-text';
        text.innerHTML = this.formatMessage(message.content);
        
        const time = document.createElement('div');
        time.className = 'message-time';
        time.textContent = this.formatTime(message.timestamp);
        
        content.appendChild(text);
        content.appendChild(time);
        
        if (message.model) {
            const model = document.createElement('div');
            model.className = 'message-model';
            model.textContent = message.model;
            content.appendChild(model);
        }
        
        messageElement.appendChild(avatar);
        messageElement.appendChild(content);
        
        if (message.streaming) {
            messageElement.classList.add('streaming');
        }
        
        this.messagesContainer.appendChild(messageElement);
        
        if (scroll) {
            this.scrollToBottom();
        }
        
        return messageElement;
    }

    formatMessage(content) {
        // Basic markdown-like formatting
        let formatted = content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
        
        // Handle code blocks
        formatted = formatted.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
            return `<pre><code class="language-${lang || 'text'}">${code.trim()}</code></pre>`;
        });
        
        return formatted;
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'typing-indicator';
        indicator.id = 'typing-indicator';
        
        indicator.innerHTML = `
            <div class="message-avatar">AI</div>
            <div class="typing-content">
                <span>AI is typing</span>
                <div class="typing-dots">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        
        this.messagesContainer.appendChild(indicator);
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    showStatusMessage(message, type = 'info') {
        const statusElement = document.createElement('div');
        statusElement.className = `status-message ${type}`;
        statusElement.textContent = message;
        
        this.messagesContainer.appendChild(statusElement);
        this.scrollToBottom();
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (statusElement.parentNode) {
                statusElement.remove();
            }
        }, 5000);
    }

    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    handleFileUpload(event) {
        const files = Array.from(event.target.files);
        if (files.length === 0) return;
        
        files.forEach(file => {
            if (file.size > 10 * 1024 * 1024) { // 10MB limit
                this.showStatusMessage(`File ${file.name} is too large (max 10MB)`, 'error');
                return;
            }
            
            const reader = new FileReader();
            reader.onload = (e) => {
                this.socket.send(JSON.stringify({
                    type: 'file_upload',
                    filename: file.name,
                    content: e.target.result.split(',')[1], // Remove data URL prefix
                    mime_type: file.type,
                    conversation_id: this.currentConversationId
                }));
            };
            reader.readAsDataURL(file);
        });
        
        // Clear file input
        event.target.value = '';
    }

    startNewChat() {
        this.socket.send(JSON.stringify({
            type: 'new_conversation'
        }));
        
        this.messagesContainer.innerHTML = '';
        this.currentConversationId = null;
    }

    loadConversations() {
        if (this.isConnected) {
            this.socket.send(JSON.stringify({
                type: 'get_conversations'
            }));
        }
    }

    renderConversations(conversations) {
        this.conversationsList.innerHTML = '';
        
        conversations.forEach(conv => {
            const item = document.createElement('div');
            item.className = 'conversation-item';
            item.dataset.conversationId = conv.id;
            
            if (conv.id === this.currentConversationId) {
                item.classList.add('active');
            }
            
            item.innerHTML = `
                <div class="conversation-title">${conv.title}</div>
                <div class="conversation-preview">${conv.preview || 'No messages yet'}</div>
            `;
            
            item.addEventListener('click', () => this.loadConversation(conv.id));
            this.conversationsList.appendChild(item);
        });
    }

    loadConversation(conversationId) {
        this.socket.send(JSON.stringify({
            type: 'get_conversation_history',
            conversation_id: conversationId
        }));
    }

    updateActiveConversation() {
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.conversationId === this.currentConversationId) {
                item.classList.add('active');
            }
        });
    }

    openSettingsModal() {
        // Pre-fill current values
        document.getElementById('openrouter-key').value = localStorage.getItem('openrouter_api_key') || '';
        document.getElementById('tavily-key').value = localStorage.getItem('tavily_api_key') || '';
        document.getElementById('custom-model').value = localStorage.getItem('custom_model') || '';
        
        this.settingsModal.style.display = 'flex';
    }

    closeSettingsModal() {
        this.settingsModal.style.display = 'none';
    }

    saveSettings(event) {
        event.preventDefault();
        
        const openrouterKey = document.getElementById('openrouter-key').value.trim();
        const tavilyKey = document.getElementById('tavily-key').value.trim();
        const customModel = document.getElementById('custom-model').value.trim();
        
        // Save to localStorage
        if (openrouterKey) {
            localStorage.setItem('openrouter_api_key', openrouterKey);
            this.apiKeys.openrouter = openrouterKey;
        }
        
        if (tavilyKey) {
            localStorage.setItem('tavily_api_key', tavilyKey);
            this.apiKeys.tavily = tavilyKey;
        }
        
        if (customModel) {
            localStorage.setItem('custom_model', customModel);
            // Add to model select if not already there
            const option = document.createElement('option');
            option.value = customModel;
            option.textContent = customModel;
            this.modelSelect.appendChild(option);
            this.modelSelect.value = customModel;
            this.currentModel = customModel;
        }
        
        // Update WebSocket connection with new keys
        if (this.isConnected) {
            this.socket.send(JSON.stringify({
                type: 'update_api_keys',
                api_keys: this.apiKeys
            }));
        } else {
            this.connectWebSocket();
        }
        
        this.closeSettingsModal();
        this.showStatusMessage('Settings saved successfully!', 'success');
    }
}

// Initialize the chat app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.chatApp = new ChatApp();
});

// Handle page visibility changes to manage WebSocket connection
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        // Page is hidden, could pause some operations
    } else {
        // Page is visible, ensure connection is active
        if (window.chatApp && !window.chatApp.isConnected) {
            window.chatApp.connectWebSocket();
        }
    }
});

// Handle beforeunload to clean up
window.addEventListener('beforeunload', () => {
    if (window.chatApp && window.chatApp.socket) {
        window.chatApp.socket.close();
    }
}); 