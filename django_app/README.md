# T3 Chat Clone - Django Edition

A modern, feature-rich chat application built with Django, featuring real-time messaging, multiple AI models, file uploads, and web search capabilities.

## 🏆 Competition Features

### Core Requirements ✅
- **Chat with Various LLMs**: 13+ AI models via OpenRouter integration
- **Authentication & Sync**: Django user system with persistent chat history
- **Browser Friendly**: Modern web interface with responsive design
- **Easy to Try**: One-command setup with demo accounts

### Bonus Features ✅
- **File Attachments**: Support for images, PDFs, and text files
- **Image Generation**: AI-powered image creation
- **Syntax Highlighting**: Beautiful code formatting with Pygments
- **Resumable Streams**: Real-time WebSocket communication
- **Chat Branching**: Multiple conversation management
- **Sharing**: Export and share conversations
- **Web Search**: Integrated search with Tavily API
- **Bring Your Own Key**: Secure API key management

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Redis server
- Git

### Installation

1. **Clone and Setup**
```bash
git clone <repository-url>
cd django_app
pip install -r requirements.txt
```

2. **Initialize Application**
```bash
python manage.py setup_t3_chat --create-superuser
```

3. **Start Services**
```bash
# Terminal 1: Django server
python manage.py runserver

# Terminal 2: Celery worker
celery -A config worker -l info

# Terminal 3: Redis (if not running)
redis-server
```

4. **Access the Application**
- Main Chat: http://localhost:8000/
- Admin Panel: http://localhost:8000/admin/
- API Documentation: http://localhost:8000/api/docs/

## 🔧 Configuration

### API Keys
Configure your API keys through the web interface:
1. Click the settings button (⚙️) in the chat interface
2. Enter your OpenRouter API key (required)
3. Enter your Tavily API key (optional, for web search)

### Environment Variables
Create a `.env` file in the project root:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
REDIS_URL=redis://localhost:6379/0
OPENROUTER_API_KEY=your-openrouter-key
TAVILY_API_KEY=your-tavily-key
```

## 📚 Features Overview

### 🤖 AI Models
- **OpenAI**: GPT-4o, GPT-4 Turbo, GPT-3.5 Turbo
- **Anthropic**: Claude 3.5 Sonnet, Claude 3 Opus
- **Google**: Gemini Pro 1.5, Gemini Flash 1.5
- **Meta**: Llama 3.1 70B Instruct
- **Mistral**: Mistral Nemo, Mistral Large
- **DeepSeek**: DeepSeek Chat
- **Cohere**: Command R+
- **Custom Models**: Support for any OpenRouter model

### 💬 Chat Features
- **Real-time Messaging**: WebSocket-based instant communication
- **Message History**: Persistent conversation storage
- **Multiple Conversations**: Organize chats by topic
- **Message Search**: Find specific conversations and messages
- **Export/Import**: Save and restore chat histories

### 📎 File Support
- **Images**: JPEG, PNG, GIF, WebP
- **Documents**: PDF, TXT, MD, JSON
- **Code Files**: Python, JavaScript, HTML, CSS, and more
- **File Analysis**: Automatic content extraction and analysis

### 🎨 User Interface
- **Modern Design**: Clean, responsive interface
- **Dark/Light Mode**: Automatic theme detection
- **Mobile Friendly**: Optimized for all screen sizes
- **Syntax Highlighting**: Beautiful code formatting
- **Markdown Support**: Rich text formatting

### 🔍 Web Search
- **Real-time Search**: Get up-to-date information
- **Source Citations**: Links to original sources
- **Context Integration**: Search results integrated into conversations

## 🏗️ Architecture

### Backend Stack
- **Django 4.2**: Web framework
- **Django Channels**: WebSocket support
- **Celery**: Background task processing
- **Redis**: Caching and message broker
- **SQLite/PostgreSQL**: Database
- **OpenAI SDK**: AI model integration

### Frontend Stack
- **Vanilla JavaScript**: No framework dependencies
- **WebSocket API**: Real-time communication
- **CSS Grid/Flexbox**: Modern layout
- **Progressive Enhancement**: Works without JavaScript

### Key Components
```
django_app/
├── config/                 # Django settings and configuration
├── chat/                   # Main chat application
│   ├── models.py          # Database models
│   ├── views.py           # HTTP views and API endpoints
│   ├── consumers.py       # WebSocket consumers
│   ├── tasks.py           # Background tasks
│   ├── serializers.py     # API serializers
│   ├── templates/         # HTML templates
│   └── static/            # CSS, JavaScript, images
├── logs/                   # Application logs
├── requirements.txt        # Python dependencies
└── manage.py              # Django management script
```

## 🔒 Security Features

- **User Authentication**: Django's built-in auth system
- **API Key Encryption**: Secure storage of user API keys
- **CSRF Protection**: Cross-site request forgery prevention
- **Rate Limiting**: API abuse prevention
- **Input Validation**: Comprehensive data validation
- **File Upload Security**: Safe file handling and validation

## 📊 Admin Interface

Access the Django admin at `/admin/` to:
- Manage users and conversations
- View chat statistics
- Monitor system health
- Configure application settings
- Export data for analysis

## 🧪 Testing

Run the test suite:
```bash
python manage.py test
```

Run with coverage:
```bash
coverage run --source='.' manage.py test
coverage report
```

## 🚀 Deployment

### Production Setup
1. Set `DEBUG=False` in settings
2. Configure a production database (PostgreSQL recommended)
3. Set up a reverse proxy (Nginx)
4. Use a production WSGI server (Gunicorn)
5. Configure SSL/TLS certificates
6. Set up monitoring and logging

### Docker Deployment
```bash
docker-compose up -d
```

### Environment Variables for Production
```env
SECRET_KEY=your-production-secret-key
DEBUG=False
DATABASE_URL=postgresql://user:pass@localhost/dbname
REDIS_URL=redis://localhost:6379/0
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📝 API Documentation

The application provides a comprehensive REST API:
- **Authentication**: Token-based auth
- **Conversations**: CRUD operations
- **Messages**: Send and retrieve messages
- **File Uploads**: Handle file attachments
- **User Management**: Profile and settings

Visit `/api/docs/` for interactive API documentation.

## 🐛 Troubleshooting

### Common Issues

**WebSocket Connection Failed**
- Ensure Redis is running
- Check firewall settings
- Verify WebSocket URL configuration

**API Key Errors**
- Verify OpenRouter API key is valid
- Check API key permissions
- Ensure sufficient API credits

**File Upload Issues**
- Check file size limits (10MB default)
- Verify file type is supported
- Ensure proper permissions

### Logs
Check application logs in the `logs/` directory:
- `django.log`: General application logs
- `chat.log`: Chat-specific logs
- `celery.log`: Background task logs

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- OpenRouter for AI model access
- Tavily for web search capabilities
- Django community for the excellent framework
- All contributors and testers

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the troubleshooting guide

---

**Built for the T3 Chat Cloneathon Competition** 🏆 